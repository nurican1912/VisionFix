// client/src/App.jsx
import { useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, useNavigate } from 'react-router-dom';
import axios from 'axios';
import './App.css';

// --- Login / Register Component ---
function AuthPage({ setIsAuthenticated }) {
  const [isLogin, setIsLogin] = useState(true);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const navigate = useNavigate();

  const handleAuth = async () => {
    const endpoint = isLogin ? '/login' : '/register';
    try {
      const res = await axios.post(`http://127.0.0.1:5000/api${endpoint}`, { username, password });
      
      if (isLogin) {
        localStorage.setItem('token', res.data.access_token);
        setIsAuthenticated(true);
        navigate('/');
      } else {
        alert('Registration successful! You can now login.');
        setIsLogin(true);
      }
    } catch (err) {
      alert(err.response?.data?.msg || 'An error occurred');
    }
  };

  return (
    <div className="auth-container">
      <h1>VisionFix <span className="beta">AI</span></h1>
      <h2>{isLogin ? 'Login' : 'Sign Up'}</h2>
      
      <div className="form-group">
        <input 
          type="text" 
          placeholder="Username" 
          value={username} 
          onChange={(e) => setUsername(e.target.value)} 
        />
      </div>
      <div className="form-group">
        <input 
          type="password" 
          placeholder="Password" 
          value={password} 
          onChange={(e) => setPassword(e.target.value)} 
        />
      </div>
      
      <button className="btn btn-primary" onClick={handleAuth}>
        {isLogin ? 'Login' : 'Sign Up'}
      </button>

      <button className="link-btn" onClick={() => setIsLogin(!isLogin)}>
        {isLogin ? "Don't have an account? Sign Up" : "Already have an account? Login"}
      </button>
    </div>
  );
}

// --- Main Application (Dashboard) Component ---
function Dashboard({ handleLogout }) {
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
    if (!file || !description) return alert("Please upload a photo and enter a description.");

    setLoading(true);
    const formData = new FormData();
    formData.append('file', file);
    formData.append('description', description);
    const token = localStorage.getItem('token');

    try {
      const response = await axios.post('http://127.0.0.1:5000/api/analyze', formData, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setReport(response.data.report);
    } catch (error) {
      console.error("Error:", error);
      if(error.response && error.response.status === 401) handleLogout(); // Logout if token is invalid
      else alert("Analysis failed.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app-container">
      <div style={{display:'flex', justifyContent:'space-between', alignItems:'center'}}>
        <h1>VisionFix <span className="beta">PRO</span></h1>
        <button onClick={handleLogout} style={{background:'transparent', border:'1px solid white', color:'white', padding:'5px 15px', borderRadius:'5px', cursor:'pointer'}}>Logout</button>
      </div>

      <div className="upload-area">
        <label htmlFor="file-upload" className="file-label">
          {preview ? "Change Photo" : "📸 Upload Damage Photo"}
        </label>
        <input id="file-upload" type="file" onChange={handleFileChange} accept="image/*" />

        {preview && (
          <div className="preview-box">
            <img src={preview} alt="Preview" />
          </div>
        )}

        <textarea 
          placeholder="Describe the damage (e.g., Broken front bumper, scratched headlight)..."
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          rows="4"
        ></textarea>

        <button onClick={handleAnalyze} disabled={loading || !file} className="btn btn-primary">
          {loading ? "Analyzing..." : "Analyze with AI"}
        </button>
      </div>

      {report && (
        <div className="result-section">
          <h3>📋 AI Assessment Report</h3>
          <div className="report-content">
            <pre>{report}</pre>
          </div>
        </div>
      )}
    </div>
  );
}

// --- Main Routing ---
function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(!!localStorage.getItem('token'));

  const handleLogout = () => {
    localStorage.removeItem('token');
    setIsAuthenticated(false);
  };

  return (
    <Router>
      <Routes>
        <Route path="/login" element={!isAuthenticated ? <AuthPage setIsAuthenticated={setIsAuthenticated} /> : <Navigate to="/" />} />
        <Route path="/" element={isAuthenticated ? <Dashboard handleLogout={handleLogout} /> : <Navigate to="/login" />} />
      </Routes>
    </Router>
  );
}

export default App;