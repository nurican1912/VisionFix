import { useState } from 'react';
import axios from 'axios';
import './App.css';

function App() {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [description, setDescription] = useState("");
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleFileChange = (e) => {
    const selected = e.target.files[0];
    if (selected) {
      setFile(selected);
      setPreview(URL.createObjectURL(selected));
      setReport(null);
    }
  };

  const handleAnalyze = async () => {
    if (!file || !description) {
      alert("Please upload a photo and describe the damage.");
      return;
    }

    setLoading(true);
    const formData = new FormData();
    formData.append('file', file);
    formData.append('description', description);

    try {

      const response = await axios.post('http://127.0.0.1:5000/api/analyze', formData);
      setReport(response.data.report);
    } catch (error) {
      console.error("Error:", error);
      alert("Analysis failed. Check backend console.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app-container">
      <header className="navbar">
        <h1>VisionFix <span className="beta">AI</span></h1>
      </header>

      <div className="main-content">
        <div className="upload-section">
          <h2>Vehicle Damage Assessment</h2>
          <p>Upload a photo and describe the damage for an instant AI cost estimate.</p>
          
          <div className="input-group">
            <div className="file-upload-wrapper">
              <input type="file" id="file" onChange={handleFileChange} accept="image/*" hidden />
              <label htmlFor="file" className="upload-btn">
                {preview ? "Change Photo" : "📸 Upload Photo"}
              </label>
            </div>
            
            {preview && (
              <div className="preview-box">
                <img src={preview} alt="Damage Preview" />
              </div>
            )}

            <textarea 
              placeholder="Describe the damage (e.g., 'Broken front bumper and scratched headlight')..."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows="4"
            ></textarea>

            <button onClick={handleAnalyze} disabled={loading || !file} className="analyze-btn">
              {loading ? "Processing..." : "Analyze Damage & Estimate Cost"}
            </button>
          </div>
        </div>

        {report && (
          <div className="result-section">
            <h3>AI Assessment Report</h3>
            <div className="report-content">
              <pre>{report}</pre>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;