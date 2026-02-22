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
    // Vite Proxy sayesinde artık tam URL yazmamıza gerek yok
    const endpoint = isLogin ? '/login' : '/register';
    try {
      const res = await axios.post(`/api${endpoint}`, { username, password });
      
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
  const [view, setView] = useState('new');
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [description, setDescription] = useState("");
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);
  
  const [history, setHistory] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(false);

  const [selectedImage, setSelectedImage] = useState(null);

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
      // Relative path kullanımı
      const response = await axios.post('/api/analyze', formData, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setReport(response.data.report);
    } catch (error) {
      console.error("Error:", error);
      if(error.response && error.response.status === 401) handleLogout();
      else alert("Analysis failed.");
    } finally {
      setLoading(false);
    }
  };

  const fetchHistory = async () => {
    setView('history');
    setHistoryLoading(true);
    const token = localStorage.getItem('token');
    try {
      // Relative path kullanımı
      const res = await axios.get('/api/history', {
        headers: { Authorization: `Bearer ${token}` }
      });
      setHistory(res.data);
    } catch (error) {
      console.error("History fetch error", error);
    } finally {
      setHistoryLoading(false);
    }
  };

  return (
    <div className="app-container">
      <div style={{display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:'20px', borderBottom:'1px solid rgba(255,255,255,0.2)', paddingBottom:'15px'}}>
        <h1 style={{margin:0, fontSize:'1.8rem'}}>VisionFix <span className="beta">PRO</span></h1>
        
        <div style={{display:'flex', gap:'10px'}}>
          <button onClick={() => setView('new')} className={`nav-btn ${view === 'new' ? 'active' : ''}`}>New Analysis</button>
          <button onClick={fetchHistory} className={`nav-btn ${view === 'history' ? 'active' : ''}`}>My History</button>
          <button onClick={handleLogout} className="logout-btn">Logout</button>
        </div>
      </div>

      {view === 'new' && (
        <div className="upload-area animation-fade">
          <label htmlFor="file-upload" className="file-label">
            {preview ? "🔄 Change Photo" : "📸 Upload Damage Photo"}
          </label>
          <input id="file-upload" type="file" onChange={handleFileChange} accept="image/*" />

          {preview && (
            <div className="preview-box">
              <img src={preview} alt="Preview" />
            </div>
          )}

          <textarea 
            placeholder="Describe the damage (e.g., Broken front bumper)..."
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows="4"
          ></textarea>

          <button onClick={handleAnalyze} disabled={loading || !file} className="btn btn-primary">
            {loading ? "Analyzing..." : "Analyze with AI"}
          </button>

          {report && (
            <div className="result-section">
              <h3>📋 AI Assessment Report</h3>
              <div className="report-content">
                <pre>{report}</pre>
              </div>
            </div>
          )}
        </div>
      )}

      {view === 'history' && (
        <div className="history-area animation-fade">
          {historyLoading ? <p>Loading history...</p> : (
            history.length === 0 ? <p>No past analysis found.</p> : (
              <div className="history-grid">
                {history.map((item) => (
                  <div key={item.id} className="history-card">
                    <div className="history-img">
                      <img 
                        src={item.image} 
                        alt="Damage" 
                        onClick={() => setSelectedImage(item.image)} 
                        title="Click to Enlarge"
                      />
                    </div>
                    <div className="history-content">
                      <h4>Description: {item.description}</h4>
                      <hr style={{borderColor:'rgba(255,255,255,0.1)'}}/>
                      <pre className="small-report">{item.ai_report}</pre>
                    </div>
                  </div>
                ))}
              </div>
            )
          )}
        </div>
      )}

      {selectedImage && (
        <div className="image-modal" onClick={() => setSelectedImage(null)}>
          <div className="modal-content">
            <span className="close-btn">&times;</span>
            <img src={selectedImage} alt="Full Size" />
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