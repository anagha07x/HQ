import React, { useState } from 'react';
import './App.css';

function App() {
  const [file, setFile] = useState(null);
  const [uploadResponse, setUploadResponse] = useState(null);
  const [chatMessage, setChatMessage] = useState('');
  const [chatResponse, setChatResponse] = useState(null);
  const [decisions, setDecisions] = useState(null);
  const [forecastResponse, setForecastResponse] = useState(null);
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

  const generateForecast = async () => {
    if (!uploadResponse || !uploadResponse.dataset_id) {
      alert('Please upload a dataset first');
      return;
    }

    setLoading(true);
    try {
      const response = await fetch(`${API_URL}/api/forecast`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          dataset_id: uploadResponse.dataset_id,
          horizon: 30,
        }),
      });
      const data = await response.json();
      setForecastResponse(data);
    } catch (error) {
      setForecastResponse({ status: 'error', message: error.message });
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
              {uploadResponse.status === 'success' ? (
                <div className="schema-display">
                  <div className="success-message">
                    ✅ {uploadResponse.message}
                  </div>
                  
                  <div className="schema-section">
                    <h4>Dataset Information</h4>
                    <div className="info-grid">
                      <div className="info-item">
                        <span className="label">Dataset ID:</span>
                        <span className="value">{uploadResponse.dataset_id}</span>
                      </div>
                      <div className="info-item">
                        <span className="label">Total Rows:</span>
                        <span className="value">{uploadResponse.rows}</span>
                      </div>
                    </div>
                  </div>

                  <div className="schema-section">
                    <h4>All Columns ({uploadResponse.columns.length})</h4>
                    <div className="columns-list">
                      {uploadResponse.columns.map((col, idx) => (
                        <span key={idx} className="column-tag">{col}</span>
                      ))}
                    </div>
                  </div>

                  <div className="schema-section">
                    <h4>Auto-Detected Schema</h4>
                    <div className="detected-schema">
                      <div className="schema-item">
                        <span className="schema-label">📅 Date Column:</span>
                        <span className="schema-value">
                          {uploadResponse.detected_schema.date || 'Not detected'}
                        </span>
                      </div>
                      <div className="schema-item">
                        <span className="schema-label">💰 Spend Column:</span>
                        <span className="schema-value">
                          {uploadResponse.detected_schema.spend || 'Not detected'}
                        </span>
                      </div>
                      <div className="schema-item">
                        <span className="schema-label">💵 Revenue Column:</span>
                        <span className="schema-value">
                          {uploadResponse.detected_schema.revenue || 'Not detected'}
                        </span>
                      </div>
                    </div>
                  </div>

                  <details className="json-details">
                    <summary>View Raw JSON</summary>
                    <pre>{JSON.stringify(uploadResponse, null, 2)}</pre>
                  </details>
                </div>
              ) : (
                <div className="error-message">
                  ❌ Error: {uploadResponse.message}
                </div>
              )}
            </div>
          )}
        </section>

        {/* Baseline Forecast */}
        {uploadResponse && uploadResponse.status === 'success' && (
          <section className="section">
            <h2>Baseline Forecast</h2>
            <p className="section-description">
              Train a simple regression model: revenue = a × spend + b
            </p>
            <button 
              onClick={generateForecast} 
              disabled={loading}
              data-testid="generate-forecast-button"
            >
              {loading ? 'Generating...' : 'Generate Baseline Forecast'}
            </button>
            
            {forecastResponse && (
              <div className="response-box" data-testid="forecast-response">
                {forecastResponse.status === 'success' ? (
                  <div className="forecast-display">
                    <div className="success-message">
                      ✅ Baseline model trained successfully
                    </div>

                    <div className="schema-section">
                      <h4>Model Formula</h4>
                      <div className="formula-box">
                        {forecastResponse.formula}
                      </div>
                    </div>

                    <div className="schema-section">
                      <h4>Model Performance</h4>
                      <div className="metrics-grid">
                        <div className="metric-card">
                          <span className="metric-label">R² Score</span>
                          <span className="metric-value">
                            {(forecastResponse.metrics.r2 * 100).toFixed(2)}%
                          </span>
                          <span className="metric-description">
                            Model explains {(forecastResponse.metrics.r2 * 100).toFixed(1)}% of variance
                          </span>
                        </div>
                        <div className="metric-card">
                          <span className="metric-label">MAPE Error</span>
                          <span className="metric-value">
                            {forecastResponse.metrics.mape.toFixed(2)}%
                          </span>
                          <span className="metric-description">
                            Average prediction error
                          </span>
                        </div>
                      </div>
                    </div>

                    <div className="schema-section">
                      <h4>Latest Month Prediction</h4>
                      <div className="prediction-grid">
                        <div className="prediction-item">
                          <span className="pred-label">Spend:</span>
                          <span className="pred-value">
                            ${forecastResponse.latest_month.spend.toFixed(2)}
                          </span>
                        </div>
                        <div className="prediction-item">
                          <span className="pred-label">Actual Revenue:</span>
                          <span className="pred-value actual">
                            ${forecastResponse.latest_month.actual_revenue.toFixed(2)}
                          </span>
                        </div>
                        <div className="prediction-item">
                          <span className="pred-label">Predicted Revenue:</span>
                          <span className="pred-value predicted">
                            ${forecastResponse.latest_month.predicted_revenue.toFixed(2)}
                          </span>
                        </div>
                        <div className="prediction-item">
                          <span className="pred-label">Residual (Error):</span>
                          <span className={`pred-value ${forecastResponse.latest_month.residual > 0 ? 'positive' : 'negative'}`}>
                            ${forecastResponse.latest_month.residual.toFixed(2)}
                          </span>
                        </div>
                      </div>
                    </div>

                    <details className="json-details">
                      <summary>View Raw JSON</summary>
                      <pre>{JSON.stringify(forecastResponse, null, 2)}</pre>
                    </details>
                  </div>
                ) : (
                  <div className="error-message">
                    ❌ Error: {forecastResponse.message}
                  </div>
                )}
              </div>
            )}
          </section>
        )}

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
