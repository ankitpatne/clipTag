import { useState } from "react";
import { useNavigate } from "react-router-dom"; // Import useNavigate
import "../styles/UploadForm.css"; // Import the CSS file
import axios from "axios";

const API_URL = process.env.REACT_APP_BACKEND_API_URL;

const UploadForm = () => {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [file, setFile] = useState(null);
  const [message, setMessage] = useState("");

  const navigate = useNavigate(); // Initialize navigate function

  const handleSubmit = async (e) => {
    e.preventDefault();
    setMessage("Uploading...");

    const formData = new FormData();
    formData.append("title", title);
    formData.append("description", description);
    formData.append("file", file);

    try {
      const uploadResponse = await axios.post(`${API_URL}/upload`, formData, {
        headers: {
          "Content-Type": "multipart/form-data",
        },
      });

      if (uploadResponse.data.video_id) {
        setMessage("Video uploaded successfully!");


        // Start analyzing in the background
        axios.post(`${API_URL}/analyze/${uploadResponse.data.video_id}`).catch((error) => {
          console.error("Error analyzing video:", error);
        });

        // Redirect to HomePage immediately after upload
        navigate("/");
        
      } else {
        setMessage("Upload failed. Try again.");
      }
    } catch (error) {
      setMessage("Error occurred. Try again.");
      console.error(error);
    }
  };

  return (
    <div className="upload-container">
      <h2>Upload Video</h2>
      <form onSubmit={handleSubmit}>
        <input
          type="text"
          placeholder="Title"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          required
        />
        <textarea
          placeholder="Description"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          required
        ></textarea>
        <input
          type="file"
          accept="video/*"
          onChange={(e) => setFile(e.target.files[0])}
          required
        />
        <button type="submit">Upload</button>
      </form>
      {message && <p className="message">{message}</p>}
    </div>
  );
};

export default UploadForm;
