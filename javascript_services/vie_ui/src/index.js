import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import App from './App';
import reportWebVitals from './reportWebVitals';

// Add security headers if we're in a browser environment
if (typeof window !== 'undefined') {
  // Create a meta tag for X-Frame-Options
  const xFrameOptions = document.createElement('meta');
  xFrameOptions.httpEquiv = 'X-Frame-Options';
  xFrameOptions.content = 'DENY';
  document.head.appendChild(xFrameOptions);
  
  // Create a meta tag for Content-Security-Policy
  const csp = document.createElement('meta');
  csp.httpEquiv = 'Content-Security-Policy';
  csp.content = "frame-ancestors 'none'; default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'";
  document.head.appendChild(csp);
}

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);

// If you want to start measuring performance in your app, pass a function
// to log results (for example: reportWebVitals(console.log))
// or send to an analytics endpoint. Learn more: https://bit.ly/CRA-vitals
reportWebVitals();
