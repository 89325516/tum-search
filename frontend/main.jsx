import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App.jsx';

// 确保API配置在window上可用（如果使用config.js）
if (typeof window !== 'undefined') {
  // 如果config.js存在，它会自动设置window.API_CONFIG
  // 否则App.jsx会使用默认配置
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);

