//=============================================================================
// File: main.jsx
// Project: RealmQuest Portal
// Version: 18.8.14
// About: App bootstrap; mounts ErrorBoundary so UI failures render a visible error
//=============================================================================

import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App.jsx";
import ErrorBoundary from "./error-boundary.jsx";
import "./index.css";

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  </React.StrictMode>
);
