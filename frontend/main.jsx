import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App.jsx';

// Ensure API configuration is available on window (if using config.js)
if (typeof window !== 'undefined') {
  // If config.js exists, it will automatically set window.API_CONFIG
  // Otherwise App.jsx will use default configuration
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);

