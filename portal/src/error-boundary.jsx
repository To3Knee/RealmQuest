//=============================================================================
// File: error-boundary.jsx
// Project: RealmQuest Portal
// Version: 18.8.14
// About: Prevent blank screens by catching render errors and showing a fallback UI.
//=============================================================================

import React from "react";

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, info: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, info) {
    console.error("RealmQuest Portal Error:", error, info);
    this.setState({ info });
  }

  render() {
    if (!this.state.hasError) return this.props.children;

    const msg = this.state.error?.message || "Unknown error";
    const stack = this.state.error?.stack || "";
    const comp = this.state.info?.componentStack || "";

    return (
      <div className="min-h-screen bg-obsidian text-gray-100 flex items-center justify-center p-6">
        <div className="w-full max-w-3xl rounded-2xl border border-white/10 bg-black/40 p-6 shadow-2xl">
          <div className="text-xl font-black tracking-wide">RealmQuest Portal Error</div>
          <div className="mt-2 text-sm text-gray-400">
            A UI component crashed while rendering. The portal is still running — this screen is a safe fallback.
          </div>

          <div className="mt-4 rounded-xl border border-white/10 bg-black/50 p-4">
            <div className="text-xs font-bold uppercase tracking-widest text-gray-500">Message</div>
            <div className="mt-1 font-mono text-sm text-red-200">{msg}</div>
          </div>

          <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2">
            <div className="rounded-xl border border-white/10 bg-black/50 p-4 overflow-auto max-h-64">
              <div className="text-xs font-bold uppercase tracking-widest text-gray-500">Stack</div>
              <pre className="mt-2 whitespace-pre-wrap text-xs text-gray-300">{stack}</pre>
            </div>
            <div className="rounded-xl border border-white/10 bg-black/50 p-4 overflow-auto max-h-64">
              <div className="text-xs font-bold uppercase tracking-widest text-gray-500">Component Stack</div>
              <pre className="mt-2 whitespace-pre-wrap text-xs text-gray-300">{comp}</pre>
            </div>
          </div>

          <div className="mt-6 flex items-center justify-end gap-3">
            <button
              onClick={() => window.location.reload()}
              className="px-4 py-2 rounded-xl text-xs font-bold uppercase tracking-widest text-yellow-200 bg-yellow-500/20 hover:bg-yellow-500/30 border border-yellow-500/30"
            >
              Reload Portal
            </button>
          </div>
        </div>
      </div>
    );
  }
}
