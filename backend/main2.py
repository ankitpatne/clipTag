from contextlib import asynccontextmanager
from fastapi import FastAPI
import requests
from sqlalchemy import create_engine, Column, Integer, String, Float, JSON, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from fastapi import Depends
from sqlalchemy.orm import Session
from fastapi import UploadFile, File, Form, Request, HTTPException
import boto3
import uuid
from google.cloud import vision, videointelligence
import os
from google import genai
from elasticsearch import Elasticsearch
import json
from fastapi.middleware.cors import CORSMiddleware

# os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "path/to/your/service-account-key.json"

# Initialize Elasticsearch client
es = Elasticsearch("https://localhost:9200",
                   basic_auth=("elastic", "oNGeOBcU*ubZAylIXeVU"),
                   verify_certs=False
    )  # Replace with your Elasticsearch URL if different

s3_client = boto3.client(
    's3', 
    region_name = 'ap-south-1', 
    aws_access_key_id='AKIAXYKJVRC4EHE6OLF5',
    aws_secret_access_key='zShSaUy2P6nOmEm4inmjIMWN25tk51w6UEXhkGlo'
)
# Example usage
bucket_name = 'aws-vod-1-source71e471f1-rgfsfngoq2jv'

DATABASE_URL = "postgresql://ankit:test123@localhost/inc_db_1"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def create_index():
    index_name = "videos"
    if not es.indices.exists(index=index_name):
        es.indices.create(index=index_name, body={
            "mappings": {
                "properties": {
                    "video_id": {"type": "keyword"},
                    "title": {"type": "text"},
                    "description": {"type": "text"},
                    "tags": {"type": "keyword"},
                    "explicit_content": {"type": "nested"},
                    "transcription": {"type": "text"},
                    "ai_generated_title": {"type": "text"},
                    "ai_generated_description": {"type": "text"},
                    "s3_url": {"type": "keyword"}
                }
            }
        })
        print(f"Index '{index_name}' created.")
    else:
        print(f"Index '{index_name}' already exists.")

def generate_presigned_url(bucket_name, object_key, expiration=3600):
    # object_key = object_key.split(f"https://{bucket_name}.s3.amazonaws.com/")[1]
    url = s3_client.generate_presigned_url(
        'get_object',
        Params={'Bucket': bucket_name, 'Key': object_key},
        ExpiresIn=expiration
    )
    return url

genAiClient = genai.Client(api_key="AIzaSyCWSO9krG5hxoiz9yA7xJXov0xMlvKwTmU")

def generate_title_description(transcription: str, tags: list):
    title = genAiClient.models.generate_content(
        model="gemini-2.0-flash", contents=f"Generate a concise title for a video about {transcription} with tags {', '.join(tags)}. Give only the title directly without any additional information."
    )
    description = genAiClient.models.generate_content(
        model="gemini-2.0-flash", contents=f"Generate a description for a video about {transcription} with tags {', '.join(tags)}. Give only the description directly without any additional information. It should be a brief summary of the video content."
    )
    return title.text, description.text

class Video(Base):
    __tablename__ = "videos"
    id = Column(Integer, primary_key=True, index=True)
    video_id = Column(String(100), unique=True, index=True, nullable=False)
    s3_url = Column(String(500), nullable=False)
    duration = Column(Float, nullable=False)
    tags = Column(JSON)  # Store auto-generated tags as JSON
    explicit_content = Column(JSON, nullable=True)  # Store explicit content detection results
    explicit_content_detected = Column(Boolean, nullable=True)  # Store whether explicit content was detected
    transcription = Column(String, nullable=True)  # Store video transcription
    streaming_url = Column(String, nullable=True)  # Store streaming URL
    title = Column(String, nullable=True)  # Store video title
    description = Column(String, nullable=True)  # Store video description
    ai_generated_title = Column(String, nullable=True)  # Store AI-generated title
    ai_generated_description = Column(String, nullable=True)  # Store AI-generated description

