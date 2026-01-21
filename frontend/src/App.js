import React, { useState } from 'react';
import './App.css';

function App() {
  const [file, setFile] = useState(null);
  const [uploadResponse, setUploadResponse] = useState(null);
  const [chatMessage, setChatMessage] = useState('');
  const [chatResponse, setChatResponse] = useState(null);
  const [decisions, setDecisions] = useState(null);
  const [loading, setLoading] = useState(false);

  const API_URL = process.env.REACT_APP_BACKEND_URL;

  const handleFileChange = (e) => {
    setFile(e.target.files[0]);
  };

  const handleUpload = async () => {
    if (!file) {
      alert('Please select a file first');
      return;
    }

    setLoading(true);
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch(`${API_URL}/api/upload`, {
        method: 'POST',
        body: formData,
      });
      const data = await response.json();
      setUploadResponse(data);
    } catch (error) {
      setUploadResponse({ status: 'error', message: error.message });
    } finally {
      setLoading(false);
    }
  };

  const handleChat = async () => {
    if (!chatMessage.trim()) {
      alert('Please enter a message');
      return;
    }

    setLoading(true);
    try {
      const response = await fetch(`${API_URL}/api/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: chatMessage,
          session_id: 'session_' + Date.now(),
        }),
      });
      const data = await response.json();
      setChatResponse(data);
      setChatMessage('');
    } catch (error) {
      setChatResponse({ status: 'error', message: error.message });
    } finally {
      setLoading(false);
    }
  };

  const fetchDecisions = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${API_URL}/api/decisions`);
      const data = await response.json();
      setDecisions(data);
    } catch (error) {
      setDecisions({ status: 'error', message: error.message });
    } finally {
      setLoading(false);
    }
  };

  const checkHealth = async () => {
    try {
      const response = await fetch(`${API_URL}/api/health`);
      const data = await response.json();
      alert(JSON.stringify(data, null, 2));
    } catch (error) {
      alert('Health check failed: ' + error.message);
    }
  };

  return (
    <div className="App">
      <header>
        <h1>Decision Ledger</h1>
        <p>AI-powered decision tracking and forecasting system</p>
      </header>

      <main>
        {/* Health Check */}
        <section className="section">
          <h2>System Status</h2>
          <button onClick={checkHealth}>Check Health</button>
        </section>

        {/* CSV Upload */}
        <section className="section">
          <h2>Upload CSV Dataset</h2>
          <div className="form-group">
            <input
              type="file"
              accept=".csv"
              onChange={handleFileChange}
              data-testid="file-upload-input"
            />
            <button 
              onClick={handleUpload} 
              disabled={loading}
              data-testid="upload-button"
            >
              {loading ? 'Uploading...' : 'Upload File'}
            </button>
          </div>
          {uploadResponse && (
            <div className="response-box" data-testid="upload-response">
              <h3>Upload Response:</h3>
              <pre>{JSON.stringify(uploadResponse, null, 2)}</pre>
            </div>
          )}
        </section>

        {/* Chat Interface */}
        <section className="section">
          <h2>Chat with AI Agent</h2>
          <div className="form-group">
            <input
              type="text"
              value={chatMessage}
              onChange={(e) => setChatMessage(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleChat()}
              placeholder="Ask a question about your data..."
              data-testid="chat-input"
            />
            <button 
              onClick={handleChat} 
              disabled={loading}
              data-testid="chat-button"
            >
              {loading ? 'Sending...' : 'Send'}
            </button>
          </div>
          {chatResponse && (
            <div className="response-box" data-testid="chat-response">
              <h3>Chat Response:</h3>
              <pre>{JSON.stringify(chatResponse, null, 2)}</pre>
            </div>
          )}
        </section>

        {/* View Decisions */}
        <section className="section">
          <h2>Decisions Ledger</h2>
          <button 
            onClick={fetchDecisions} 
            disabled={loading}
            data-testid="fetch-decisions-button"
          >
            {loading ? 'Loading...' : 'Fetch Decisions'}
          </button>
          {decisions && (
            <div className="response-box" data-testid="decisions-response">
              <h3>Decisions:</h3>
              <pre>{JSON.stringify(decisions, null, 2)}</pre>
            </div>
          )}
        </section>
      </main>

      <footer>
        <p>Decision Ledger MVP - Simple Preview Interface</p>
      </footer>
    </div>
  );
}

export default App;
