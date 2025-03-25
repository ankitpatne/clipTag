import React, { useState, useEffect, useCallback } from "react";
import ReactPlayer from "react-player";
import "../styles/HomePage.css";
import { useNavigate } from "react-router-dom";

const API_URL = process.env.REACT_APP_BACKEND_API_URL;

const HomePage = () => {
  const navigate = useNavigate();
  const [videos, setVideos] = useState([]);
  const [selectedVideo, setSelectedVideo] = useState(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [error, setError] = useState("");
  const [typingTimeout, setTypingTimeout] = useState(null);

  useEffect(() => {
    fetchVideos();
  }, []);

  const fetchVideos = () => {
    fetch(`${API_URL}/videos`)
      .then((response) => response.json())
      .then((data) => {
        if (Array.isArray(data) && data.length > 0) {
          const processedVideos = data.map((video) => ({
            video_id: video.video_id,
            title: video.title || "Untitled Video",
            ai_generated_title: video.ai_generated_title,
            description: video.description || "No description available",
            ai_generated_description: video.ai_generated_description,
            streaming_url: video.streaming_url || video.s3_url || "",
            tags: video.tags || [],
            explicit_content: video.explicit_content_detected || false,
            transcription: video.transcription || null,
          }));

          setVideos(processedVideos);
        } else {
          setError("No videos found. Displaying default videos.");
          setVideos(getDummyVideos());
        }
      })
      .catch(() => {
        setError("Error fetching videos. Displaying default videos.");
        setVideos(getDummyVideos());
      });
  };

  const getDummyVideos = () => [
    {
      video_id: "1",
      title: "Sample Video",
      ai_generated_title: "Hope In The Waiting",
      ai_generated_description: "Inspirational message about patience.",
      streaming_url:
        "https://d1l4ip8v5ktt0n.cloudfront.net/cfbb607b-0d04-48e2-86bc-47fdd49b0128/AppleHLS1/2a54914f-794f-4b8a-b5c0-a81c92e55218.m3u8",
      tags: ["Hope", "Faith"],
      explicit_content: false,
      transcription: "This is a sample video transcript.",
    },
    {
      video_id: "2",
      title: "Godly Ambition",
      ai_generated_title: "The Power of Faith",
      ai_generated_description: "Stay motivated with faith.",
      streaming_url:
        "https://d1l4ip8v5ktt0n.cloudfront.net/92667945-e072-4c2f-952b-72d2f007f4b9/AppleHLS1/avatar.m3u8",
      tags: ["Ambition", "Faith"],
      explicit_content: true,
      transcription: "This is another sample video transcript.",
    },
  ];

  const handleSearch = (e) => {
    const query = e.target.value;
    setSearchQuery(query);
  
    // Clear the previous timeout
    if (typingTimeout) {
      clearTimeout(typingTimeout);
    }
  
    // Set a new timeout to delay the API call
    setTypingTimeout(
      setTimeout(() => {
        if (!query.trim()) {
          fetchVideos();
          return;
        }
  
        fetch(`${API_URL}/search?query=${query}`)
          .then((response) => response.json())
          .then((data) => {
            if (data.results && Array.isArray(data.results)) {
              // Fetch video details for each search result
              const videoPromises = data.results.map((item) =>
                fetch(`${API_URL}/videos/${item.video_id}`)
                  .then((response) => response.json())
                  .catch(() => null) // Handle individual fetch errors
              );
  
              // Wait for all video details to be fetched
              Promise.all(videoPromises)
                .then((videoDetails) => {
                  // Filter out any failed fetches (null values)
                  const validVideos = videoDetails.filter((video) => video !== null);
                  setVideos(validVideos);
                })
                .catch(() => setError("Error fetching video details."));
            } else {
              setError("No search results found.");
            }
          })
          .catch(() => setError("Error fetching search results."));
      }, 500) // Adjust the delay (in milliseconds) as needed
    );
  };

  const handleUploadClick = () => {
    navigate("/upload");
  };

  return (
    <div className="homepage">
      <h1 className="page-title">VedStream</h1>

      <div className="top-bar">
        <input
          type="text"
          placeholder="🔍 Search for a video..."
          className="search-bar"
          onChange={handleSearch}
          value={searchQuery}
        />
        
        <button className="upload-button" onClick={handleUploadClick}>
          Upload Video
        </button>
        
      </div>

      {selectedVideo && (
        <div className="main-video-container">
          <ReactPlayer
            url={selectedVideo.streaming_url}
            controls
            playing
            width="100%"
            height="500px"
          />

          <div className="video-info">
            <h2 className="video-title">
              <span className="label">Title:</span> {selectedVideo.title}
            </h2>
            <h3 className="video-subtitle">
              <span className="label">AI Generated Title:</span>{" "}
              {selectedVideo.ai_generated_title}
            </h3>

            <p className="video-description">
              <span className="label">Description:</span>{" "}
              {selectedVideo.description?.split(" ").length > 60 ? (
                <>
                  {selectedVideo.description.split(" ").slice(0, 60).join(" ")}...
                  <span className="read-more"> <b> Read More </b></span>
                </>
              ) : (
                selectedVideo.description
              )}
            </p>
            <p className="video-description">
              <span className="label">AI Generated Description:</span>{" "}
              {selectedVideo.ai_generated_description?.split(" ").length > 60 ? (
                <>
                  {selectedVideo.ai_generated_description?.split(" ")
                    .slice(0, 60)
                    .join(" ")}
                  ...
                  <span className="read-more"> <b> Read More </b></span>
                </>
              ) : (
                selectedVideo.ai_generated_description
              )}
            </p>

            {selectedVideo.tags?.length > 0 && (
              <div className="video-tags">
                <h4 className="tag-heading">Tags:</h4>
                <div className="tag-container">
                  {selectedVideo.tags.map((tag, index) => (
                    <span key={index} className="tag-button">
                      {tag}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {selectedVideo.transcription && (
              <div className="video-transcription">
                <h3 className="transcription-heading">📜 Transcription:</h3>
                <p>
                  {selectedVideo.transcription?.split(" ").length > 60 ? (
                    <>
                      {selectedVideo.transcription?.split(" ")
                        .slice(0, 30)
                        .join(" ")}
                      ...
                      <span className="read-more"> <b> Read More </b></span>
                    </>
                  ) : (
                    selectedVideo.transcription
                  )}
                </p>
              </div>
            )}
          </div>
        </div>
      )}

      {error && <p className="error-message">{error}</p>}

      <div className="video-grid">
        {videos?.length > 0 &&
          videos.map((video) => (
            video.title &&
            video.streaming_url && (
            <div
              key={video.video_id}
              className="video-item"
              onClick={() => setSelectedVideo(video)}
            >
              <ReactPlayer
                url={video.streaming_url}
                light={
                  "https://static.vecteezy.com/system/resources/thumbnails/031/975/122/small/white-colored-round-play-button-on-pastel-background-concept-of-video-icon-logo-for-play-clip-audio-playback-3d-rendering-illustration-play-interface-symbol-social-media-and-website-posts-free-photo.jpg"
                }
                controls
                width="100%"
                height="200px"
              />
              <div className="video-details">
                <h3 className="video-card-title">{video.title}</h3>
                <div className="video-card-tags">
                  {video.tags?.slice(0, 3).map((tag, index) => (
                    <span key={index} className="card-tag">
                      {tag}
                    </span>
                  ))}
                  {video.tags?.length > 3 && (
                    <span className="card-tag more-tags">
                      +{video.tags.length - 4}
                    </span>
                  )}
                </div>
                {video.explicit_content_detected && (
                  <p className="explicit-warning">⚠️ Explicit Content</p>
                )}
              </div>
            </div>
            )
          ))}
      </div>
    </div>
  );
};

export default HomePage;