def analyze_video(video_id: str, s3_url: str, db: Session):
    # Analyze video using Google Video Intelligence API
    response = requests.get(s3_url)
    if response.status_code != 200:
        raise Exception(f"Failed to download video. HTTP Status Code: {response.status_code}")

    input_content = response.content
    video_client = videointelligence.VideoIntelligenceServiceClient()
    features = [
        videointelligence.Feature.LABEL_DETECTION,
        videointelligence.Feature.EXPLICIT_CONTENT_DETECTION,
        videointelligence.Feature.SPEECH_TRANSCRIPTION
    ]
    config = videointelligence.SpeechTranscriptionConfig(
    language_code="en-US", enable_automatic_punctuation=True
    )
    video_context = videointelligence.VideoContext(speech_transcription_config=config)

    operation = video_client.annotate_video(request={"features": features, "input_content": input_content, "video_context": video_context})

    result = operation.result(timeout=300)

    # Extract labels
    labels = []
    for annotation in result.annotation_results[0].segment_label_annotations:
        labels.append(annotation.entity.description)

    # Extract explicit content detection results
    explicit_content = []
    for frame in result.annotation_results[0].explicit_annotation.frames:
        # if frame.likelihood in [videointelligence.Likelihood.LIKELY, videointelligence.Likelihood.VERY_LIKELY]:
        #     explicit_content.append({
        #         "time_offset": frame.time_offset.seconds + frame.time_offset.microseconds / 1e6,
        #         "likelihood": videointelligence.Likelihood(frame.likelihood).name
        #     })

        if frame.pornography_likelihood in ["LIKELY", "VERY_LIKELY"]:
            explicit_content.append({
                "time_offset": frame.time_offset.seconds + frame.time_offset.microseconds / 1e6,
                "likelihood": frame.pornography_likelihood
            })
    
    # update explicit content detected flag
    video = db.query(Video).filter(Video.video_id == video_id).first()
    if len(explicit_content) > 0:       
        if video:
            video.explicit_content_detected = True
            db.commit()
    else:
        if video:
            video.explicit_content_detected = False
            db.commit()
        

    # Extract transcription

    # Debug: Print the full transcription response
    # print("Full Transcription Response:", result.annotation_results[0].speech_transcriptions)

    transcription = ""
    for speech_transcription in result.annotation_results[0].speech_transcriptions:
        for alternative in speech_transcription.alternatives:
            transcription += alternative.transcript + " "
        
        # if speech_transcription.alternatives:
        #     transcription += speech_transcription.alternatives[0].transcript + " "

    # Generate title and description
    title, description = generate_title_description(transcription, labels)

    # Update video metadata in PostgreSQL
    video = db.query(Video).filter(Video.video_id == video_id).first()
    
    # print labels for debugging
    print(labels)

    if video:
        video.tags = labels  # Ensure labels is JSON-serializable
        video.explicit_content = explicit_content
        video.transcription = transcription.strip()
        video.ai_generated_title = title
        video.ai_generated_description = description
        db.commit()
    else:
        raise ValueError(f"Video with ID {video_id} not found.")

    return {"ai_generated_title": title, "ai_generated_description": description, "tags": labels, "explicit_content": explicit_content, "transcription": transcription.strip(), "title": video.title, "description": video.description}

# Create the database tables
Base.metadata.create_all(bind=engine)

# Dependency to get the database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    create_index()  # Ensure the Elasticsearch index is created
    print("Application startup complete. OK!")
    
    yield  # This is where the application runs

    # Shutdown logic (if needed)
    print("Application shutdown complete. OK!")

app = FastAPI(lifespan=lifespan)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/abx")
def home2():
    return {"message": "Welcome to the Video Backend!"}

@app.get("/test-db")
def test_db(db: Session = Depends(get_db)):
    # Fetch all videos
    videos = db.query(Video).all()
    return [{"video_id": v.video_id, "s3_url": v.s3_url, "tags": v.tags} for v in videos]


@app.post("/upload")
async def upload_video(title : str = Form("Untitled Video") , description: str = Form("N/A"), file: UploadFile = File(...), db: Session = Depends(get_db)):
    video_id = str(uuid.uuid4())
    s3_key = f"assets01/videos/{video_id}.mp4"

    # Upload to S3
    s3_client.upload_fileobj(file.file, 'aws-vod-1-source71e471f1-rgfsfngoq2jv', s3_key)
    s3_url = f"https://aws-vod-1-source71e471f1-rgfsfngoq2jv.s3.amazonaws.com/{s3_key}"

    # Save video metadata to PostgreSQL
    video = Video(video_id=video_id, s3_url=s3_key, duration=120, title = title, description = description)
    db.add(video)
    db.commit()

    # wait till the time video streaming url is generated
    # while True:
    #     video = db.query(Video).filter(Video.video_id == video_id).first()
    #     if video.streaming_url:
    #         break

    # Index video metadata in Elasticsearch
    es.index(index="videos", id=video_id, body={
        "video_id": video_id,
        "title": title,
        "description": description,
        "tags": [],
        "explicit_content": [],
        "transcription": "",
        "ai_generated_title": "",
        "ai_generated_description": "",
        "s3_url": s3_url
    })

    return {"video_id": video_id, "streaming_url": video.streaming_url}

