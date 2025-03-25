import './App.css';
import HomePage from './pages/HomePage';
import React from "react";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
// import HomePage from "./HomePage";
import UploadForm from "./pages/UploadForm";

function App() {
  return (
    // <HomePage/>
    <Router>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/upload" element={<UploadForm />} />
      </Routes>
    </Router>
  );
}

export default App;
