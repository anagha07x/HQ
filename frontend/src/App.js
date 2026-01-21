import React, { useState } from 'react';
import './ChanksHQ.css';

function App() {
  const [file, setFile] = useState(null);
  const [uploadResponse, setUploadResponse] = useState(null);
  const [roleMapping, setRoleMapping] = useState([]);
  const [mappingConfirmed, setMappingConfirmed] = useState(false);
  const [chatMessage, setChatMessage] = useState('');
  const [chatResponse, setChatResponse] = useState(null);
  const [decisions, setDecisions] = useState(null);
  const [forecastResponse, setForecastResponse] = useState(null);
  const [roiResponse, setRoiResponse] = useState(null);
  const [simulationResponse, setSimulationResponse] = useState(null);
  const [currentSpend, setCurrentSpend] = useState('');
  const [proposedSpend, setProposedSpend] = useState('');
  const [loading, setLoading] = useState(false);

  const API_URL = process.env.REACT_APP_BACKEND_URL;

  const handleFileChange = (e) => {
    setFile(e.target.files[0]);
    setUploadResponse(null);
    setMappingConfirmed(false);
    setRoleMapping([]);
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
      
      // Initialize role mapping from detected roles
      if (data.status === 'success' && data.column_roles) {
        setRoleMapping(data.column_roles.map(col => ({
          name: col.name,
          role: col.detected_role
        })));
      }
    } catch (error) {
      setUploadResponse({ status: 'error', message: error.message });
    } finally {
      setLoading(false);
    }
  };

  const handleRoleChange = (columnName, newRole) => {
    setRoleMapping(prev => 
      prev.map(col => 
        col.name === columnName ? { ...col, role: newRole } : col
      )
    );
  };

  const confirmRoleMapping = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${API_URL}/api/confirm-role-mapping`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          dataset_id: uploadResponse.dataset_id,
          role_mapping: roleMapping
        })
      });
      const data = await response.json();
      
      if (data.status === 'success') {
        setMappingConfirmed(true);
      } else {
        alert(`Validation failed: ${data.errors?.join(', ')}`);
      }
    } catch (error) {
      alert('Error confirming mapping: ' + error.message);
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
        headers: { 'Content-Type': 'application/json' },
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
    if (!uploadResponse?.dataset_id) {
      alert('Please upload a dataset first');
      return;
    }
    if (!mappingConfirmed) {
      alert('Please confirm column role mapping first');
      return;
    }

    setLoading(true);
    try {
      const response = await fetch(`${API_URL}/api/forecast`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
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

  const generateRoiCurve = async () => {
    if (!uploadResponse?.dataset_id) {
      alert('Please upload a dataset first');
      return;
    }
    if (!mappingConfirmed) {
      alert('Please confirm column role mapping first');
      return;
    }

    setLoading(true);
    try {
      const response = await fetch(`${API_URL}/api/roi-curve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          dataset_id: uploadResponse.dataset_id,
          horizon: 30,
        }),
      });
      const data = await response.json();
      setRoiResponse(data);
    } catch (error) {
      setRoiResponse({ status: 'error', message: error.message });
    } finally {
      setLoading(false);
    }
  };

  const runSimulation = async () => {
    if (!uploadResponse?.dataset_id) {
      alert('Please upload a dataset first');
      return;
    }

    if (!currentSpend || !proposedSpend) {
      alert('Please enter both current and proposed spend');
      return;
    }

    setLoading(true);
    try {
      const response = await fetch(`${API_URL}/api/simulate-scenario`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          dataset_id: uploadResponse.dataset_id,
          current_spend: parseFloat(currentSpend),
          proposed_spend: parseFloat(proposedSpend),
        }),
      });
      const data = await response.json();
      setSimulationResponse(data);
    } catch (error) {
      setSimulationResponse({ status: 'error', message: error.message });
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
        <h1>ChanksHQ</h1>
        <p>Decision Intelligence Platform</p>
      </header>

      <main>
        {/* System Status */}
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
          
          {uploadResponse && uploadResponse.status === 'success' && (
            <div className="response-box" data-testid="upload-response">
              <h3>Upload Response</h3>
              <div className="schema-display">
                <div className="success-message">
                  ✓ {uploadResponse.message}
                </div>
                
                <div className="schema-section">
                  <h4>Dataset Information</h4>
                  <div className="info-grid">
                    <div className="info-item">
                      <span className="label">Dataset ID</span>
                      <span className="value">{uploadResponse.dataset_id}</span>
                    </div>
                    <div className="info-item">
                      <span className="label">Total Rows</span>
                      <span className="value">{uploadResponse.rows}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}
          
          {uploadResponse && uploadResponse.status === 'error' && (
            <div className="error-message">
              ✗ Error: {uploadResponse.message}
            </div>
          )}
        </section>

        {/* Column Role Mapping */}
        {uploadResponse?.status === 'success' && uploadResponse.column_roles && !mappingConfirmed && (
          <section className="section">
            <h2>Column Role Mapping</h2>
            <p className="section-description">
              Review and adjust column roles. Exactly one TIME and OUTCOME required, at least one ACTION.
            </p>
            
            <div className="role-mapping-container">
              <div className="role-table">
                <div className="role-table-header">
                  <div>Column Name</div>
                  <div>Detected Role</div>
                  <div>Confidence</div>
                  <div>Assign Role</div>
                </div>
                
                {(uploadResponse.column_roles || []).map((col, idx) => (
                  <div key={idx} className="role-table-row">
                    <div className="role-col-name">{col.name}</div>
                    <div className="role-detected">{col.detected_role}</div>
                    <div className="role-confidence">{(col.confidence * 100).toFixed(0)}%</div>
                    <div className="role-select">
                      <select 
                        value={roleMapping.find(r => r.name === col.name)?.role || col.detected_role}
                        onChange={(e) => handleRoleChange(col.name, e.target.value)}
                      >
                        <option value="TIME">TIME</option>
                        <option value="ACTION">ACTION</option>
                        <option value="OUTCOME">OUTCOME</option>
                        <option value="METRIC">METRIC</option>
                        <option value="DIMENSION">DIMENSION</option>
                        <option value="IGNORE">IGNORE</option>
                      </select>
                    </div>
                  </div>
                ))}
              </div>
              
              <button 
                onClick={confirmRoleMapping}
                disabled={loading}
                className="confirm-mapping-btn"
                data-testid="confirm-mapping-button"
              >
                {loading ? 'Confirming...' : 'Confirm Mapping'}
              </button>
            </div>
          </section>
        )}

        {mappingConfirmed && (
          <section className="section">
            <div className="success-message">
              ✓ Column role mapping confirmed. You can now generate forecasts.
            </div>
          </section>
        )}

        {/* Baseline Forecast - Only show if mapping confirmed */}
        {mappingConfirmed && (
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
            
            {forecastResponse && forecastResponse.status === 'success' && (
              <div className="response-box" data-testid="forecast-response">
                <h3>Forecast Results</h3>
                <div className="forecast-display">
                  <div className="success-message">
                    ✓ Baseline model trained successfully
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
                        <div className="metric-label">R² Score</div>
                        <div className="metric-value">
                          {(forecastResponse.metrics.r2 * 100).toFixed(2)}%
                        </div>
                        <div className="metric-description">
                          Model explains {(forecastResponse.metrics.r2 * 100).toFixed(1)}% of variance
                        </div>
                      </div>
                      <div className="metric-card">
                        <div className="metric-label">MAPE Error</div>
                        <div className="metric-value">
                          {forecastResponse.metrics.mape.toFixed(2)}%
                        </div>
                        <div className="metric-description">
                          Average prediction error
                        </div>
                      </div>
                    </div>
                  </div>

                  <details className="json-details">
                    <summary>View Raw JSON</summary>
                    <pre>{JSON.stringify(forecastResponse, null, 2)}</pre>
                  </details>
                </div>
              </div>
            )}
            
            {forecastResponse && forecastResponse.status === 'error' && (
              <div className="error-message">
                ✗ Error: {forecastResponse.message}
              </div>
            )}
          </section>
        )}

        {/* ROI Efficiency Curve - Only show if mapping confirmed */}
        {mappingConfirmed && (
          <section className="section">
            <h2>ROI Efficiency Curve</h2>
            <p className="section-description">
              Analyze diminishing returns and find optimal spend levels
            </p>
            <button 
              onClick={generateRoiCurve} 
              disabled={loading}
              data-testid="generate-roi-button"
            >
              {loading ? 'Analyzing...' : 'Generate ROI Curve'}
            </button>
            
            {roiResponse && roiResponse.status === 'success' && (
              <div className="response-box" data-testid="roi-response">
                <h3>ROI Analysis</h3>
                <div className="roi-display">
                  <div className="success-message">
                    ✓ ROI efficiency analysis complete
                  </div>

                  <div className="schema-section">
                    <h4>Optimal Spend</h4>
                    <div className="info-item">
                      <span className="label">Recommended Spend Level</span>
                      <span className="value">${roiResponse.optimal_spend.toFixed(2)}</span>
                    </div>
                  </div>

                  <div className="schema-section">
                    <h4>Saturation Point</h4>
                    <div className="info-item">
                      <span className="label">Maximum Efficient Spend</span>
                      <span className="value">${roiResponse.saturation_spend.toFixed(2)}</span>
                    </div>
                  </div>

                  <details className="json-details">
                    <summary>View Raw JSON</summary>
                    <pre>{JSON.stringify(roiResponse, null, 2)}</pre>
                  </details>
                </div>
              </div>
            )}
            
            {roiResponse && roiResponse.status === 'error' && (
              <div className="error-message">
                ✗ Error: {roiResponse.message}
              </div>
            )}
          </section>
        )}

        {/* What-If Simulator - Only show if ROI generated */}
        {roiResponse?.status === 'success' && (
          <section className="section">
            <h2>What-If Scenario Simulator</h2>
            <p className="section-description">
              Compare expected outcomes at different spend levels
            </p>
            
            <div className="form-group">
              <input
                type="number"
                value={currentSpend}
                onChange={(e) => setCurrentSpend(e.target.value)}
                placeholder="Current Spend"
                data-testid="current-spend-input"
              />
              <input
                type="number"
                value={proposedSpend}
                onChange={(e) => setProposedSpend(e.target.value)}
                placeholder="Proposed Spend"
                data-testid="proposed-spend-input"
              />
              <button 
                onClick={runSimulation} 
                disabled={loading}
                data-testid="run-simulation-button"
              >
                {loading ? 'Simulating...' : 'Run Simulation'}
              </button>
            </div>
            
            {simulationResponse && simulationResponse.status === 'success' && (
              <div className="response-box" data-testid="simulation-response">
                <h3>Simulation Results</h3>
                <div className="simulation-display">
                  <div className="success-message">
                    ✓ Simulation complete
                  </div>

                  <div className="schema-section">
                    <h4>Incremental ROI</h4>
                    <div className="info-item">
                      <span className="label">ROI on Additional Spend</span>
                      <span className="value">{simulationResponse.impact.incremental_roi.toFixed(2)}x</span>
                    </div>
                  </div>

                  <div className="schema-section">
                    <h4>Recommendation</h4>
                    <div className="info-item">
                      <span className="label">Action</span>
                      <span className="value">{simulationResponse.recommendation.toUpperCase()}</span>
                    </div>
                  </div>

                  <details className="json-details">
                    <summary>View Raw JSON</summary>
                    <pre>{JSON.stringify(simulationResponse, null, 2)}</pre>
                  </details>
                </div>
              </div>
            )}
            
            {simulationResponse && simulationResponse.status === 'error' && (
              <div className="error-message">
                ✗ Error: {simulationResponse.message}
              </div>
            )}
          </section>
        )}
      </main>

      <footer>
        <p>ChanksHQ MVP — Terminal Interface</p>
      </footer>
    </div>
  );
}

export default App;