@app.post("/analyze/{video_id}")
async def analyze(video_id: str, db: Session = Depends(get_db)):
    video = db.query(Video).filter(Video.video_id == video_id).first()
    if not video:
        return {"error": "Video not found"}
    
    # Get the presigned URL
    presigned_url = generate_presigned_url(bucket_name, video.s3_url)

    analysis_results = analyze_video(video_id, presigned_url, db)

    print()
    print()
    print(analysis_results["tags"])
    print()
    print()
    # Update Elasticsearch index with the analysis results
    es.update(index="videos", id=video_id, body={
        "doc": {
            "ai_generated_title": analysis_results["ai_generated_title"],
            "ai_generated_description": analysis_results["ai_generated_description"],
            "tags": analysis_results["tags"],
            "explicit_content": analysis_results["explicit_content"],
            "transcription": analysis_results["transcription"],
            "title": analysis_results["title"],
            "description": analysis_results["description"]
        }
    })
    return {
        "title": analysis_results["title"],
        "description": analysis_results["description"],
        "ai_generated_title": analysis_results["ai_generated_title"],
        "ai_generated_description": analysis_results["ai_generated_description"],
        "video_id": video_id,
        "tags": analysis_results["tags"],
        "explicit_content": analysis_results["explicit_content"],
        "transcription": analysis_results["transcription"]
    }

# endpoint to fetch videos flagged for moderation
@app.get("/moderation")
def get_moderation_videos(db: Session = Depends(get_db)):
    # Fetch videos with explicit content flagged
    videos = db.query(Video).filter(Video.explicit_content != None).all()

    # Filter videos where explicit content likelihood is "VERY_LIKELY" or "LIKELY"
    flagged_videos = []
    for video in videos:
        for frame in video.explicit_content:
            if frame["likelihood"] in ["VERY_LIKELY", "LIKELY"]:
                flagged_videos.append({
                    "video_id": video.video_id,
                    "s3_url": f"https://aws-vod-1-source71e471f1-rgfsfngoq2jv.s3.amazonaws.com/{video.s3_url}",
                    "explicit_content": video.explicit_content
                })
                break  # Stop checking further frames for this video

    return flagged_videos

@app.get("/search")
def search_videos(query: str):
    # Search videos using Elasticsearch
    search_results = es.search(index="videos", body={
        "query": {
            "multi_match": {
                "query": query,
                "fields": ["title", "description", "tags", "transcription", "ai_generated_title", "ai_generated_description"]
            }
        }
    })

    return {"results": [hit["_source"] for hit in search_results["hits"]["hits"]]}

# list all videos
@app.get("/videos")
def list_videos(db: Session = Depends(get_db)):
    videos = db.query(Video).order_by(Video.id.desc()).all()
    # return all the fields of all the videos
    return [{"video_id": v.video_id, "s3_url": f"https://aws-vod-1-source71e471f1-rgfsfngoq2jv.s3.amazonaws.com/{v.s3_url}", "title": v.title, "description": v.description, "tags": v.tags, "explicit_content": v.explicit_content, "transcription": v.transcription, "ai_generated_title": v.ai_generated_title, "ai_generated_description": v.ai_generated_description, "streaming_url": v.streaming_url, "explicit_content_detected": v.explicit_content_detected} for v in videos]

# get a specific video
@app.get("/videos/{video_id}")
def get_video(video_id: str, db: Session = Depends(get_db)):
    video = db.query(Video).filter(Video.video_id == video_id).first()
    if video:
        return {"video_id": video.video_id, "s3_url": f"https://aws-vod-1-source71e471f1-rgfsfngoq2jv.s3.amazonaws.com/{video.s3_url}", "title": video.title, "description": video.description, "tags": video.tags, "explicit_content": video.explicit_content, "transcription": video.transcription, "ai_generated_title": video.ai_generated_title, "ai_generated_description": video.ai_generated_description, "streaming_url": video.streaming_url, "explicit_content_detected": video.explicit_content_detected}
    else:
        raise HTTPException(status_code=404, detail="Video not found")

@app.post("/mediaconvert-callback")
async def mediaconvert_callback(request: Request, db: Session = Depends(get_db)):
    try:
        # Parse the SNS notification
        body = await request.body()
        notification = json.loads(body)

        # Confirm the subscription if required
        if "Type" in notification and notification["Type"] == "SubscriptionConfirmation":
            # Confirm the subscription by visiting the SubscribeURL
            import requests
            requests.get(notification["SubscribeURL"])
            return {"message": "Subscription confirmed"}

        # Process the notification
        if "Message" in notification:
            message = json.loads(notification["Message"])

            # Extract the streaming URL and input file
            # input_file = message.get("InputFile")
            streaming_url = message.get("Outputs", {}).get("HLS_GROUP", [None])[0]
            # extract the video_id from the streaming url
            video_id = streaming_url.split("/")[-1].split(".")[0]

            if streaming_url:
                # Extract the video_id from the input file path
                # video_id = input_file.split("/")[-1].split(".")[0]

                # Update the video record in the database
                video = db.query(Video).filter(Video.video_id == video_id).first()
                if video:
                    video.streaming_url = streaming_url
                    db.commit()
                    return {"message": "Video updated successfully"}
                else:
                    raise HTTPException(status_code=404, detail="Video not found")

        return {"message": "Notification processed"}
    except Exception as e:
        print(f"Error processing notification: {e}")
        raise HTTPException(status_code=500, detail="Error processing notification")