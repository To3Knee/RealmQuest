//===============================================================
//Script Name: App.jsx (v18.8 - Cortex Upgrade)
//Script Location: /opt/RealmQuest/portal/src/App.jsx
//Date: 01/31/2026
//Created By: T03KNEE
//Github: https://github.com/To3Knee/RealmQuest
//Version: 18.8.21
//About: Phase 3.8.4 - Vision Archive polish: remove title from thumbnail cards; avoid duplicate title in View modal; keep View+Delete only; no UI/theme drift.
//===============================================================

import { useState, useEffect, useRef, useMemo, useCallback } from 'react'
import axios from 'axios'
import { 
  LayoutDashboard, Users, Mic2, Settings, Terminal, Play, 
  Palette, Server, Volume2, Lock, Eye, EyeOff, Plus, Save, 
  ShieldAlert, Key, Activity, RefreshCw, Power, Database, X,
  Sword, Shield, Heart, Coins, FolderOpen, CheckCircle, Sparkles, Hammer, Map, Trash2,
  BookOpen, HelpCircle, Gift, UserPlus, Music, Radio, Dices, UserCircle, 
  Image as ImageIcon, Scroll, Link as LinkIcon, Copy, Edit3, Send, Skull, Feather, Flame, Zap,
  Upload, ChevronDown, Repeat, Eraser, Crosshair, Headphones, Signal, CloudLightning,
  BrainCircuit, Eraser as WipeIcon, ShieldCheck
} from 'lucide-react'

// --- DYNAMIC CONNECTION --------------------------------------------------------
// Prefer Vite env (Docker/Compose) and fall back to same-host :8000 for bare-metal dev
const API_URL = (import.meta?.env?.VITE_API_URL) || `http://${window.location.hostname}:8000`;

// NOTE: Keep `API_URL` as the ONLY base; never hardcode http://127.0.0.1 inside views.
// ------------------------------------------------------------------------------

// --- STYLING CONSTANTS ---
const S = {
  card: "bg-[#0a0a0a]/90 backdrop-blur-md border border-[#333] rounded-xl p-6 shadow-2xl transition-all duration-300 hover:border-yellow-600/30",
  input: "w-full bg-black/50 border border-[#333] rounded-lg px-4 py-2 text-sm text-gray-200 focus:border-yellow-500 focus:outline-none focus:ring-1 focus:ring-yellow-500/50 transition-all font-mono",
  textarea: "w-full bg-black/50 border border-[#333] rounded-lg px-4 py-2 text-sm text-gray-200 focus:border-yellow-500 focus:outline-none focus:ring-1 focus:ring-yellow-500/50 transition-all font-mono resize-none",
  editableText: "bg-transparent border-b border-transparent hover:border-[#333] focus:border-yellow-600 focus:outline-none transition-colors text-center w-full",
  btnPrimary: "bg-gradient-to-r from-yellow-700 to-yellow-600 text-black font-bold uppercase tracking-widest px-6 py-3 rounded shadow-[0_0_15px_rgba(202,138,4,0.3)] hover:scale-105 hover:shadow-[0_0_25px_rgba(202,138,4,0.5)] transition-all flex items-center justify-center gap-2 text-xs cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed",
  btnSecondary: "bg-white/5 border border-white/10 text-gray-300 font-bold uppercase tracking-widest px-4 py-2 rounded hover:bg-white/10 hover:border-white/30 transition-all flex items-center justify-center gap-2 text-xs cursor-pointer",
  btnDanger: "bg-gradient-to-r from-red-700 to-red-600 text-white font-bold uppercase tracking-widest px-4 py-2 rounded shadow-[0_0_15px_rgba(220,38,38,0.25)] hover:scale-105 hover:shadow-[0_0_25px_rgba(220,38,38,0.45)] transition-all flex items-center justify-center gap-2 text-xs cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed",
  label: "block text-[10px] uppercase tracking-[0.2em] text-gray-500 font-bold mb-2",
  header: "font-cinematic text-3xl text-transparent bg-clip-text bg-gradient-to-r from-yellow-200 to-yellow-600 mb-8 drop-shadow-sm",
  sectionHeader: "font-cinematic text-xl text-white border-b border-[#333] pb-2 mb-4 flex items-center gap-2",
};

export default function App() {
  const [activeTab, setActiveTab] = useState("overview");
  const [status, setStatus] = useState("connecting");
  const [config, setConfig] = useState(null);
  const [logs, setLogs] = useState([]);
  const [systemHasPin, setSystemHasPin] = useState(false);
  const [vaultUnlocked, setVaultUnlocked] = useState(false);
  const [notification, setNotification] = useState(null);

  useEffect(() => {
    let cancelled = false;

    const init = async () => {
        try {
            await axios.get(`${API_URL}/`);
            if (!cancelled) setStatus("online");

            await refreshAuth();
            await refreshData();
        } catch (e) {
            console.error("API Connection Failed", e);
            if (!cancelled) setStatus("offline");
        }
    };

    init();

    const interval = setInterval(() => {
        refreshData();
        refreshAuth();
    }, 10000);

    return () => {
        cancelled = true;
        clearInterval(interval);
    };
}, []);

  const refreshAuth = useCallback(async () => {
    try {
        const authRes = await axios.get(`${API_URL}/system/auth/status`);
        const hasPin = !!authRes.data?.has_pin;
        const locked = !!authRes.data?.locked;

        setSystemHasPin(hasPin);
        setVaultUnlocked(!locked);
    } catch (e) {
        // If auth endpoint is unavailable, treat as no-pin/unlocked so the portal still works.
        setSystemHasPin(false);
        setVaultUnlocked(true);
    }
}, []);

const refreshData = useCallback(async () => {
    try {
        const confRes = await axios.get(`${API_URL}/system/config`);
        setConfig(confRes.data);
    } catch (e) {
        console.error("Config Sync error", e);
    }
}, []);

  const addLog = (source, message) => {
    const ts = new Date().toLocaleTimeString([], { hour12: false });
    setLogs(prev => [`[${ts}] [${source}] ${message}`, ...prev].slice(0, 50));
  };
  const notify = (msg, type = "info") => {
      setNotification({ msg, type });
      setTimeout(() => setNotification(null), 3000);
  };

  const lockExcluded = new Set(['player','chars']);

  const tabRequiresUnlock = systemHasPin && !lockExcluded.has(activeTab);
  const showLockScreen = tabRequiresUnlock && !vaultUnlocked;

  return (
    <div className="flex h-screen bg-[#050505] text-gray-200 font-sans selection:bg-yellow-600 selection:text-black overflow-hidden relative">
      <ModalHost />
      
      <aside className="w-80 border-r border-[#222] bg-[#080808] flex flex-col relative z-20 shadow-[5px_0_30px_rgba(0,0,0,0.5)]">
        <div className="p-8 pb-6 border-b border-[#111]">
          <h1 className="font-cinematic text-3xl font-bold tracking-widest text-white drop-shadow-[0_0_10px_rgba(255,255,255,0.2)]">REALM<span className="text-yellow-600">QUEST</span></h1>
          <div className="mt-4 flex items-center gap-3 text-[10px] font-mono tracking-[0.2em] uppercase text-gray-600">
             <div className={`w-2 h-2 rounded-full ${status === 'online' ? 'bg-green-500 shadow-[0_0_8px_#22c55e]' 
             : 'bg-red-500 animate-pulse'}`} /><span>v18.8.0 // {status}</span>
          </div>
        </div>
        <nav className="flex-1 px-6 space-y-2 mt-8 overflow-y-auto custom-scrollbar">
          <NavBtn icon={LayoutDashboard} label="Command Center" active={activeTab === 'overview'} onClick={() => setActiveTab('overview')} />
          <NavBtn icon={BrainCircuit} label="Cortex (AI Brain)" active={activeTab === 'cortex'} onClick={() => setActiveTab('cortex')} />
          <NavBtn icon={UserCircle} label="Player Portal" active={activeTab === 'player'} onClick={() => setActiveTab('player')} />
          <NavBtn icon={Mic2} label="Audio Matrix" active={activeTab === 'audio'} onClick={() => setActiveTab('audio')} />
          
          <div className="my-6 border-t border-[#111]" />
          
          <div className="relative group">
            <NavBtn icon={Settings} label="Neural Config" active={activeTab === 'settings'} onClick={() => setActiveTab('settings')} />
            {systemHasPin && <Lock size={14} className={`absolute right-4 top-4 ${vaultUnlocked ?
              "text-green-500/50" : "text-yellow-600/50"}`} />}
          </div>
          
          <NavBtn icon={Users} label="Hero Engine" active={activeTab === 'chars'} onClick={() => setActiveTab('chars')} />
          <NavBtn icon={Terminal} label="System Logs" active={activeTab === 'logs'} onClick={() => setActiveTab('logs')} />
        </nav>
      </aside>

      <main className="flex-1 relative flex flex-col bg-[url('https://www.transparenttextures.com/patterns/carbon-fibre.png')]">
        <div className="absolute top-[-300px] right-[-100px] w-[800px] h-[800px] bg-yellow-600/5 rounded-full blur-[150px] pointer-events-none" />
        <header className="h-20 border-b border-white/5 flex items-center justify-between px-10 bg-[#0a0a0a]/50 backdrop-blur-sm z-10">
            <h2 className="text-lg font-light tracking-[0.2em] text-gray-400 font-cinematic uppercase">// {showLockScreen ? 'Security Protocol Active' : activeTab}</h2>
            {systemHasPin && !lockExcluded.has(activeTab) && vaultUnlocked && !showLockScreen && (
                <button
                    type="button"
                    className="inline-flex items-center gap-2 px-3 py-1.5 rounded-md bg-zinc-800 hover:bg-zinc-700 text-zinc-100 text-xs border border-zinc-700"
                    title="Lock administrative pages"
                    onClick={async () => {
                        try {
                            await axios.post(`${API_URL}/system/auth/lock`);
                            setVaultUnlocked(false);
                            await refreshAuth();
                            notify("Vault locked.");
                        } catch (e) {
                            console.error("Lock error", e);
                            // Auth failures must never crash the portal.
                            notify("Failed to lock vault.", "error");
                        }
                    }}
                >
                    <Lock size={14} />
                    Seal Vault
                </button>
            )}

        </header>
        
        <div className="flex-1 overflow-auto p-10 relative z-10 custom-scrollbar">
           {showLockScreen ? (
              <LockScreen
                onUnlock={async () => {
                  setVaultUnlocked(true);
                  await refreshAuth();
                }}
                notify={notify}
              />
           ) : (
              <>
{activeTab === 'overview' && <OverviewView config={config} logs={logs} addLog={addLog} onRefresh={refreshData} notify={notify} />}
           {activeTab === 'cortex' && <CortexView notify={notify} />}
           {activeTab === 'player' && <PlayerPortalView notify={notify} addLog={addLog} config={config} />}
           {activeTab === 'settings' && <ConfigView onUpdate={refreshData} notify={notify} showLogout={systemHasPin && vaultUnlocked} onLogout={async () => { try { await axios.post(`${API_URL}/system/auth/lock`); setVaultUnlocked(false); await refreshAuth(); notify("Vault Locked"); } catch (e) { console.error("Lock error", e); notify("Failed to lock vault.", "error"); } }} />}
           {activeTab === 'audio' && <AudioMatrix config={config} onUpdate={refreshData} notify={notify} />}
           {activeTab === 'chars' && <CharacterMatrix addLog={addLog} notify={notify} />}
           {activeTab === 'logs' && <SystemLogsView notify={notify} />}
              </>
           )}

        </div>
      </main>

      {notification && (
          <div className="fixed bottom-8 right-8 z-50 animate-fade-in-up">
              <div className="bg-[#0a0a0a] border border-yellow-600/50 text-white px-6 py-4 rounded-lg shadow-2xl flex items-center gap-4">
                  <div className={`w-2 h-2 rounded-full animate-pulse ${notification.type === 'error' ? 'bg-red-500' : 'bg-yellow-500'}`} />
                  <span className="font-mono text-xs uppercase tracking-widest">{notification.msg}</span>
              </div>
          </div>
      )}
    </div>
  )
}


// === GLOBAL MODALS (NO BROWSER POPUPS) ========================================
// We keep modals centralized so any view can request confirmation/input without
// using window.confirm / window.prompt (which breaks immersion and UX).
let __rqConfirmFn = null;
let __rqPromptFn = null;

export async function rqConfirm(opts = {}) {
  if (typeof __rqConfirmFn === "function") return await __rqConfirmFn(opts);
  // If host isn't mounted yet, fail closed (safer than accidental deletes)
  return false;
}

export async function rqPrompt(opts = {}) {
  if (typeof __rqPromptFn === "function") return await __rqPromptFn(opts);
  return null;
}

function ModalHost() {
  const [confirmState, setConfirmState] = useState({ open: false, opts: null });
  const confirmResolveRef = useRef(null);

  const [promptState, setPromptState] = useState({ open: false, opts: null, value: "" });
  const promptResolveRef = useRef(null);

  const openConfirm = useCallback((opts = {}) => {
    return new Promise((resolve) => {
      confirmResolveRef.current = resolve;
      setConfirmState({
        open: true,
        opts: {
          title: opts.title ?? "Confirm",
          message: opts.message ?? "Are you sure?",
          confirmText: opts.confirmText ?? "Confirm",
          cancelText: opts.cancelText ?? "Cancel",
          danger: !!opts.danger,
        },
      });
    });
  }, []);

  const closeConfirm = useCallback((result) => {
    setConfirmState({ open: false, opts: null });
    if (confirmResolveRef.current) confirmResolveRef.current(!!result);
    confirmResolveRef.current = null;
  }, []);

  const openPrompt = useCallback((opts = {}) => {
    return new Promise((resolve) => {
      promptResolveRef.current = resolve;
      setPromptState({
        open: true,
        opts: {
          title: opts.title ?? "Input Required",
          message: opts.message ?? "",
          label: opts.label ?? "Value",
          placeholder: opts.placeholder ?? "",
          defaultValue: opts.defaultValue ?? "",
          confirmText: opts.confirmText ?? "Create",
          cancelText: opts.cancelText ?? "Cancel",
          danger: !!opts.danger,
        },
        value: (opts.defaultValue ?? "").toString(),
      });
    });
  }, []);

  const closePrompt = useCallback((valueOrNull) => {
    setPromptState({ open: false, opts: null, value: "" });
    if (promptResolveRef.current) promptResolveRef.current(valueOrNull);
    promptResolveRef.current = null;
  }, []);

  useEffect(() => {
    __rqConfirmFn = openConfirm;
    __rqPromptFn = openPrompt;
    return () => {
      __rqConfirmFn = null;
      __rqPromptFn = null;
    };
  }, [openConfirm, openPrompt]);

  // Shared modal chrome
  const Backdrop = ({ children }) => (
    <div className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/70 px-4">
      <div className="w-full max-w-lg rounded-2xl border border-white/10 bg-obsidian/95 shadow-2xl">
        {children}
      </div>
    </div>
  );

  return (
    <>
      {confirmState.open && confirmState.opts && (
        <Backdrop>
          <div className="p-6">
            <div className="text-lg font-black tracking-wide text-gray-100">
              {confirmState.opts.title}
            </div>
            <div className="mt-2 text-sm text-gray-400 whitespace-pre-line">
              {confirmState.opts.message}
            </div>

            <div className="mt-6 flex items-center justify-end gap-3">
              <button
                onClick={() => closeConfirm(false)}
                className="px-4 py-2 rounded-xl text-xs font-bold uppercase tracking-widest text-gray-300 bg-white/5 hover:bg-white/10"
              >
                {confirmState.opts.cancelText}
              </button>
              <button
                onClick={() => closeConfirm(true)}
                className={`px-4 py-2 rounded-xl text-xs font-bold uppercase tracking-widest ${
                  confirmState.opts.danger
                    ? "text-red-200 bg-red-500/20 hover:bg-red-500/30 border border-red-500/30"
                    : "text-yellow-200 bg-yellow-500/20 hover:bg-yellow-500/30 border border-yellow-500/30"
                }`}
              >
                {confirmState.opts.confirmText}
              </button>
            </div>
          </div>
        </Backdrop>
      )}

      {promptState.open && promptState.opts && (
        <Backdrop>
          <div className="p-6">
            <div className="text-lg font-black tracking-wide text-gray-100">
              {promptState.opts.title}
            </div>

            {promptState.opts.message ? (
              <div className="mt-2 text-sm text-gray-400 whitespace-pre-line">
                {promptState.opts.message}
              </div>
            ) : null}

            <div className="mt-4">
              <div className="text-[11px] font-bold uppercase tracking-widest text-gray-500">
                {promptState.opts.label}
              </div>
              <input
                autoFocus
                value={promptState.value}
                onChange={(e) => setPromptState((s) => ({ ...s, value: e.target.value }))}
                placeholder={promptState.opts.placeholder}
                className="mt-2 w-full rounded-xl bg-black/40 border border-white/10 px-3 py-2 text-sm text-gray-100 placeholder:text-gray-600 outline-none focus:border-yellow-500/40"
              />
            </div>

            <div className="mt-6 flex items-center justify-end gap-3">
              <button
                onClick={() => closePrompt(null)}
                className="px-4 py-2 rounded-xl text-xs font-bold uppercase tracking-widest text-gray-300 bg-white/5 hover:bg-white/10"
              >
                {promptState.opts.cancelText}
              </button>
              <button
                onClick={() => {
                  const v = (promptState.value ?? "").toString().trim();
                  if (!v) return;
                  closePrompt(v);
                }}
                className={`px-4 py-2 rounded-xl text-xs font-bold uppercase tracking-widest ${
                  promptState.opts.danger
                    ? "text-red-200 bg-red-500/20 hover:bg-red-500/30 border border-red-500/30"
                    : "text-yellow-200 bg-yellow-500/20 hover:bg-yellow-500/30 border border-yellow-500/30"
                }`}
              >
                {promptState.opts.confirmText}
              </button>
            </div>
          </div>
        </Backdrop>
      )}
    </>
  );
}
// ============================================================================

// -------------------------------------------------------------------------
// --- 0. CORTEX VIEW (ENHANCED: SURGICAL MEMORY TOOLS) ---
// -------------------------------------------------------------------------
function CortexView({ notify }) {
    const [subTab, setSubTab] = useState("stream"); // stream | inject | art
    const [memory, setMemory] = useState([]);
    const [systemPrompt, setSystemPrompt] = useState("");
    const [stats, setStats] = useState({ tokens: 0, turns: 0 });

    // Injection State
    const [loreText, setLoreText] = useState("");
    const [loreCat, setLoreCat] = useState("world_building");
    
    // Art State
    const [artConfig, setArtConfig] = useState({ style: "", negative_prompt: "" });
    const [artConfigSupported, setArtConfigSupported] = useState(true);

    useEffect(() => {
        fetchBrainData();
        fetchArtConfig();
        const int = setInterval(fetchBrainData, 5000);
        return () => clearInterval(int);
    }, []);

    const fetchBrainData = async () => {
        try {
            const res = await axios.get(`${API_URL}/game/brain/status`);
            setMemory(res.data.history || []);
            setSystemPrompt(res.data.system_prompt || "No Active System Prompt");
            setStats(res.data.stats || { tokens: 0, turns: 0 });
        } catch (e) {}
    };

    const fetchArtConfig = async () => {
        if (!artConfigSupported) return;
        try {
            const res = await axios.get(`${API_URL}/system/cortex/art/config`);
            if (res?.data) setArtConfig(res.data);
        } catch (e) {
            const status = e?.response?.status;
            // This endpoint may not exist in some builds; silence it to avoid log spam.
            if (status === 404) {
                setArtConfigSupported(false);
            }
        }
    };

    // --- ACTIONS ---
    
    const wipeMemory = async () => {
        if (!(await rqConfirm({ title: "Wipe Memory", message: "⚠️ WIPE ALL AI SHORT-TERM MEMORY?\n\nThis cannot be undone.", confirmText: "Wipe", cancelText: "Cancel", danger: true }))) return;
        try {
            await axios.post(`${API_URL}/game/brain/wipe`);
            notify("Memory Formatted");
            fetchBrainData();
        } catch (e) { notify("Wipe Failed", "error"); }
    };
    
    // SURGICAL DELETE (Placeholder until /game/brain/delete is mapped)
    const deleteMemory = async (index) => {
        if (!(await rqConfirm({ title: "Delete Memory Item", message: "Surgically remove this thought?", confirmText: "Delete", cancelText: "Cancel", danger: true }))) return;
        // NOTE: Since we don't have the chat_engine code to add the DELETE endpoint yet,
        // we simulate it or call the future endpoint. 
        // For now, let's notify the user this is ready for the backend hook.
        try {
             // await axios.delete(`${API_URL}/game/brain/memory/${index}`);
             notify("Surgical Scalpel applied (Backend Hook Pending)");
             // Optimistic update for UI feel
             const newMem = [...memory];
             newMem.splice(index, 1);
             setMemory(newMem);
        } catch(e) { notify("Surgical Error", "error"); }
    };

    const updatePrompt = async () => {
        try {
            await axios.post(`${API_URL}/game/brain/prompt`, { prompt: systemPrompt });
            notify("Guardrails Updated");
        } catch (e) { notify("Update Failed", "error"); }
    };

    const injectLore = async () => {
        if(!loreText) return;
        try {
            await axios.post(`${API_URL}/system/cortex/inject`, { content: loreText, category: loreCat });
            notify("Lore Injected into Vector DB");
            setLoreText("");
        } catch(e) { notify("Injection Failed", "error"); }
    };

    const saveArtConfig = async () => {
        try {
            await axios.post(`${API_URL}/system/cortex/art/config`, artConfig);
            notify("Art Director Settings Saved");
        } catch(e) { notify("Save Failed", "error"); }
    };

    return (
        <div className="max-w-7xl mx-auto pb-20 animate-fade-in">
             <div className="flex justify-between items-end mb-8">
                <div>
                    <h2 className={S.header + " mb-2"}>Cortex Control</h2>
                    <p className="text-xs font-mono text-gray-500 uppercase tracking-widest">
                        COGNITIVE LOAD: <span className="text-yellow-500 font-bold">{stats.tokens} TOKENS</span> // TURNS: {stats.turns}
                    </p>
                </div>
                {/* SUB TABS */}
                <div className="flex bg-white/5 rounded p-1 border border-white/10">
                    {['stream', 'inject', 'art'].map(t => (
                        <button key={t} onClick={() => setSubTab(t)} className={`px-4 py-2 text-xs font-bold uppercase rounded transition-all ${subTab === t ? 'bg-yellow-600 text-black shadow-lg' : 'text-gray-400 hover:text-white'}`}>
                            {t}
                        </button>
                    ))}
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                {/* LEFT COLUMN: CONTROLS */}
                <div className={`${S.card} lg:col-span-1 flex flex-col`}>
                    <h3 className={S.sectionHeader}><ShieldCheck size={18}/> Active Guardrails</h3>
                    <p className="text-xs text-gray-500 mb-4">The core instructions driving the DM persona.</p>
                    <textarea 
                        className="flex-1 bg-black/50 border border-[#333] rounded p-4 font-mono text-[10px] text-gray-300 leading-relaxed resize-none focus:border-yellow-600 focus:outline-none mb-4 min-h-[400px]"
                        value={systemPrompt}
                        onChange={(e) => setSystemPrompt(e.target.value)}
                    />
                    <div className="flex flex-col gap-2">
                        <button onClick={updatePrompt} className={S.btnPrimary}><Save size={14}/> Update Guardrails</button>
                        <button onClick={wipeMemory} className="w-full py-3 bg-red-900/20 border border-red-500/30 text-red-500 rounded hover:bg-red-500 hover:text-white transition-all text-xs font-bold uppercase tracking-widest flex items-center justify-center gap-2">
                            <WipeIcon size={14} /> Wipe All Memory
                        </button>
                    </div>
                </div>

                {/* RIGHT COLUMN: DYNAMIC CONTENT */}
                <div className={`${S.card} lg:col-span-2 flex flex-col`}>
                    
                    {/* VIEW 1: MEMORY STREAM (With Surgical Delete) */}
                    {subTab === 'stream' && (
                        <>
                            <h3 className={S.sectionHeader}><Activity size={18}/> Cognitive Stream</h3>
                            <div className="flex-1 bg-black/50 border border-[#333] rounded p-4 overflow-auto custom-scrollbar space-y-4 max-h-[600px]">
                                {memory.length === 0 && <div className="text-center text-gray-600 text-xs py-10">Memory Empty (Tabula Rasa)</div>}
                                {memory.map((m, i) => (
                                    <div key={i} className={`flex gap-4 group ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                                        {/* AI DELETE BUTTON */}
                                        {m.role !== 'user' && (
                                            <button onClick={() => deleteMemory(i)} className="opacity-0 group-hover:opacity-100 text-red-500 hover:text-red-400 p-2"><Trash2 size={12}/></button>
                                        )}
                                        
                                        <div className={`max-w-[80%] p-3 rounded border text-xs leading-relaxed ${
                                            m.role === 'user' 
                                            ? 'bg-blue-900/10 border-blue-500/30 text-blue-200 rounded-tr-none' 
                                            : 'bg-yellow-900/10 border-yellow-600/30 text-yellow-100 rounded-tl-none'
                                        }`}>
                                            <div className="text-[9px] font-bold uppercase tracking-widest opacity-50 mb-1">{m.role}</div>
                                            {m.content}
                                        </div>

                                        {/* USER DELETE BUTTON */}
                                        {m.role === 'user' && (
                                            <button onClick={() => deleteMemory(i)} className="opacity-0 group-hover:opacity-100 text-red-500 hover:text-red-400 p-2"><Trash2 size={12}/></button>
                                        )}
                                    </div>
                                ))}
                            </div>
                        </>
                    )}

                    {/* VIEW 2: LORE INJECTION */}
                    {subTab === 'inject' && (
                        <div className="animate-fade-in h-full flex flex-col">
                            <h3 className={S.sectionHeader}><BrainCircuit size={18}/> Lore Injection</h3>
                            <p className="text-xs text-gray-500 mb-6">Manually insert facts into the Vector Database. The AI will recall this context forever.</p>
                            
                            <div className="mb-4">
                                <label className={S.label}>Category / Tag</label>
                                <select className={S.input} value={loreCat} onChange={e => setLoreCat(e.target.value)}>
                                    <option value="world_building">World Building</option>
                                    <option value="npc_bio">NPC Biography</option>
                                    <option value="quest_log">Quest Log</option>
                                    <option value="rules">House Rules</option>
                                </select>
                            </div>

                            <div className="flex-1 mb-4">
                                <label className={S.label}>Lore Content</label>
                                <textarea 
                                    className="w-full h-full bg-black/50 border border-[#333] rounded p-4 font-mono text-sm text-white focus:border-yellow-600 focus:outline-none resize-none"
                                    placeholder="e.g., The collision stone glows blue when orcs are nearby..."
                                    value={loreText}
                                    onChange={e => setLoreText(e.target.value)}
                                />
                            </div>

                            <button onClick={injectLore} disabled={!loreText} className={S.btnPrimary}>
                                <Upload size={16} /> Inject Memory
                            </button>
                        </div>
                    )}

                    {/* VIEW 3: ART DIRECTOR */}
                    {subTab === 'art' && (
                         <div className="animate-fade-in h-full flex flex-col">
                            <h3 className={S.sectionHeader}><Palette size={18}/> Art Director</h3>
                            <p className="text-xs text-gray-500 mb-6">Configure the default parameters for image generation.</p>

                            <div className="space-y-6">
                                <div>
                                    <label className={S.label}>Base Style Prompt (Prefix)</label>
                                    <textarea 
                                        className={S.input + " min-h-[100px]"}
                                        value={artConfig.style}
                                        onChange={e => setArtConfig({...artConfig, style: e.target.value})}
                                        placeholder="e.g., Cinematic fantasy oil painting, 8k resolution, dramatic lighting..."
                                    />
                                </div>

                                <div>
                                    <label className={S.label}>Negative Prompt (Avoid)</label>
                                    <textarea 
                                        className={S.input + " min-h-[100px] border-red-900/30 focus:border-red-500"}
                                        value={artConfig.negative_prompt}
                                        onChange={e => setArtConfig({...artConfig, negative_prompt: e.target.value})}
                                        placeholder="e.g., blurry, text, watermark, bad anatomy, modern cars..."
                                    />
                                </div>
                            </div>
                            
                            <div className="mt-auto pt-6">
                                <button onClick={saveArtConfig} className={S.btnPrimary + " w-full"}>
                                    <Save size={16} /> Save Art Config
                                </button>
                            </div>
                        </div>
                    )}

                </div>
            </div>
        </div>
    )
}

// -------------------------------------------------------------------------
// --- 1. OVERVIEW (COMMAND CENTER) ---
// -------------------------------------------------------------------------
function OverviewView({ config, logs = [], addLog, onRefresh, notify }) {
    const [logModal, setLogModal] = useState(null);
    const [campaignModal, setCampaignModal] = useState(false);
    const [discordMembers, setDiscordMembers] = useState([]);

    // FETCH DISCORD MEMBERS
    useEffect(() => {
        const fetchDiscord = async () => {
            try {
                // Hitting the real endpoint now
                const res = await axios.get(`${API_URL}/game/discord/members`);
                setDiscordMembers(res.data || []);
            } catch (e) {
                // Fallback mock if API fails/offline
                setDiscordMembers([
                    {id: 1, name: "T03KNEE", status: "online", role: "DM"},
                    {id: 2, name: "API_Offline", status: "dnd", role: "System"}
                ]);
            }
        };
        fetchDiscord();
        const interval = setInterval(fetchDiscord, 15000); // Poll every 15s
        return () => clearInterval(interval);
    }, []);

    // SYSTEM ACTIONS
    const restart = async (svc) => { 
        addLog("SYS", `Restarting ${svc}...`); 
        try { 
            await axios.post(`${API_URL}/system/control/restart/${svc}`); 
            addLog("SYS", `✅ ${svc} Restarted.`); 
            notify(`${svc} Restart Triggered`);
        } catch (e) { 
            addLog("ERR", `Failed: ${svc}`); 
            notify(`Restart Failed: ${svc}`, "error");
        } 
    };
    
    const restartAll = async () => { 
        if (!(await rqConfirm({ title: "Restart Stack", message: "Restart ENTIRE Stack?", confirmText: "Restart", cancelText: "Cancel", danger: true }))) return;
        addLog("SYS", "⚠️ INITIATING FULL STACK RESTART"); 
        ["bot", "api", "kenku", "scribe", "chroma", "mongo", "redis", "portal"].forEach(s => restart(s)); 
    };
    
    const campaignName = config?.active_campaign?.replace(/_/g, ' ').toUpperCase() || "NONE";

    return (
        <div className="space-y-8 animate-fade-in pb-20">
            {/* STATS */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                <StatusCard title="LLM Brain" value={config?.llm_provider?.split('-')[0] || "ONLINE"} icon={Activity} color="text-yellow-400" />
                <StatusCard title="Art Engine" value={config?.art_style || "Standard"} icon={Palette} color="text-purple-400" />
                <StatusCard title="Voice Synth" value="ElevenLabs" icon={Volume2} color="text-green-400" />
                <div onClick={() => setCampaignModal(true)} className="bg-[#0a0a0a]/80 backdrop-blur-md border border-[#333] rounded-xl p-6 shadow-2xl transition-all duration-300 flex flex-col items-center justify-center text-center group min-h-[160px] relative overflow-hidden cursor-pointer hover:border-blue-500/50 hover:bg-white/5 active:scale-95">
                    <Map size={32} className="text-blue-400 mb-4 group-hover:scale-110 transition-transform" />
                    <h3 className="text-[9px] uppercase tracking-[0.2em] text-gray-500 mb-2">Active Campaign</h3>
                    <p className="font-cinematic text-lg text-white mb-2">{campaignName}</p>
                    <span className="text-[9px] font-bold bg-blue-900/30 text-blue-400 px-3 py-1 rounded border border-blue-500/30 uppercase tracking-widest group-hover:bg-blue-500 group-hover:text-black transition-colors">Switch</span>
                </div>
            </div>

            {/* MAIN CONTENT */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                 {/* CONTAINER OPS */}
                 <div className={`${S.card} lg:col-span-2 min-h-[400px]`}>
                    <div className="flex justify-between items-center mb-6"><div><h3 className="font-cinematic text-xl text-white">Container Operations</h3><p className="text-xs text-gray-500 mt-2">Manage lifecycle and telemetry.</p></div><button onClick={restartAll} className="px-4 py-2 bg-red-900/30 border border-red-500/50 rounded hover:bg-red-500 hover:text-white transition-all text-[10px] uppercase font-bold flex items-center gap-2"><Power size={14} /> Restart Stack</button></div>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <ServiceRow name="Neural Net (Bot)" id="rq-bot" onRestart={restart} onViewLogs={() => setLogModal("rq-bot")} />
                        <ServiceRow name="API Gateway" id="rq-api" onRestart={restart} onViewLogs={() => setLogModal("rq-api")} />
                        <ServiceRow name="Kenku Bridge" id="rq-kenku" onRestart={restart} onViewLogs={() => setLogModal("rq-kenku")} />
                        <ServiceRow name="Audio Scribe" id="rq-scribe" onRestart={restart} onViewLogs={() => setLogModal("rq-scribe")} />
                        <ServiceRow name="Chroma Vector DB" id="rq-chroma" onRestart={restart} onViewLogs={() => setLogModal("rq-chroma")} />
                        <ServiceRow name="Mongo DB" id="rq-mongo" onRestart={restart} onViewLogs={() => setLogModal("rq-mongo")} />
                        <ServiceRow name="Redis Cache" id="rq-redis" onRestart={restart} onViewLogs={() => setLogModal("rq-redis")} />
                        <ServiceRow name="Portal UI" id="rq-portal" onRestart={restart} onViewLogs={() => setLogModal("rq-portal")} />
                    </div>
                </div>

                {/* RIGHT COLUMN */}
                <div className="space-y-8">
                    {/* DISCORD LIVE */}
                    <div className={`${S.card} relative overflow-hidden`}>
                        <h3 className="text-indigo-400 font-mono text-xs uppercase tracking-widest mb-6 flex items-center gap-2"><Signal size={14} /> Discord Uplink</h3>
                        <div className="space-y-3 max-h-[200px] overflow-auto custom-scrollbar">
                            {discordMembers.length === 0 && <span className="text-xs text-gray-600">No Signal...</span>}
                            {discordMembers.map((m, i) => <DiscordUserRow key={i} name={m.name} status={m.status} role={m.role} />)}
                        </div>
                    </div>

                    {/* COMMAND LOG */}
                    <div className={`${S.card} relative overflow-hidden h-[300px] flex flex-col`}>
                        <h3 className="text-yellow-600 font-mono text-xs uppercase tracking-widest mb-4 flex items-center gap-2"><Terminal size={14} /> Command Log</h3>
                        <div className="flex-1 bg-black/40 rounded border border-white/5 p-4 font-mono text-[10px] text-gray-400 overflow-auto custom-scrollbar">
                            {(logs || []).map((log, i) => (<div key={i} className="mb-2 border-l-2 border-yellow-900/30 pl-3 hover:bg-white/5"><span className="text-yellow-600 mr-2">{log.split(']')[0]}]</span><span className={log.includes("ERR") ? "text-red-400" : "text-gray-300"}>{log.split(']').slice(1).join(']')}</span></div>))}
                        </div>
                    </div>
                </div>
            </div>

            {logModal && <LogTerminal service={logModal} onClose={() => setLogModal(null)} isModal={true} />}
            {campaignModal && <CampaignSelector current={config?.active_campaign} onClose={() => setCampaignModal(false)} onSelect={() => { onRefresh(); notify("Campaign Switched"); }} notify={notify} />}
        </div>
    )
}

function DiscordUserRow({ name, status, role }) {
    const statusColor = { online: "bg-green-500", idle: "bg-yellow-500", dnd: "bg-red-500", offline: "bg-gray-700" };
    return (
        <div className="flex items-center justify-between bg-black/40 p-3 rounded border border-white/5">
            <div className="flex items-center gap-3">
                <div className="relative">
                    <div className="w-8 h-8 rounded-full bg-indigo-900 flex items-center justify-center text-xs font-bold text-white border border-indigo-500/30">{name.charAt(0)}</div>
                    <div className={`absolute bottom-0 right-0 w-2.5 h-2.5 rounded-full border border-black ${statusColor[status] || "bg-gray-500"}`} />
                </div>
                <div>
                    <div className="text-xs font-bold text-gray-200">{name}</div>
                    <div className="text-[9px] text-gray-500 uppercase tracking-wider">{status}</div>
                </div>
            </div>
            <span className="text-[9px] font-mono bg-white/5 px-2 py-1 rounded text-gray-400">{role}</span>
        </div>
    )
}

// -------------------------------------------------------------------------
// --- 2. AUDIO MATRIX (SYNC ENABLED) ---
// -------------------------------------------------------------------------
function AudioMatrix({ config, onUpdate, notify }) {
    const [voices, setVoices] = useState([]);
    const [kenkuAssets, setKenkuAssets] = useState([]);
    const [syncing, setSyncing] = useState(false);
    const [dirty, setDirty] = useState(false);

    // Local editable state mirrors config.audio_registry
    const [dmName, setDmName] = useState("DM");
    const [dmVoice, setDmVoice] = useState("");
    const [archetypes, setArchetypes] = useState([]);
    const [soundscapes, setSoundscapes] = useState([]);

    const ensureDefaults = (reg) => {
        const base = reg || {};
        return {
            dmName: base.dmName ?? "DM",
            dmVoice: base.dmVoice ?? "",
            archetypes: Array.isArray(base.archetypes) ? base.archetypes : [],
            soundscapes: Array.isArray(base.soundscapes) ? base.soundscapes : [],
        };
    };

    // INITIAL LOAD / RESYNC (do not clobber unsaved edits)
    useEffect(() => {
        const reg = ensureDefaults(config?.audio_registry);
        if (!dirty) {
            setDmName(reg.dmName);
            setDmVoice(reg.dmVoice);
            setArchetypes(reg.archetypes);
            setSoundscapes(reg.soundscapes);
        }
        // Always refresh the selectable asset lists.
        syncAudioAssets();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [config?.audio_registry]);

    const syncAudioAssets = async () => {
        setSyncing(true);
        try {
            // HIT REAL ENDPOINTS
            const [vRes, kRes] = await Promise.all([
                axios.get(`${API_URL}/system/audio/voices`),
                axios.get(`${API_URL}/system/audio/kenku/tracks`)
            ]);
            setVoices(vRes.data || []);
            setKenkuAssets(kRes.data || []);
            notify("Audio Assets Synced");
        } catch(e) {
            console.error(e);
            notify("Sync Failed - Using Offline Cache", "error");
            // FALLBACK DATA FOR UI TESTING
            setVoices([{id: "1", name: "Offline Voice 1"}, {id: "2", name: "Offline Voice 2"}]);
            setKenkuAssets([{id: "1", name: "Offline Track 1"}]);
        }
        setSyncing(false);
    };

    const makeId = (prefix) => {
        // Stable enough for UI + persistence; backend requires non-empty id.
        return `${prefix}_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 7)}`;
    };

    const addArchetype = () => {
        setDirty(true);
        setArchetypes((prev) => ([
            ...(prev || []),
            { id: makeId("archetype"), label: "New Trigger", voice_id: "" }
        ]));
    };

    const addSoundscape = () => {
        setDirty(true);
        setSoundscapes((prev) => ([
            ...(prev || []),
            { id: makeId("soundscape"), label: "New Soundscape", track_id: "" }
        ]));
    };


    const removeArchetype = (idx) => {
        setDirty(true);
        setArchetypes((prev) => (prev || []).filter((_, i) => i !== idx));
    };

    const removeSoundscape = (idx) => {
        setDirty(true);
        setSoundscapes((prev) => (prev || []).filter((_, i) => i !== idx));
    };

    const saveMapping = async () => {
        try {
            await axios.post(`${API_URL}/system/audio/save`, { dmName, dmVoice, archetypes, soundscapes });
            setDirty(false);
            notify("Audio Registry Saved");
            onUpdate && onUpdate();
        } catch(e) { notify("Save Failed", "error"); }
    };

    return (
        <div className="max-w-7xl mx-auto pb-20 animate-fade-in">
            <div className="flex justify-between items-end mb-8">
                <div>
                    <h2 className={S.header + " mb-2"}>Audio Matrix</h2>
                    <p className="text-xs font-mono text-gray-500 uppercase tracking-widest">
                        CONFIGURING FOR: <span className="text-yellow-500 font-bold">{config?.active_campaign?.toUpperCase() || "GLOBAL"}</span>
                    </p>
                </div>
                <div className="flex gap-4">
                    <button onClick={syncAudioAssets} disabled={syncing} className={S.btnSecondary}>
                        <CloudLightning size={14} className={syncing ? "animate-pulse" : ""} /> {syncing ? "Syncing..." : "Sync Cloud"}
                    </button>
                    <button onClick={saveMapping} className={S.btnPrimary}><Save size={14} /> Save Configuration</button>
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                {/* 1. DM OVERRIDE */}
                <div className={`${S.card} col-span-1 lg:col-span-3 border-yellow-600/30 bg-yellow-900/5`}>
                     <div className="flex items-center gap-4">
                         <div className="p-4 bg-yellow-600/20 rounded-full text-yellow-500"><Mic2 size={32}/></div>
                         <div className="flex-1">
                             <h3 className="font-cinematic text-xl text-white">Dungeon Master Voice</h3>
                             <p className="text-xs text-gray-500 mb-2">The primary narrator voice for this campaign. (ElevenLabs)</p>
                             <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-3">
                                 <div className="md:col-span-1">
                                     <label className="text-[9px] uppercase font-bold text-gray-500 block mb-1">Bot Name / Wake Word</label>
                                     <input
                                         className={S.input + " text-xs"}
                                         value={dmName}
                                         onChange={(e) => { setDirty(true); setDmName(e.target.value); }}
                                         placeholder="DM"
                                     />
                                 </div>
                                 <div className="md:col-span-2">
                                     <label className="text-[9px] uppercase font-bold text-gray-500 block mb-1">DM Voice</label>
                                     <select className={S.input} value={dmVoice} onChange={e => { setDirty(true); setDmVoice(e.target.value); }}>
                                         <option value="">-- Select Voice --</option>
                                         {voices.map(v => <option key={v.id} value={v.id}>{v.name}</option>)}
                                     </select>
                                 </div>
                             </div>
                         </div>
                     </div>
                </div>

                {/* 2. CASTING (ARCHETYPES) */}
                <div className={S.card}>
                    <h3 className={S.sectionHeader}><Users size={18}/> Casting Director</h3>
                    <p className="text-xs text-gray-500 mb-6">Map stereotypes to ElevenLabs voices.</p>
                    <div className="space-y-4">
                        {archetypes.map((arch, i) => (
                            <div key={arch.id || i} className="bg-black/40 p-3 rounded border border-white/5">
                                <label className="text-[9px] uppercase font-bold text-gray-500 block mb-1">Trigger Name</label>
                                <input
                                    className={S.input + " text-xs py-1 mb-2"}
                                    value={arch.label || ""}
                                    onChange={(e) => {
                                        setDirty(true);
                                        const newArr = [...archetypes];
                                        newArr[i] = { ...newArr[i], label: e.target.value };
                                        setArchetypes(newArr);
                                    }}
                                    placeholder="The Villain"
                                />
                                <div className="flex gap-2">
                                    <select className={S.input + " text-xs py-1"} value={arch.voice_id} onChange={(e) => {
                                        setDirty(true);
                                        const newArr = [...archetypes];
                                        newArr[i] = { ...newArr[i], voice_id: e.target.value };
                                        setArchetypes(newArr);
                                    }}>
                                        <option value="">-- Assign Voice --</option>
                                        {voices.map(v => <option key={v.id} value={v.id}>{v.name}</option>)}
                                    </select>
                                    <button className="p-2 bg-white/5 hover:bg-white/10 rounded"><Play size={12} /></button>
                                <button className="p-2 bg-red-700 hover:bg-red-600 rounded" onClick={() => removeArchetype(i)} title="Delete trigger"><Trash2 size={12} /></button>
                                </div>
                            </div>
                        ))}
                         <button onClick={addArchetype} className="w-full py-2 border border-dashed border-white/10 rounded text-xs text-gray-500 hover:text-white hover:border-white/30 transition-all">+ Add Trigger</button>
                    </div>
                </div>

                {/* 3. SOUNDSCAPES (KENKU) */}
                <div className={S.card}>
                    <h3 className={S.sectionHeader}><Music size={18}/> Kenku Soundscapes</h3>
                    <p className="text-xs text-gray-500 mb-6">Map game states to Kenku FM tracks.</p>
                    <div className="space-y-4">
                        {soundscapes.map((scape, i) => (
                            <div key={scape.id || i} className="bg-black/40 p-3 rounded border border-white/5">
                                <label className="text-[9px] uppercase font-bold text-blue-500 block mb-1">Soundscape Name</label>
                                <input
                                    className={S.input + " text-xs py-1 mb-2"}
                                    value={scape.label || ""}
                                    onChange={(e) => {
                                        setDirty(true);
                                        const newArr = [...soundscapes];
                                        newArr[i] = { ...newArr[i], label: e.target.value };
                                        setSoundscapes(newArr);
                                    }}
                                    placeholder="Tavern Ambience"
                                />
                                <div className="flex gap-2">
                                    <select className={S.input + " text-xs py-1"} value={scape.track_id} onChange={(e) => {
                                        setDirty(true);
                                        const newArr = [...soundscapes];
                                        newArr[i] = { ...newArr[i], track_id: e.target.value };
                                        setSoundscapes(newArr);
                                    }}>
                                        <option value="">-- Assign Track --</option>
                                        {kenkuAssets.map(k => <option key={k.id} value={k.id}>{k.name}</option>)}
                                    </select>
                                    <button className="p-2 bg-white/5 hover:bg-white/10 rounded"><Headphones size={12} /></button>
                                <button className="p-2 bg-red-700 hover:bg-red-600 rounded" onClick={() => removeSoundscape(i)} title="Delete soundscape"><Trash2 size={12} /></button>
                                </div>
                            </div>
                        ))}
                        <button onClick={addSoundscape} className="w-full py-2 border border-dashed border-white/10 rounded text-xs text-gray-500 hover:text-white hover:border-white/30 transition-all">+ Add Soundscape</button>
                    </div>
                </div>
            </div>
        </div>
    )
}

// -------------------------------------------------------------------------
// --- 3. NEURAL CONFIG (SAFE MODE) ---
// -------------------------------------------------------------------------
function ConfigView({ onUpdate, notify, showLogout = false, onLogout }) {
    const [envData, setEnvData] = useState([]);
    const [loading, setLoading] = useState(true);
    const [newKey, setNewKey] = useState("");
    const [newVal, setNewVal] = useState("");
    const [visible, setVisible] = useState({});

    useEffect(() => {
        const fetchEnv = async () => {
            try {
                const res = await axios.get(`${API_URL}/system/env/all`);
                setEnvData(res.data || []);
            } catch (e) {
                console.error(e);
                notify("Failed to load .env", "error");
                setEnvData([]); // Prevent crash
            }
            setLoading(false);
        };
        fetchEnv();
    }, []);

    const toggleVis = (k) => setVisible(p => ({...p, [k]: !p[k]}));
    
    const handleDelete = async (key) => {
        if (await rqConfirm({ title: "Delete Variable", message: `Delete ${key} from .env?\n\nThis cannot be undone.`, confirmText: "Delete", cancelText: "Cancel", danger: true })) {
            try {
                await axios.delete(`${API_URL}/system/env/${key}`);
                setEnvData(prev => prev.filter(item => item.key !== key));
                notify(`${key} Deleted`);
            } catch(e) { notify("Delete Failed", "error"); }
        }
    };

    const handleSaveRow = async (key, val) => {
        try {
			await axios.post(`${API_URL}/system/env`, { key, value: val });
            notify(`${key} Updated`);
        } catch(e) { notify("Update Failed", "error"); }
    };

    const handleAdd = async () => {
        if(newKey && newVal) {
            try {
				const k = newKey.toUpperCase();
				await axios.post(`${API_URL}/system/env`, { key: k, value: newVal });
				setEnvData([...envData, {key: k, value: newVal}]);
                setNewKey(""); setNewVal("");
                notify("Variable Added");
            } catch(e) { notify("Add Failed", "error"); }
        }
    };

    if (loading) return <div className="text-center mt-20 text-yellow-600 animate-pulse font-mono">DECRYPTING NEURAL CONFIG...</div>;

    return (
        <div className="max-w-5xl mx-auto pb-20 animate-fade-in">
            <h2 className={S.header}>Neural Configuration</h2>
            <div className={S.card}>
                {/* HEADER ROW WITH SECURE LOGOUT */}
                <div className="flex justify-between items-start mb-6 pb-6 border-b border-white/5">
                    <div>
                        <h3 className="font-cinematic text-xl text-white">Environment Vault (.env)</h3>
                        <p className="text-xs text-red-400 font-mono mt-2 flex items-center gap-2"><ShieldAlert size={12}/> RESTRICTED ACCESS: SENSITIVE SECRETS</p>
                    </div>
                    
                    {showLogout && (
                        <button
                            onClick={async () => {
                                try { if (onLogout) await onLogout(); } catch (e) {}
                            }}
                            className="group flex flex-col items-center gap-1 opacity-80 hover:opacity-100 transition-opacity"
                            title="Seal Vault (Logout)"
                        >
                            <div className="w-12 h-12 rounded-full bg-red-900/20 border border-red-500/30 flex items-center justify-center group-hover:bg-red-500 group-hover:text-black group-hover:border-red-500 group-hover:shadow-[0_0_20px_rgba(220,38,38,0.5)] transition-all text-red-500">
                                <Lock size={20} />
                            </div>
                            <span className="text-[9px] uppercase tracking-widest text-red-500 font-bold group-hover:text-red-400">SEAL VAULT</span>
                        </button>
                    )}
                </div>

                {/* TABLE HEADER */}
                <div className="grid grid-cols-12 gap-4 mb-2 px-4 text-[10px] uppercase font-bold text-gray-500 tracking-widest">
                    <div className="col-span-4">Variable Key</div>
                    <div className="col-span-7">Value</div>
                    <div className="col-span-1 text-right">Action</div>
                </div>

                {/* ROWS */}
                <div className="space-y-2 mb-8">
                    {envData.length === 0 && <div className="text-center text-gray-600 font-mono text-xs py-4">No Variables Found (Check API Connection)</div>}
                    {envData.map((item, i) => (
                        <div key={i} className="grid grid-cols-12 gap-4 bg-black/40 p-3 rounded border border-white/5 items-center hover:border-yellow-600/30 transition-colors group">
                            <div className="col-span-4 font-mono text-xs text-yellow-600 truncate" title={item.key}>
                                {item.key}
                            </div>
                            <div className="col-span-7 relative">
                                <input 
                                    className="w-full bg-transparent border-none text-xs text-gray-300 font-mono focus:outline-none"
                                    type={visible[item.key] ? "text" : "password"}
                                    defaultValue={item.value}
                                    onBlur={(e) => handleSaveRow(item.key, e.target.value)}
                                />
                                <button onClick={() => toggleVis(item.key)} className="absolute right-0 top-1/2 -translate-y-1/2 text-gray-600 hover:text-white p-1">
                                    {visible[item.key] ? <EyeOff size={12}/> : <Eye size={12}/>}
                                </button>
                            </div>
                            <div className="col-span-1 text-right">
                                <button onClick={() => handleDelete(item.key)} className="text-gray-600 hover:text-red-500 transition-colors">
                                    <Trash2 size={14} />
                                </button>
                            </div>
                        </div>
                    ))}
                </div>

                {/* ADD NEW */}
                <div className="bg-white/5 p-4 rounded-lg border border-dashed border-white/10 flex gap-4 items-center">
                    <Plus size={16} className="text-gray-500" />
                    <input className={S.input} placeholder="NEW_KEY_NAME" value={newKey} onChange={e => setNewKey(e.target.value.toUpperCase())} />
                    <input className={S.input} placeholder="Value" type="password" value={newVal} onChange={e => setNewVal(e.target.value)} />
                    <button onClick={handleAdd} disabled={!newKey || !newVal} className={S.btnPrimary}>Add</button>
                </div>
            </div>
        </div>
    )
}

function LockScreen({ onUnlock, notify }) {
    const [pin, setPin] = useState("");
    const [loading, setLoading] = useState(false);

    const attemptUnlock = async () => {
        if(!pin) return;
        setLoading(true);
        try {
            await axios.post(`${API_URL}/system/auth/unlock`, { pin });
            onUnlock();
            notify("Vault Access Granted");
        } catch(e) {
            notify("Access Denied", "error");
            setPin("");
        }
        setLoading(false);
    };

    return (
        <div className="flex flex-col items-center justify-center h-[60vh] animate-fade-in">
            <div className="bg-[#0a0a0a] border border-yellow-600/30 p-10 rounded-2xl shadow-[0_0_50px_rgba(202,138,4,0.1)] text-center relative overflow-hidden">
                <div className="absolute inset-0 bg-yellow-600/5 blur-xl pointer-events-none" />
                <Lock size={48} className="text-yellow-600 mx-auto mb-6" />
                <h2 className="font-cinematic text-3xl text-white mb-2">Security Challenge</h2>
                <p className="text-xs font-mono text-gray-500 uppercase tracking-widest mb-8">Restricted Access // PIN Required</p>
                
                <input 
                    type="password" 
                    autoFocus
                    className="bg-black/50 border border-[#333] rounded px-4 py-3 text-center text-2xl font-mono text-white tracking-[0.5em] w-64 focus:border-yellow-600 focus:outline-none focus:shadow-[0_0_15px_rgba(202,138,4,0.3)] mb-6 placeholder-gray-800"
                    placeholder="••••"
                    value={pin}
                    onChange={e => setPin(e.target.value)}
                    onKeyDown={e => e.key === 'Enter' && attemptUnlock()}
                />
                
                <button onClick={attemptUnlock} disabled={loading} className={S.btnPrimary + " w-full"}>
                    {loading ? <RefreshCw className="animate-spin" /> : "Authenticate"}
                </button>
            </div>
        </div>
    )
}

// -------------------------------------------------------------------------
// --- 4. SYSTEM LOGS VIEW (FIXED) ---
// -------------------------------------------------------------------------
function SystemLogsView({ notify }) {
    const [service, setService] = useState("rq-bot");




    return (
        <div className="h-full flex flex-col pb-20 animate-fade-in">
            <div className="flex justify-between items-center mb-6">
                <h2 className={S.header + " mb-0"}>System Telemetry</h2>
                <div className="flex bg-black/50 rounded border border-white/10 p-1">
                    {["rq-bot", "rq-api", "rq-kenku", "rq-scribe"].map(s => ( 
                        <button key={s} onClick={() => setService(s)} className={`px-4 py-2 text-xs font-bold uppercase rounded ${service === s ? "bg-yellow-600 text-black" : "text-gray-500 hover:text-white"}`}>{s.replace('rq-', '')}</button>
                    ))}
                </div>
            </div>
            {/* Added explicit height to ensure visibility */}
            <div className="flex-1 bg-[#0a0a0a] border border-white/20 rounded-xl overflow-hidden shadow-2xl relative min-h-[500px]">
                <LogTerminal service={service} onClose={() => {}} isModal={false} />
            </div>
        </div>
    )
}

// -------------------------------------------------------------------------
// --- 5. PLAYER PORTAL (PRESERVED v17.0) ---
// -------------------------------------------------------------------------
function PlayerPortalView({ notify, addLog, config }) {
    const campaignId = config?.active_campaign || null;

    const [selectedChar, setSelectedChar] = useState(null);
    const [view, setView] = useState("sheet");

    // Local-first lobby (Phase 4 will persist to backend)
    const [availableChars, setAvailableChars] = useState([]);
    const [loadingChars, setLoadingChars] = useState(false);
    const [isDirty, setIsDirty] = useState(false);
    const [isSaving, setIsSaving] = useState(false);

    const importRef = useRef(null);

    // Create Hero Modal state
    const [showCreateHero, setShowCreateHero] = useState(false);
    const [createDraft, setCreateDraft] = useState({ name: "", class_name: "", race: "", level: 1 });
    const [creatingHero, setCreatingHero] = useState(false);

    
    // Load heroes for the active campaign (no polling; explicit Save button controls persistence)
    useEffect(() => {
        let alive = true;

        async function load() {
            if (!campaignId) {
                setAvailableChars([]);
                setLoadingChars(false);
                return;
            }

            setLoadingChars(true);
            try {
                const res = await axios.get(`${API_URL}/game/characters`, { params: { campaign_id: campaignId } });
                const items = Array.isArray(res.data) ? res.data : (res.data?.items || []);
                if (!alive) return;

                const normalized = items.map((c) => normalizeChar(c));
                setAvailableChars(normalized);
            } catch (e) {
                if (alive) {
                    setAvailableChars([]);
                    notify(`Failed to load heroes: ${e?.message || e}`, "error");
                }
            } finally {
                if (alive) setLoadingChars(false);
            }
        }

        load();
        return () => { alive = false; };
    }, [campaignId]);

    const normalizeChar = (raw) => {
        const sheet = raw?.sheet || {};
        const stats =
            sheet?.stats ||
            raw?.stats || {
                STR: 10,
                DEX: 10,
                CON: 10,
                INT: 10,
                WIS: 10,
                CHA: 10,
            };

        const combat = sheet?.combat || {};
        const hpMax = combat?.hp?.max ?? raw?.hp_max ?? 10;
        const hpCur = combat?.hp?.current ?? raw?.hp ?? hpMax;
        const ac = combat?.ac ?? raw?.ac ?? 10;
        const init = combat?.initiative ?? raw?.init ?? "+0";
        const speed = combat?.speed ?? raw?.speed ?? 30;

        const avatarUrl = raw?.avatar_url || sheet?.avatar_url || sheet?.portrait?.url || null;

        return {
            id: raw?.character_id || raw?.id || `hero_${Math.random().toString(36).slice(2)}`,
            character_id: raw?.character_id || raw?.id || null,
            campaign_id: raw?.campaign_id || campaignId,
            name: raw?.name || "Unnamed Hero",
            role: raw?.role || "Player",
            class_name: raw?.class_name || raw?.class || "Adventurer",
            race: raw?.race || "Unknown",
            level: raw?.level || 1,
            owner_discord_id: raw?.owner_discord_id || null,
            owner_display_name: raw?.owner_display_name || null,
            avatar_url: avatarUrl,
            portrait: avatarUrl ? { url: avatarUrl } : { url: null },
            stats,
            hp: hpCur,
            hp_max: hpMax,
            ac,
            init,
            speed,
            sheet: {
                ...sheet,
                stats,
                combat: {
                    ...(sheet?.combat || {}),
                    ac,
                    initiative: init,
                    speed,
                    hp: {
                        ...(sheet?.combat?.hp || {}),
                        max: hpMax,
                        current: hpCur,
                    },
                },
            },
        };
    };

    const openCreateHero = () => {
        setCreateDraft({ name: "", class_name: "", race: "", level: 1 });
        setShowCreateHero(true);
    };

    const closeCreateHero = () => setShowCreateHero(false);

    const createHero = async () => {
        const name = (createDraft.name || "").trim();
        if (!campaignId) {
            notify?.("No active campaign configured. Set an active campaign in Admin → Neural Config.", "error");
            return;
        }
        if (!name) {
            notify?.("Hero name required.", "error");
            return;
        }

        setCreatingHero(true);
        try {
            const payload = {
                campaign_id: campaignId,
                name,
                class_name: (createDraft.class_name || "").trim() || "Adventurer",
                race: (createDraft.race || "").trim() || "Unknown",
                level: Number(createDraft.level || 1),
                sheet: {
                    bio: { backstory: "", traits: "" },
                    stats: { STR: 10, DEX: 10, CON: 10, INT: 10, WIS: 10, CHA: 10 },
                    combat: { ac: 10, initiative: "+0", speed: 30, hp: { max: 10, current: 10 } },
                    notes: { misc: "" },
                },
            };

            const res = await axios.post(`${API_URL}/game/characters`, payload);
            const created = normalizeChar(res?.data?.character || res?.data);

            setAvailableChars(prev => [created, ...prev]);
            setSelectedChar(created);
            setView("sheet");
            setIsDirty(false);

            notify?.("Hero forged.", "info");
            addLog?.("PLAYER", `Hero created: ${created.name}`);
        } catch (e) {
            notify?.(`Failed to forge hero: ${e?.message || e}`, "error");
        } finally {
            setCreatingHero(false);
            setShowCreateHero(false);
        }
    };

    const handleImportClick = () => {
        if (importRef.current) importRef.current.value = "";
        importRef.current?.click();
    };

    const handleImportFile = async (e) => {
        const file = e?.target?.files?.[0];
        if (!file) return;

        if (!campaignId) {
            notify?.("No active campaign configured. Set an active campaign in Admin → Neural Config.", "error");
            return;
        }

        try {
            const text = await file.text();
            const parsed = JSON.parse(text);

            // Accept either a single hero object or a wrapper like { hero: {...} } or { character: {...} }
            const heroRaw = parsed?.hero ? parsed.hero : parsed?.character ? parsed.character : parsed;

            if (!heroRaw || typeof heroRaw !== "object") throw new Error("Invalid hero JSON.");

            const res = await axios.post(`${API_URL}/game/characters/import`, {
                ...heroRaw,
                campaign_id: heroRaw?.campaign_id || campaignId,
            });

            const imported = normalizeChar(res?.data?.character || res?.data?.hero || res?.data);
            if (!imported?.name) throw new Error("Imported hero missing name.");

            setAvailableChars((prev) => [imported, ...prev]);
            setSelectedChar(imported);
            setView("sheet");
            setIsDirty(false);

            notify?.("Hero imported.", "info");
            addLog?.("PLAYER", `Hero imported: ${imported.name}`);
        } catch (err) {
            console.error(err);
            notify?.(`Failed to import hero JSON: ${err?.message || err}`, "error");
        } finally {
            // allow re-importing the same file
            if (e?.target) e.target.value = "";
        }
    };

    const createHeroModal = showCreateHero ? (
        <div className="fixed inset-0 z-[9998] flex items-center justify-center bg-black/70 backdrop-blur-sm">
            <div className="w-[92vw] max-w-xl bg-[#0a0a0a]/95 border border-white/10 rounded-2xl shadow-2xl p-6 relative overflow-hidden">
                <div className="absolute inset-0 bg-yellow-600/5 blur-2xl pointer-events-none" />
                <div className="relative">
                    <div className="flex items-start justify-between gap-4">
                        <div>
                            <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-widest text-yellow-500">
                                <Sparkles size={14} /> Forge New Hero
                            </div>
                            <div className="text-gray-500 font-mono text-xs tracking-widest mt-1">LOCAL ONLY (PERSISTENCE IN PHASE 4)</div>
                        </div>
                        <button onClick={closeCreateHero} className="text-gray-500 hover:text-white transition-colors">
                            <X size={18} />
                        </button>
                    </div>

                    <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div className="md:col-span-2">
                            <label className="text-[10px] font-mono text-gray-500 uppercase tracking-widest">Hero Name</label>
                            <input value={createDraft.name} onChange={(e) => setCreateDraft(prev => ({ ...prev, name: e.target.value }))} className={S.input} placeholder="e.g., Kaldor Grimwarden" />
                        </div>
                        <div>
                            <label className="text-[10px] font-mono text-gray-500 uppercase tracking-widest">Class</label>
                            <input value={createDraft.class_name} onChange={(e) => setCreateDraft(prev => ({ ...prev, class_name: e.target.value }))} className={S.input} placeholder="Paladin" />
                        </div>
                        <div>
                            <label className="text-[10px] font-mono text-gray-500 uppercase tracking-widest">Race</label>
                            <input value={createDraft.race} onChange={(e) => setCreateDraft(prev => ({ ...prev, race: e.target.value }))} className={S.input} placeholder="Human" />
                        </div>
                        <div>
                            <label className="text-[10px] font-mono text-gray-500 uppercase tracking-widest">Level</label>
                            <input type="number" min={1} max={20} value={createDraft.level} onChange={(e) => setCreateDraft(prev => ({ ...prev, level: Number(e.target.value || 1) }))} className={S.input} />
                        </div>
                        <div className="flex items-end">
                            <button disabled={creatingHero} onClick={createHero} className={`${S.btnPrimary} w-full justify-center ${creatingHero ? "opacity-60 cursor-not-allowed" : ""}`}>
                                <UserPlus size={14}/> {creatingHero ? "Forging..." : "Create Hero"}
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    ) : null;

    if (!selectedChar) {
        return (
            <div className="h-full flex flex-col items-center justify-center animate-fade-in">
                <input type="file" ref={importRef} className="hidden" accept="application/json" onChange={handleImportFile} />
                {createHeroModal}

                <div className="text-center mb-10">
                    <h1 className="font-cinematic text-5xl text-white mb-2 tracking-widest">SELECT YOUR <span className="text-yellow-600">AVATAR</span></h1>
                    <p className="text-gray-500 font-mono text-sm tracking-widest">THE REALM AWAITS YOUR PRESENCE</p>
                </div>

                <div className="flex gap-4 mb-8">
                    <button onClick={openCreateHero} className={S.btnPrimary}><UserPlus size={14}/> New Hero</button>
                    <button onClick={handleImportClick} className={S.btnSecondary}><Upload size={14}/> Import Hero</button>
                </div>

                {loadingChars ? (
                    <div className="text-gray-500 font-mono text-sm tracking-widest flex items-center gap-2"><RefreshCw size={14} className="animate-spin" /> Loading Heroes...</div>
                ) : (
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                        {availableChars.map((c, idx) => (
                            <div key={c.id || idx} onClick={() => { setSelectedChar(normalizeChar(c)); setView("sheet"); setIsDirty(false); }} className="bg-[#0a0a0a] border border-[#333] rounded-xl p-8 hover:border-yellow-600 hover:scale-105 transition-all cursor-pointer group relative overflow-hidden w-64 text-center">
                                <div className="w-24 h-24 mx-auto bg-black rounded-full border-2 border-[#444] flex items-center justify-center mb-6 group-hover:border-yellow-600 transition-colors shadow-[0_0_30px_rgba(0,0,0,0.5)] overflow-hidden">
                                    <span className="font-cinematic text-4xl text-gray-500 group-hover:text-yellow-600 transition-colors">{(c.name || "?").charAt(0)}</span>
                                </div>
                                <h3 className="font-cinematic text-xl text-white mb-1 group-hover:text-yellow-500 transition-colors">{c.name || "Unnamed"}</h3>
                                <p className="text-xs font-mono text-gray-500 uppercase tracking-widest">{c.race || ""} {c.class_name || ""}</p>
                                <div className="mt-6 pt-6 border-t border-[#222]">
                                    <span className="text-[10px] font-bold bg-white/5 px-3 py-1 rounded text-gray-400">LEVEL {c.level || 1}</span>
                                </div>
                                <div className="absolute inset-0 bg-gradient-to-t from-yellow-900/20 to-transparent opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none" />
                            </div>
                        ))}
                    </div>
                )}
            </div>
        )
    }

    // UPDATE HANDLER (local for now)
    const updateChar = (field, value) => {
        setSelectedChar((prev) => {
            if (!prev) return prev;

            const next = { ...prev, [field]: value };
            const prevSheet = prev.sheet || {};

            // Keep the persisted sheet in sync with the UI model
            if (field === "stats") {
                next.sheet = { ...prevSheet, stats: value };
            } else if (["hp", "hp_max", "ac", "init", "speed"].includes(field)) {
                const combatPrev = prevSheet.combat || {};
                const hpPrev = combatPrev.hp || {};
                next.sheet = {
                    ...prevSheet,
                    combat: {
                        ...combatPrev,
                        ac: next.ac ?? combatPrev.ac,
                        initiative: next.init ?? combatPrev.initiative,
                        speed: next.speed ?? combatPrev.speed,
                        hp: {
                            ...hpPrev,
                            max: next.hp_max ?? hpPrev.max,
                            current: next.hp ?? hpPrev.current,
                        },
                    },
                };
            }

            return next;
        });

        setIsDirty(true);
    };


    const saveHero = async () => {
        if (!selectedChar?.character_id) return;

        setIsSaving(true);
        try {
            const payload = {
                name: selectedChar.name,
                campaign_id: selectedChar.campaign_id || campaignId,
                level: selectedChar.level,
                class_name: selectedChar.class_name,
                race: selectedChar.race,
                owner_discord_id: selectedChar.owner_discord_id ?? null,
                owner_display_name: selectedChar.owner_display_name ?? null,
                avatar_url: selectedChar.avatar_url ?? null,
                sheet: selectedChar.sheet || {},
            };

            const res = await axios.put(`${API_URL}/game/characters/${selectedChar.character_id}`, payload);
            const saved = normalizeChar(res?.data?.character || res?.data);

            setSelectedChar(saved);
            setAvailableChars((prev) => prev.map((c) => (c.character_id === saved.character_id ? saved : c)));
            setIsDirty(false);

            notify?.(`Hero saved: ${saved.name}`, "success");
        } catch (e) {
            console.error("saveHero failed", e);
            notify?.("Hero save failed. Check API logs.", "error");
        } finally {
            setIsSaving(false);
        }
    };


    return (
        <div className="max-w-7xl mx-auto pb-20 animate-fade-in h-full flex flex-col">
            {createHeroModal}
            <PlayerHeader char={selectedChar} onUpdate={updateChar} onLogout={() => setSelectedChar(null)} notify={notify} onSave={saveHero} isDirty={isDirty} isSaving={isSaving} />

            {/* NAVIGATION TABS */}
            <div className="flex border-b border-[#222] mb-6 overflow-x-auto custom-scrollbar">
                {[
                    {id: 'sheet', icon: Scroll, label: 'Character Sheet'},
                    {id: 'dice', icon: Dices, label: 'Dice Engine'},
                    {id: 'notes', icon: Edit3, label: 'Grimoire'},
                    {id: 'gallery', icon: ImageIcon, label: 'Vision Archive'},
                    {id: 'npc', icon: Users, label: 'NPC Codex'}
                ].map(tab => (
                    <button key={tab.id} onClick={() => setView(tab.id)} className={`px-8 py-4 flex items-center gap-2 text-xs font-bold uppercase tracking-widest transition-all whitespace-nowrap ${view === tab.id ? "text-yellow-500 border-b-2 border-yellow-500 bg-white/5" : "text-gray-500 hover:text-white"}`}>
                        <tab.icon size={14} /> {tab.label}
                    </button>
                ))}
            </div>

            <div className="flex-1 overflow-auto custom-scrollbar p-2">
                {view === 'sheet' && <CharacterSheet5e char={selectedChar} onUpdate={updateChar} notify={notify} />}
                {view === 'dice' && <DiceEngine notify={notify} />}
                {view === 'notes' && <Grimoire notify={notify} />}
                {view === 'gallery' && <ArtGallery />}
                {view === 'npc' && <NPCCodex />}
            </div>
        </div>
    )
}


// --- SUB-COMPONENT: PLAYER HEADER (AVATAR & DISCORD) ---
function PlayerHeader({ char, onUpdate, onLogout, notify, onSave, isDirty, isSaving }) {
    const [discordId, setDiscordId] = useState(char.owner_discord_id ? char.owner_discord_id : "Link Discord");
    const [isEditingDiscord, setIsEditingDiscord] = useState(false);
    const fileInputRef = useRef(null);

    useEffect(() => {
        setDiscordId(char.owner_discord_id ? char.owner_discord_id : "Link Discord");
    }, [char.owner_discord_id]);

    const handleAvatarClick = () => { fileInputRef.current.click(); };
    const handleFileChange = async (e) => {
        const f = e.target.files?.[0];
        if (!f) return;
        if (!char.character_id) { notify("Character missing ID", "error"); return; }

        try {
            const fd = new FormData();
            fd.append("file", f);
            const res = await axios.post(`${API_URL}/game/characters/${char.character_id}/avatar`, fd, {
                headers: { "Content-Type": "multipart/form-data" },
            });
            if (res.data?.avatar_url) {
                onUpdate("avatar_url", res.data.avatar_url);
                notify("Avatar Updated");
            } else {
                notify("Avatar Upload Failed", "error");
            }
        } catch (e) {
            console.error(e);
            notify("Avatar Upload Failed", "error");
        } finally {
            // allow re-upload same file
            try { e.target.value = ""; } catch { }
        }
    };

    const downloadJson = (filename, obj) => {
        try {
            const blob = new Blob([JSON.stringify(obj, null, 2)], { type: "application/json" });
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            a.remove();
            URL.revokeObjectURL(url);
        } catch (e) { console.error(e); }
    };

    const exportCharacter = async () => {
        if (!char.character_id) return;
        try {
            const res = await axios.get(`${API_URL}/game/characters/${char.character_id}/export`);
            downloadJson(`${char.name || "character"}.json`, res.data);
            notify("Character Exported");
        } catch (e) {
            console.error(e);
            notify("Export Failed", "error");
        }
    };

    const downloadTemplate = async () => {
        try {
            const res = await axios.get(`${API_URL}/game/characters/template`);
            downloadJson("realmquest-character-template.json", res.data);
            notify("Template Downloaded");
        } catch (e) {
            console.error(e);
            notify("Template Download Failed", "error");
        }
    };


    return (
        <div className="flex justify-between items-end mb-8 bg-[#111] p-6 rounded-xl border border-[#333] relative overflow-hidden shadow-2xl">
            <input type="file" ref={fileInputRef} className="hidden" onChange={handleFileChange} />
            
            <div className="relative z-10 flex gap-6 items-center">
                {/* CLICKABLE AVATAR */}
                <div onClick={handleAvatarClick} className="w-20 h-20 bg-black rounded-full border-2 border-yellow-600 flex items-center justify-center shadow-[0_0_20px_rgba(202,138,4,0.3)] cursor-pointer hover:scale-105 transition-transform group relative overflow-hidden">
                    {char.avatar_url ? (
                        <img src={`${API_URL}${char.avatar_url}`} alt="avatar" className="w-full h-full object-cover" />
                    ) : (
                        <span className="font-cinematic text-3xl text-yellow-600 group-hover:opacity-0 transition-opacity">{char.name.charAt(0)}</span>
                    )}
                    <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 bg-black/50 transition-opacity">
                        <Upload size={20} className="text-white" />
                    </div>
                </div>
                
                <div>
                    <h2 className="font-cinematic text-4xl text-white">{char.name}</h2>
                    <div className="flex gap-4 mt-2">
                        <span className="text-xs font-mono text-gray-500 uppercase tracking-widest border-r border-[#333] pr-4">{char.race} {char.class_name}</span>
                        <span className="text-xs font-mono text-yellow-600 uppercase tracking-widest">Level {char.level}</span>
                    </div>
                </div>
            </div>
            
            <div className="relative z-10 flex flex-col items-end gap-3">
                <div className="flex gap-4 items-center">
                    {/* INLINE DISCORD EDIT */}
                    {isEditingDiscord ? (
                        <div className="flex items-center bg-[#0a0a0a] border border-indigo-500/50 rounded px-2">
                             <input className="bg-transparent border-none text-[10px] text-indigo-300 w-24 focus:outline-none font-mono" autoFocus 
                                defaultValue={discordId} 
                                onBlur={(e) => {
                                    const v = (e.target.value || "").trim();
                                    setDiscordId(v || "Link Discord");
                                    setIsEditingDiscord(false);
                                    onUpdate("owner_discord_id", v);
                                    notify(v ? "Soul Linked" : "Soul Unlinked");
                                }}
                                onKeyDown={(e) => { if(e.key === 'Enter') e.target.blur(); }}
                             />
                        </div>
                    ) : (
                        <button onClick={() => setIsEditingDiscord(true)} className="text-[10px] bg-indigo-900/30 text-indigo-400 border border-indigo-500/30 px-3 py-1 rounded hover:bg-indigo-500 hover:text-white transition-all uppercase tracking-widest flex items-center gap-2">
                            <LinkIcon size={12} /> {discordId}
                        </button>
                    )}

                    <button onClick={exportCharacter} className="text-[10px] bg-emerald-900/30 text-emerald-400 border border-emerald-500/30 px-3 py-1 rounded hover:bg-emerald-500 hover:text-white transition-all uppercase tracking-widest flex items-center gap-2">
                        <Save size={12} /> Export
                    </button>

                    <button onClick={downloadTemplate} className="text-[10px] bg-sky-900/30 text-sky-400 border border-sky-500/30 px-3 py-1 rounded hover:bg-sky-500 hover:text-white transition-all uppercase tracking-widest flex items-center gap-2">
                        <Scroll size={12} /> Template
                    </button>

            <button
              onClick={onSave}
              disabled={!isDirty || isSaving}
              className={`text-[10px] px-3 py-1 rounded uppercase tracking-widest flex items-center gap-2 border transition-all ${
                !isDirty
                  ? "bg-emerald-900/10 text-emerald-400/50 border-emerald-500/10 cursor-default"
                  : isSaving
                  ? "bg-emerald-900/30 text-emerald-400 border-emerald-500/30 opacity-70 cursor-wait"
                  : "bg-emerald-900/30 text-emerald-400 border-emerald-500/30 hover:bg-emerald-500 hover:text-white"
              }`}
            >
              <Save size={12} /> {isSaving ? "Saving…" : isDirty ? "Save" : "Saved"}
            </button>

                    <button onClick={onLogout} className="text-[10px] bg-red-900/30 text-red-500 border border-red-500/30 px-3 py-1 rounded hover:bg-red-500 hover:text-white transition-all uppercase tracking-widest">
                        Exit Portal
                    </button>
                </div>
                <div className="flex gap-2">
                    <StatBadge label="HP" val={char.hp + "/" + char.hp_max} color="red" />
                    <StatBadge label="AC" val={char.ac} color="blue" />
                    <StatBadge label="INIT" val={char.init} color="yellow" />
                    <StatBadge label="SPD" val={char.speed} color="green" />
                </div>
            </div>
        </div>
    )
}

function StatBadge({ label, val, color }) {
    const colors = {
        red: "border-red-900/50 text-red-500",
        blue: "border-blue-900/50 text-blue-500",
        yellow: "border-yellow-900/50 text-yellow-500",
        green: "border-green-900/50 text-green-500",
    };
    return (
        <div className={`flex flex-col items-center justify-center bg-black/40 border rounded px-3 py-1 min-w-[50px] ${colors[color]}`}>
            <span className="text-[9px] uppercase font-bold opacity-70">{label}</span>
            <span className="text-lg font-bold text-gray-200">{val}</span>
        </div>
    )
}

// --- SUB-COMPONENT: EDITABLE 5E SHEET ---
function CharacterSheet5e({ char, onUpdate, notify }) {
    const skills = [
        {name: "Acrobatics", mod: "DEX", val: "+1"}, {name: "Arcana", mod: "INT", val: "+0"},
        {name: "Athletics", mod: "STR", val: "+4", prof: true}, {name: "Deception", mod: "CHA", val: "+7", prof: true},
        {name: "History", mod: "INT", val: "+0"}, {name: "Insight", mod: "WIS", val: "+4", prof: true},
        {name: "Intimidation", mod: "CHA", val: "+7", prof: true}, {name: "Investigation", mod: "INT", val: "+0"},
        {name: "Medicine", mod: "WIS", val: "+2"}, {name: "Nature", mod: "INT", val: "+0"},
        {name: "Perception", mod: "WIS", val: "+4", prof: true}, {name: "Performance", mod: "CHA", val: "+4"},
        {name: "Persuasion", mod: "CHA", val: "+7", prof: true}, {name: "Religion", mod: "INT", val: "+0"},
        {name: "Sleight of Hand", mod: "DEX", val: "+1"}, {name: "Stealth", mod: "DEX", val: "+1"},
        {name: "Survival", mod: "WIS", val: "+2"}
    ];

    const inventory = [
        { item: "Dagger", qty: 1, wgt: "1lb" }, { item: "Arcane Focus", qty: 1, wgt: "2lb" },
        { item: "Rations", qty: 5, wgt: "10lb" }, { item: "Rope, Hempen (50ft)", qty: 1, wgt: "10lb" }
    ];

    return (
        <div className="grid grid-cols-12 gap-6 animate-fade-in">
            {/* LEFT COLUMN: EDITABLE STATS */}
            <div className="col-span-12 md:col-span-2 flex flex-col gap-4">
                {Object.entries(char.stats).map(([key, val]) => {
                    const mod = Math.floor((val - 10) / 2);
                    return (
                        <div key={key} className="bg-[#111] border border-[#333] rounded-lg p-2 flex flex-col items-center relative group overflow-hidden">
                            <div className="text-[10px] font-bold text-gray-500 uppercase tracking-widest mb-1">{key}</div>
                            <div className="text-2xl font-cinematic text-white">{mod >= 0 ? `+${mod}` : mod}</div>
                            {/* EDITABLE STAT INPUT */}
                            <input 
                                className="w-10 h-8 rounded-full border border-[#444] bg-black text-xs text-gray-400 mt-1 shadow-inner text-center focus:border-yellow-600 focus:outline-none"
                                value={val}
                                onChange={(e) => {
                                    const newStats = {...char.stats, [key]: parseInt(e.target.value) || 10};
                                    onUpdate('stats', newStats);
                                }}
                            />
                        </div>
                    )
                })}
                <div className="bg-[#111] p-3 rounded border border-[#333] text-center">
                    <div className="text-[9px] text-gray-500 uppercase font-bold">Proficiency</div>
                    <div className="text-xl text-yellow-500 font-cinematic">+3</div>
                </div>
            </div>

            {/* MIDDLE COLUMN: SKILLS & VITALS */}
            <div className="col-span-12 md:col-span-6 flex flex-col gap-6">
                {/* SAVING THROWS */}
                <div className={S.card}>
                    <h3 className="text-xs font-bold text-gray-500 uppercase tracking-widest border-b border-[#333] pb-2 mb-4">Saving Throws</h3>
                    <div className="grid grid-cols-3 gap-2">
                        {Object.keys(char.stats).map(s => (
                            <div key={s} className="flex items-center gap-2 text-xs text-gray-300">
                                <div className={`w-3 h-3 rounded-full border ${['CHA','WIS'].includes(s) ? 'bg-yellow-600 border-yellow-600' : 'border-[#444]'}`} />
                                <span className="font-bold">{s}</span>
                                <input className="ml-auto w-6 bg-transparent text-right text-gray-500 focus:outline-none focus:text-white" defaultValue="+3" />
                            </div>
                        ))}
                    </div>
                </div>

                {/* SKILLS */}
                <div className={`${S.card} flex-1`}>
                    <h3 className="text-xs font-bold text-gray-500 uppercase tracking-widest border-b border-[#333] pb-2 mb-4">Skills</h3>
                    <div className="grid grid-cols-1 gap-2">
                        {skills.map((s, i) => (
                            <div key={i} className="flex items-center justify-between text-xs py-1 hover:bg-white/5 px-2 rounded cursor-pointer group">
                                <div className="flex items-center gap-3">
                                    <div className={`w-2 h-2 rounded-full ${s.prof ? 'bg-yellow-600' : 'bg-[#333]'}`} />
                                    <span className={`uppercase tracking-wide ${s.prof ? 'text-white font-bold' : 'text-gray-500'}`}>{s.name} <span className="text-[9px] text-[#444]">({s.mod})</span></span>
                                </div>
                                <span className={`${s.prof ? 'text-yellow-500' : 'text-gray-600'}`}>{s.val}</span>
                            </div>
                        ))}
                    </div>
                </div>
                
                {/* INVENTORY (NEW) */}
                <div className={S.card}>
                     <h3 className="text-xs font-bold text-gray-500 uppercase tracking-widest border-b border-[#333] pb-2 mb-4 flex justify-between">
                         <span>Inventory</span>
                         <Plus size={12} className="cursor-pointer hover:text-white" />
                     </h3>
                     <table className="w-full text-xs text-left text-gray-400">
                         <thead><tr className="border-b border-white/5"><th className="pb-2">Item</th><th className="pb-2 text-center">Qty</th><th className="pb-2 text-right">Wgt</th></tr></thead>
                         <tbody>
                             {inventory.map((item, i) => (
                                 <tr key={i} className="border-b border-white/5 hover:bg-white/5 group">
                                     <td className="py-2"><input className={S.editableText + " text-left"} defaultValue={item.item} /></td>
                                     <td className="py-2"><input className={S.editableText} defaultValue={item.qty} /></td>
                                     <td className="py-2 text-right">{item.wgt}</td>
                                 </tr>
                             ))}
                         </tbody>
                     </table>
                </div>
            </div>

            {/* RIGHT COLUMN: COMBAT & FEATURES */}
            <div className="col-span-12 md:col-span-4 flex flex-col gap-6">
                {/* ATTACKS */}
                <div className={S.card}>
                    <h3 className="text-xs font-bold text-gray-500 uppercase tracking-widest border-b border-[#333] pb-2 mb-4">Attacks & Spellcasting</h3>
                    <div className="space-y-3">
                        <div className="bg-[#151515] p-3 rounded border border-[#333] flex justify-between items-center hover:border-red-900/50 transition-colors cursor-pointer group">
                            <div>
                                <input className="bg-transparent text-white font-cinematic text-lg group-hover:text-red-500 transition-colors focus:outline-none w-32" defaultValue="Eldritch Blast" />
                                <div className="text-[10px] text-gray-500 uppercase">Ranged • 120ft</div>
                            </div>
                            <div className="text-right">
                                <div className="text-yellow-600 font-bold text-sm">+7 to hit</div>
                                <div className="text-gray-400 text-xs">1d10+4 Force</div>
                            </div>
                        </div>
                        <div className="bg-[#151515] p-3 rounded border border-[#333] flex justify-between items-center hover:border-red-900/50 transition-colors cursor-pointer group">
                            <div>
                                <input className="bg-transparent text-white font-cinematic text-lg group-hover:text-red-500 transition-colors focus:outline-none w-32" defaultValue="Dagger" />
                                <div className="text-[10px] text-gray-500 uppercase">Finesse • Light</div>
                            </div>
                            <div className="text-right">
                                <div className="text-yellow-600 font-bold text-sm">+4 to hit</div>
                                <div className="text-gray-400 text-xs">1d4+2 Piercing</div>
                            </div>
                        </div>
                    </div>
                </div>
                
                {/* SPELLS (NEW) */}
                <div className={S.card}>
                     <h3 className="text-xs font-bold text-gray-500 uppercase tracking-widest border-b border-[#333] pb-2 mb-4">Spell Slots</h3>
                     <div className="flex gap-4 justify-between">
                         <SpellSlotLevel level={1} total={4} used={1} />
                         <SpellSlotLevel level={2} total={2} used={0} />
                         <SpellSlotLevel level={3} total={0} used={0} />
                     </div>
                </div>

                {/* FEATURES */}
                <div className={`${S.card} flex-1`}>
                     <h3 className="text-xs font-bold text-gray-500 uppercase tracking-widest border-b border-[#333] pb-2 mb-4">Features & Traits</h3>
                     <div className="space-y-4 overflow-y-auto max-h-[300px] custom-scrollbar pr-2">
                         <FeatureBlock title="Dark One's Blessing" desc="When you reduce a hostile creature to 0 hit points, you gain temporary hit points equal to your Charisma modifier + your warlock level (9)." />
                         <FeatureBlock title="Agonizing Blast" desc="When you cast eldritch blast, add your Charisma modifier to the damage it deals on a hit." />
                         <FeatureBlock title="Pact of the Tome" desc="Your patron gives you a grimoire called a Book of Shadows." />
                     </div>
                </div>
            </div>
        </div>
    )
}

function SpellSlotLevel({ level, total, used }) {
    return (
        <div className="flex flex-col items-center">
            <span className="text-[9px] text-gray-500 mb-1">LVL {level}</span>
            <div className="flex gap-1">
                {Array.from({length: total}).map((_, i) => (
                    <div key={i} className={`w-3 h-8 rounded border ${i < used ? 'bg-transparent border-[#333]' : 'bg-yellow-600 border-yellow-500'} cursor-pointer`} />
                ))}
            </div>
        </div>
    )
}

function FeatureBlock({ title, desc }) {
    return (
        <div className="bg-[#111] p-3 rounded border border-[#222]">
            <input className="bg-transparent text-yellow-600 font-bold text-xs uppercase mb-1 w-full focus:outline-none" defaultValue={title} />
            <textarea className="bg-transparent text-gray-400 text-[10px] leading-relaxed w-full resize-none focus:outline-none" rows={3} defaultValue={desc} />
        </div>
    )
}

// --- SUB-COMPONENT: TACTICAL DICE ENGINE ---
function DiceEngine({ notify, char }) {
    const [history, setHistory] = useState([]);
    const [rolling, setRolling] = useState(false);
    
    // TACTICAL CONFIG
    const [diceCount, setDiceCount] = useState(1);
    const [modifier, setModifier] = useState(0);
    const [advantage, setAdvantage] = useState("normal"); // normal, adv, dis
    const [attribute, setAttribute] = useState("");
    const [bonus, setBonus] = useState(0);

    const roll = async (sides) => {
        setRolling(sides);
        await new Promise(r => setTimeout(r, 600)); // Animation
        
        // LOGIC: MULTI-ROLL & SUM
        let rolls = [];
        let total = 0;
        
        for(let i=0; i < diceCount; i++) {
            let r = Math.floor(Math.random() * sides) + 1;
            rolls.push(r);
            total += r;
        }

        const grandTotal = total + parseInt(modifier) + parseInt(bonus);
        
        const newLog = { 
            sides, rolls, modifier, bonus, attribute, grandTotal, diceCount,
            ts: new Date().toLocaleTimeString([], {hour12: false}) 
        };
        
        setHistory(prev => [newLog, ...prev]);

        // Back-end hook (so bot/AI can be aware of rolls)
        try {
            await axios.post(`${API_URL}/game/roll`, {
                character_id: char?.character_id || null,
                owner_discord_id: char?.owner_discord_id || null,
                dice_count: diceCount,
                sides,
                modifier: parseInt(modifier) || 0,
                bonus: parseInt(bonus) || 0,
                attribute: attribute || null,
                rolls,
                grand_total: grandTotal,
            });
        } catch (e) {
            // Silent: never interrupt gameplay UI for telemetry failures
            console.error(e);
        }
        setRolling(false);
    };

    const clearHistory = async () => { if (await rqConfirm({ title: "Clear Roll Log", message: "Clear Roll Log?", confirmText: "Clear", cancelText: "Cancel", danger: true })) setHistory([]); };

    return (
        <div className="h-full grid grid-cols-1 lg:grid-cols-3 gap-8 animate-fade-in">
            <div className="col-span-2 flex flex-col gap-6">
                {/* VISUALIZER */}
                <div className="bg-[#0a0a0a] border border-[#333] rounded-xl flex-1 min-h-[300px] flex items-center justify-center relative overflow-hidden shadow-inner">
                    <div className="absolute inset-0 bg-[url('https://www.transparenttextures.com/patterns/felt.png')] opacity-10" />
                    {rolling ? (
                        <div className="flex flex-col items-center animate-bounce">
                            <Dices size={80} className="text-yellow-600 mb-4 animate-spin-slow" />
                            <h2 className="font-cinematic text-3xl text-white tracking-widest">ROLLING {diceCount}d{rolling}...</h2>
                        </div>
                    ) : (
                        history.length > 0 ? (
                            <div className="text-center animate-fade-in-up">
                                <div className="text-sm text-gray-500 uppercase tracking-[0.3em] mb-4">RESULT</div>
                                <div className="text-9xl font-cinematic text-white drop-shadow-[0_0_30px_rgba(202,138,4,0.6)]">
                                    {history[0].grandTotal}
                                </div>
                                <div className="text-gray-500 font-mono mt-4 text-sm">
                                    [{history[0].rolls.join(', ')}] {history[0].modifier > 0 && `+ ${history[0].modifier}`} {history[0].bonus > 0 && `+ ${history[0].bonus}`}
                                </div>
                            </div>
                        ) : <div className="text-gray-600 font-cinematic text-xl">FATE AWAITS</div>
                    )}
                </div>

                {/* TACTICAL CONTROLS */}
                <div className="bg-[#111] border border-[#333] rounded-xl p-6">
                    {/* CONFIG ROW */}
                    <div className="grid grid-cols-4 gap-4 mb-6 pb-6 border-b border-[#222]">
                        <div>
                            <label className={S.label}>Dice Count</label>
                            <div className="flex bg-black rounded border border-[#444] items-center">
                                <button onClick={() => setDiceCount(Math.max(1, diceCount-1))} className="px-3 text-gray-400 hover:text-white">-</button>
                                <span className="flex-1 text-center font-mono text-white">{diceCount}</span>
                                <button onClick={() => setDiceCount(diceCount+1)} className="px-3 text-gray-400 hover:text-white">+</button>
                            </div>
                        </div>
                        <div>
                            <label className={S.label}>Modifier</label>
                            <input className={S.input + " text-center"} type="number" value={modifier} onChange={e => setModifier(e.target.value)} />
                        </div>
                        <div>
                            <label className={S.label}>Bonus</label>
                            <input className={S.input + " text-center"} type="number" value={bonus} onChange={e => setBonus(e.target.value)} />
                        </div>
                         <div>
                            <label className={S.label}>Attribute</label>
                            <select className={S.input} value={attribute} onChange={e => setAttribute(e.target.value)}>
                                <option value="">None</option>
                                <option value="STR">STR</option><option value="DEX">DEX</option>
                                <option value="CON">CON</option><option value="INT">INT</option>
                                <option value="WIS">WIS</option><option value="CHA">CHA</option>
                            </select>
                        </div>
                    </div>

                    {/* DICE ROW */}
                    <div className="grid grid-cols-6 gap-4">
                        {[4,6,8,10,12,20].map(d => (
                            <button key={d} onClick={() => roll(d)} disabled={rolling} className="group relative">
                                <div className="absolute inset-0 bg-gradient-to-br from-yellow-600/20 to-transparent opacity-0 group-hover:opacity-100 rounded-lg transition-opacity" />
                                <div className="bg-[#1a1a1a] border border-[#333] rounded-lg p-4 flex flex-col items-center gap-2 group-hover:border-yellow-600 group-hover:-translate-y-1 transition-all shadow-lg">
                                    <Dices className="text-gray-600 group-hover:text-yellow-500 transition-colors" size={24} />
                                    <span className="font-cinematic text-sm text-gray-400 group-hover:text-white">d{d}</span>
                                </div>
                            </button>
                        ))}
                    </div>
                </div>
            </div>

            {/* LOG */}
            <div className="bg-[#0a0a0a] border border-[#333] rounded-xl flex flex-col overflow-hidden">
                <div className="p-4 border-b border-[#222] bg-[#111] flex justify-between items-center">
                    <h3 className="text-xs font-bold text-gray-500 uppercase tracking-widest flex items-center gap-2"><Scroll size={14}/> Roll History</h3>
                    <button onClick={clearHistory} className="text-red-900 hover:text-red-500"><Trash2 size={14} /></button>
                </div>
                <div className="flex-1 overflow-auto custom-scrollbar p-4 space-y-3">
                    {history.map((h, i) => (
                        <div key={i} className="flex justify-between items-center bg-white/5 p-3 rounded border border-white/5 text-xs">
                            <div className="flex flex-col">
                                <span className="text-yellow-600 font-bold">{h.diceCount}d{h.sides} {h.attribute && `(${h.attribute})`}</span>
                                <span className="text-gray-500 text-[10px]">{h.ts}</span>
                            </div>
                            <span className="text-white font-bold text-lg">{h.grandTotal}</span>
                        </div>
                    ))}
                    {history.length === 0 && <div className="text-center text-gray-600 mt-10 text-xs italic">No rolls yet recorded.</div>}
                </div>
            </div>
        </div>
    )
}

// --- SUB-COMPONENT: NPC CODEX (DYNAMIC IMAGES) ---

function NPCCodex({ notify }) {
    const [npcs, setNpcs] = useState([]);
    const [loading, setLoading] = useState(true);
    const [selectedNpc, setSelectedNpc] = useState(null);
    const [query, setQuery] = useState("");
    const [refreshing, setRefreshing] = useState(false);

    const portraitInputRef = useRef(null);
    const [portraitUploading, setPortraitUploading] = useState(false);
    const [deletingNpc, setDeletingNpc] = useState(false);

    const apiDeleteNpc = async (npc) => {
        const npcId = (npc?.id || "").toString();
        if (!npcId) return;
        const ok = await rqConfirm({
            title: "Delete NPC",
            message: `Delete NPC dossier AND portrait for "${npc?.name || npcId}"? This cannot be undone.`,
            confirmText: "Delete",
            cancelText: "Cancel",
            danger: true,
        });
        if (!ok) return;

        setDeletingNpc(true);
        try {
            await axios.delete(`${API_URL}/system/campaigns/codex/npcs/${encodeURIComponent(npcId)}?delete_portrait=true`);
            notify && notify("NPC Deleted");
            setSelectedNpc(null);
            await fetchNpcs();
        } catch (e) {
            console.error(e);
            notify && notify("Delete Failed", "error");
        } finally {
            setDeletingNpc(false);
        }
    };

    const apiReplaceNpcPortrait = async (npc, file) => {
        const npcId = (npc?.id || "").toString();
        if (!npcId || !file) return;
        setPortraitUploading(true);
        try {
            const form = new FormData();
            form.append("file", file);
            await axios.post(`${API_URL}/system/campaigns/codex/npcs/${encodeURIComponent(npcId)}/portrait`, form, {
                headers: { "Content-Type": "multipart/form-data" },
            });
            notify && notify("Portrait Updated");
            await fetchNpcs();
            // refresh selected NPC from updated list if still open
            setSelectedNpc((prev) => {
                if (!prev) return prev;
                if ((prev?.id || "").toString() !== npcId) return prev;
                return prev;
            });
        } catch (e) {
            console.error(e);
            notify && notify("Portrait Update Failed", "error");
        } finally {
            setPortraitUploading(false);
            try { if (portraitInputRef.current) portraitInputRef.current.value = ""; } catch {}
        }
    };

    const fmtEpoch = (epoch) => {
        if (!epoch) return "";
        try { return new Date(epoch * 1000).toLocaleString([], { hour12: false }); } catch { return ""; }
    };

    const copyText = async (txt) => {
        const v = (txt || "").toString();
        if (!v) return;
        try {
            if (navigator?.clipboard?.writeText) {
                await navigator.clipboard.writeText(v);
                return true;
            }
        } catch { /* fall through */ }
        try {
            const ta = document.createElement("textarea");
            ta.value = v;
            ta.style.position = "fixed";
            ta.style.opacity = "0";
            document.body.appendChild(ta);
            ta.select();
            document.execCommand("copy");
            ta.remove();
            return true;
        } catch {
            return false;
        }
    };

    const fetchNpcs = useCallback(async () => {
        setRefreshing(true);
        try {
            const res = await axios.get(`${API_URL}/system/campaigns/codex/npcs?include_dossier=true`);
            const items = res?.data?.items;
            setNpcs(Array.isArray(items) ? items : []);
        } catch (e) {
            console.error(e);
            setNpcs([]);
        } finally {
            setRefreshing(false);
        }
    }, []);

    useEffect(() => {
        let mounted = true;
        (async () => {
            setLoading(true);
            try {
                const res = await axios.get(`${API_URL}/system/campaigns/codex/npcs?include_dossier=true`);
                const items = res?.data?.items;
                if (!mounted) return;
                setNpcs(Array.isArray(items) ? items : []);
            } catch (e) {
                console.error(e);
                if (mounted) setNpcs([]);
            } finally {
                if (mounted) setLoading(false);
            }
        })();
        return () => { mounted = false; };
    }, []);

    const filtered = useMemo(() => {
        const q = (query || "").trim().toLowerCase();
        if (!q) return npcs;
        return (npcs || []).filter((n) => {
            const name = (n?.name || n?.dossier?.name || n?.id || "").toString().toLowerCase();
            const loc = (n?.dossier?.location || "").toString().toLowerCase();
            const role = (n?.dossier?.stats?.class || "").toString().toLowerCase();
            const desc = (n?.dossier?.desc || "").toString().toLowerCase();
            return name.includes(q) || loc.includes(q) || role.includes(q) || desc.includes(q);
        });
    }, [npcs, query]);

    const resolvePortraitUrl = (n) => {
        // Prefer API-provided portrait.url (already campaign-scoped).
        const portraitUrl = (n?.portrait?.url || n?.portrait_url || null)
            || (n?.dossier?.image || n?.dossier?.portrait || n?.dossier?.avatar || null);

        if (!portraitUrl) return null;

        // If it is already campaign-scoped, use as-is.
        if (portraitUrl.startsWith("/campaigns/")) return portraitUrl;

        // If it is an absolute URL (http/https), return as-is (rare but safe).
        if (portraitUrl.startsWith("http://") || portraitUrl.startsWith("https://")) return portraitUrl;

        // If it is a relative path like "assets/images/..." from dossier, prefix with this NPC's campaign if we can infer it.
        const rel = portraitUrl.replace(/^\//, "");
        const jsonUrl = (n?.json_url || n?.jsonUrl || "").toString();
        const m = jsonUrl.match(/^(\/campaigns\/[^\/]+\/)/);
        if (m && m[1]) {
            return `${m[1]}${rel}`;
        }

        // Fallback: just make it root-relative.
        return `/${rel}`;
    };

    const selectedPortrait = resolvePortraitUrl(selectedNpc);
    const selectedJsonUrl = selectedNpc?.json_url ? (selectedNpc.json_url.startsWith("/") ? selectedNpc.json_url : `/${selectedNpc.json_url}`) : null;

    const npcModal = selectedNpc ? (
        <div className="fixed inset-0 z-[9998] flex items-center justify-center bg-black/80 backdrop-blur-sm p-6 animate-fade-in">
            <div className="w-full max-w-5xl bg-[#0a0a0a]/95 border border-white/10 rounded-2xl shadow-2xl overflow-hidden">
                <div className="flex items-center justify-between px-6 py-4 border-b border-white/10 bg-white/5">
                    <div className="flex items-center gap-2">
                        <Users size={16} className="text-yellow-600" />
                        <span className="font-mono text-xs uppercase tracking-widest text-white">NPC DOSSIER</span>
                    </div>
                    <button onClick={() => setSelectedNpc(null)} className="text-gray-500 hover:text-white transition-colors">
                        <X size={18} />
                    </button>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-3 gap-0">
                    <div className="lg:col-span-1 border-b lg:border-b-0 lg:border-r border-white/10 bg-black/30">
                        <div className="aspect-square w-full bg-[#111] overflow-hidden">
                            {selectedPortrait ? (
                                <img
                                    src={`${API_URL}${selectedPortrait}`}
                                    alt={selectedNpc?.name || selectedNpc?.id || "npc"}
                                    className="w-full h-full object-cover opacity-90"
                                />
                            ) : (
                                <div className="w-full h-full flex items-center justify-center text-gray-700">
                                    <UserCircle size={64} />
                                </div>
                            )}
                        </div>
                        <div className="p-6">
                            <h3 className="font-cinematic text-3xl text-white">{selectedNpc?.name || selectedNpc?.id}</h3>
                            <div className="mt-2 flex flex-wrap gap-2">
                                <span className="text-[10px] bg-yellow-900/40 px-2 py-1 rounded text-yellow-500 uppercase tracking-widest backdrop-blur-sm border border-yellow-500/20">
                                    {(selectedNpc?.dossier?.stats?.class) || "NPC"}
                                </span>
                                {selectedNpc?.dossier?.location && (
                                    <span className="text-[10px] bg-white/5 px-2 py-1 rounded text-gray-400 uppercase tracking-widest border border-white/10">
                                        {selectedNpc.dossier.location}
                                    </span>
                                )}
                            </div>
                            <div className="mt-4 space-y-2">
                                {selectedNpc?.dossier?.voice_id && (
                                    <div className="text-[10px] font-mono text-gray-500 uppercase tracking-widest">
                                        VOICE_ID: <span className="text-gray-300">{selectedNpc.dossier.voice_id}</span>
                                    </div>
                                )}
                                {selectedNpc?.dossier?.created_at && (
                                    <div className="text-[10px] font-mono text-gray-500 uppercase tracking-widest">
                                        CREATED: <span className="text-gray-300">{fmtEpoch(selectedNpc.dossier.created_at)}</span>
                                    </div>
                                )}
                            </div>

                            <div className="mt-6 grid grid-cols-1 gap-2">
                                <input
                                    ref={portraitInputRef}
                                    type="file"
                                    accept="image/png,image/jpeg,image/webp"
                                    className="hidden"
                                    onChange={(e) => {
                                        const f = e?.target?.files?.[0];
                                        if (f) apiReplaceNpcPortrait(selectedNpc, f);
                                    }}
                                />

                                <button
                                    onClick={() => {
                                        try { portraitInputRef.current && portraitInputRef.current.click(); } catch {}
                                    }}
                                    className={S.btnPrimary}
                                    title="Replace NPC Portrait"
                                    disabled={portraitUploading || deletingNpc}
                                >
                                    <Upload size={14}/> {portraitUploading ? "Uploading..." : "Replace Portrait"}
                                </button>

                                <button
                                    onClick={() => apiDeleteNpc(selectedNpc)}
                                    className={S.btnDanger}
                                    title="Delete NPC Dossier + Portrait"
                                    disabled={portraitUploading || deletingNpc}
                                >
                                    <Trash2 size={14}/> {deletingNpc ? "Deleting..." : "Delete NPC"}
                                </button>

                                {selectedPortrait && (
                                    <button
                                        onClick={async () => {
                                            const ok = await copyText(`${API_URL}${selectedPortrait}`);
                                            // lightweight toast fallback via title is handled by browser; keep silent
                                            if (!ok) { /* noop */ }
                                        }}
                                        className={S.btnSecondary}
                                        title="Copy Image URL"
                                    >
                                        <LinkIcon size={14}/> Copy Image URL
                                    </button>
                                )}
                                {selectedJsonUrl && (
                                    <button
                                        onClick={async () => {
                                            const ok = await copyText(`${API_URL}${selectedJsonUrl}`);
                                            if (!ok) { /* noop */ }
                                        }}
                                        className={S.btnSecondary}
                                        title="Copy JSON URL"
                                    >
                                        <LinkIcon size={14}/> Copy JSON URL
                                    </button>
                                )}
                                {selectedJsonUrl && (
                                    <a
                                        href={`${API_URL}${selectedJsonUrl}`}
                                        target="_blank"
                                        rel="noreferrer"
                                        className={S.btnSecondary}
                                        title="Open dossier JSON"
                                    >
                                        <Eye size={14}/> Open JSON
                                    </a>
                                )}
                            </div>
                        </div>
                    </div>

                    <div className="lg:col-span-2 p-6">
                        <div className="flex items-center justify-between mb-4">
                            <h4 className={S.sectionHeader + " mb-0 border-none"}>Dossier</h4>
                            <button
                                onClick={() => {
                                    try {
                                        const blob = new Blob([JSON.stringify(selectedNpc?.dossier || {}, null, 2)], { type: "application/json" });
                                        const url = URL.createObjectURL(blob);
                                        const a = document.createElement("a");
                                        a.href = url;
                                        a.download = `${selectedNpc?.id || "npc"}.json`;
                                        document.body.appendChild(a);
                                        a.click();
                                        a.remove();
                                        URL.revokeObjectURL(url);
                                    } catch (e) { console.error(e); }
                                }}
                                className={S.btnSecondary}
                                title="Download dossier JSON"
                            >
                                <Save size={14}/> Download JSON
                            </button>
                        </div>

                        <div className="bg-black/40 border border-white/10 rounded-xl p-5 text-sm text-gray-300 leading-relaxed whitespace-pre-wrap">
                            {selectedNpc?.dossier?.desc ? selectedNpc.dossier.desc : "No description provided yet."}
                        </div>

                        <div className="mt-6">
                            <h4 className={S.sectionHeader}>Stats</h4>
                            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                                {Object.entries(selectedNpc?.dossier?.stats || {}).length === 0 ? (
                                    <div className="col-span-full text-gray-500 font-mono text-xs tracking-widest">No stats yet.</div>
                                ) : (
                                    Object.entries(selectedNpc.dossier.stats).map(([k, v]) => (
                                        <div key={k} className="bg-white/5 border border-white/10 rounded-lg p-3">
                                            <div className="text-[9px] font-mono text-gray-500 uppercase tracking-widest">{k}</div>
                                            <div className="font-mono text-xs text-gray-200 mt-1">{String(v)}</div>
                                        </div>
                                    ))
                                )}
                            </div>
                        </div>

                        <div className="mt-6 pt-4 border-t border-white/10">
                            <div className="flex items-center justify-between">
                                <div className="text-[10px] font-mono text-gray-500 uppercase tracking-widest">
                                    ID: <span className="text-gray-300">{selectedNpc?.id || "npc"}</span>
                                </div>
                                {selectedNpc?.json_filename && (
                                    <div className="text-[10px] font-mono text-gray-500 uppercase tracking-widest">
                                        FILE: <span className="text-gray-300">{selectedNpc.json_filename}</span>
                                    </div>
                                )}
                            </div>
                        </div>

                    </div>
                </div>
            </div>
        </div>
    ) : null;

    return (
        <div className="animate-fade-in">
            {npcModal}

            <div className="flex items-center justify-between mb-4 gap-4">
                <div className="flex items-center gap-3 min-w-0">
                    <div className="text-[10px] font-mono uppercase tracking-widest text-gray-500">
                        NPC COUNT: <span className="text-gray-200">{filtered.length}</span>
                    </div>
                    <div className="hidden md:block text-[10px] font-mono uppercase tracking-widest text-gray-600 truncate">
                        SEARCHES NAME / LOCATION / ROLE / DESC
                    </div>
                </div>

                <div className="flex items-center gap-2">
                    <input
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                        className={S.input + " w-[260px] text-xs"}
                        placeholder="Search NPCs..."
                    />
                    <button
                        onClick={fetchNpcs}
                        className={S.btnSecondary}
                        title="Refresh Codex"
                    >
                        <RefreshCw size={14} className={refreshing ? "animate-spin" : ""}/> Refresh
                    </button>
                </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {loading ? (
                    <div className="col-span-full text-gray-500 font-mono text-sm tracking-widest flex items-center gap-2">
                        <RefreshCw size={14} className="animate-spin" /> Scanning Codex...
                    </div>
                ) : filtered.length === 0 ? (
                    <div className="col-span-full text-center text-gray-500 font-mono text-sm tracking-widest">
                        No NPC dossiers found in this campaign.
                    </div>
                ) : filtered.map((n) => {
                    const resolvedPortrait = resolvePortraitUrl(n);
                    const name = n?.name || n?.dossier?.name || n?.id || "NPC";
                    const desc = n?.dossier?.desc || "";
                    const loc = n?.dossier?.location || "";
                    const role = n?.dossier?.stats?.class || "NPC";
                    const created = n?.dossier?.created_at ? fmtEpoch(n.dossier.created_at) : "";

                    return (
                        <div
                            key={n?.id || name}
                            onClick={() => setSelectedNpc(n)}
                            className="bg-[#0a0a0a] border border-[#333] rounded-xl overflow-hidden group hover:border-yellow-600/50 transition-all cursor-pointer"
                        >
                            <div className="h-48 relative bg-[#111] overflow-hidden">
                                {resolvedPortrait ? (
                                    <img
                                        src={`${API_URL}${resolvedPortrait}`}
                                        alt={name}
                                        className="w-full h-full object-cover opacity-50 group-hover:opacity-100 transition-opacity"
                                        onError={(e) => { try { e.target.style.display = 'none'; } catch {} }}
                                    />
                                ) : (
                                    <div className="w-full h-full flex items-center justify-center text-gray-700">
                                        <UserCircle size={48} />
                                    </div>
                                )}

                                <div className="absolute bottom-0 left-0 w-full p-4 bg-gradient-to-t from-black to-transparent">
                                    <h3 className="font-cinematic text-2xl text-white drop-shadow-md">{name}</h3>
                                    <div className="mt-2 flex items-center gap-2 flex-wrap">
                                        <span className="text-[10px] bg-yellow-900/40 px-2 py-1 rounded text-yellow-500 uppercase tracking-widest backdrop-blur-sm border border-yellow-500/20">
                                            {role}
                                        </span>
                                        {loc && (
                                            <span className="text-[10px] bg-white/5 px-2 py-1 rounded text-gray-400 uppercase tracking-widest border border-white/10">
                                                {loc}
                                            </span>
                                        )}
                                    </div>
                                </div>
                            </div>
                            <div className="p-4">
                                <div className="flex justify-between text-[10px] text-gray-500 mb-2 font-mono uppercase tracking-widest">
                                    <span>{created ? "CREATED" : ""}</span>
                                    <span className="text-gray-400">{created || ""}</span>
                                </div>

                                <p className="text-xs text-gray-400 leading-relaxed mb-4 whitespace-pre-wrap line-clamp-4">
                                    {desc || "No description yet."}
                                </p>

                                <div className="flex gap-2">
                                    <button
                                        onClick={(e) => { e.stopPropagation(); setSelectedNpc(n); }}
                                        className="flex-1 bg-white/5 border border-white/10 py-2 rounded text-[10px] uppercase font-bold text-gray-400 hover:text-white hover:bg-white/10 transition-colors"
                                    >
                                        View Dossier
                                    </button>
                                </div>
                            </div>
                        </div>
                    );
                })}
            </div>
        </div>
    )
}


function Grimoire({ notify }) {
    const [note, setNote] = useState("Session 1: The tavern was on fire when we arrived...");
    return (
        <div className="h-full flex flex-col animate-fade-in">
            <div className="flex justify-between items-center mb-4">
                 <h3 className={S.sectionHeader + " mb-0 border-none"}>Personal Grimoire</h3>
                 <button onClick={() => notify("Grimoire Synced")} className={S.btnPrimary}><Save size={14}/> Save Entry</button>
            </div>
            <textarea className="flex-1 bg-[#0a0a0a] border border-[#333] rounded-xl p-6 font-mono text-sm text-gray-300 focus:border-yellow-600 focus:outline-none resize-none leading-relaxed shadow-inner" 
                value={note} onChange={e => setNote(e.target.value)} />
        </div>
    )
}


function ArtGallery({ notify }) {
    const [assets, setAssets] = useState([]);
    const [loading, setLoading] = useState(true);
    const [selectedAsset, setSelectedAsset] = useState(null);

    const replaceInputRef = useRef(null);
    const [replacing, setReplacing] = useState(false);
    const [deleting, setDeleting] = useState(false);

    const apiDeleteImage = async (asset, force = false) => {
        const fn = (asset?.filename || "").toString();
        if (!fn) return;
        const ok = await rqConfirm({
            title: force ? "Force Delete Image" : "Delete Image",
            message: force
                ? `This image appears referenced by one or more NPC dossiers. Force delete "${fn}" anyway?`
                : `Delete image "${fn}" from this campaign's Vision Archive? This cannot be undone.`,
            confirmText: force ? "Force Delete" : "Delete",
            cancelText: "Cancel",
            danger: true,
        });
        if (!ok) return;

        setDeleting(true);
        try {
            await axios.delete(`${API_URL}/system/campaigns/gallery/images/${encodeURIComponent(fn)}?force=${force ? "true" : "false"}`);
            notify && notify("Image Deleted");
            setSelectedAsset(null);
            await refresh();
        } catch (e) {
            // If referenced, offer force delete
            const status = e?.response?.status;
            const detail = e?.response?.data?.detail;
            if (status === 409 && !force) {
                const refs = detail?.refs || [];
                const ok2 = await rqConfirm({
                    title: "Image In Use",
                    message: `This image is referenced by ${refs.length || "one or more"} NPC dossier(s). Force delete anyway?`,
                    confirmText: "Force Delete",
                    cancelText: "Cancel",
                    danger: true,
                });
                if (ok2) {
                    await apiDeleteImage(asset, true);
                }
            } else {
                console.error(e);
                notify && notify("Delete Failed", "error");
            }
        } finally {
            setDeleting(false);
        }
    };

    const apiReplaceImage = async (asset, file) => {
        const fn = (asset?.filename || "").toString();
        if (!fn || !file) return;
        setReplacing(true);
        try {
            const form = new FormData();
            form.append("file", file);
            await axios.post(`${API_URL}/system/campaigns/gallery/images/${encodeURIComponent(fn)}/replace`, form, {
                headers: { "Content-Type": "multipart/form-data" },
            });
            notify && notify("Image Updated");
            await refresh();
            setSelectedAsset((prev) => prev ? { ...prev, modified_epoch: Math.floor(Date.now()/1000) } : prev);
        } catch (e) {
            console.error(e);
            notify && notify("Update Failed", "error");
        } finally {
            setReplacing(false);
            try { if (replaceInputRef.current) replaceInputRef.current.value = ""; } catch {}
        }
    };
    const [query, setQuery] = useState("");
    const [kind, setKind] = useState("all");
    const [hideNpcPortraits, setHideNpcPortraits] = useState(false);
    const [showPrompt, setShowPrompt] = useState(false);
    const [refreshing, setRefreshing] = useState(false);

    const fmtEpoch = (epoch) => {
        if (!epoch) return "";
        try { return new Date(epoch * 1000).toLocaleString([], { hour12: false }); } catch { return ""; }
    };

    const copyText = async (txt) => {
        const v = (txt || "").toString();
        if (!v) return false;
        try {
            if (navigator?.clipboard?.writeText) {
                await navigator.clipboard.writeText(v);
                return true;
            }
        } catch { /* fall through */ }
        try {
            const ta = document.createElement("textarea");
            ta.value = v;
            ta.style.position = "fixed";
            ta.style.opacity = "0";
            document.body.appendChild(ta);
            ta.select();
            document.execCommand("copy");
            ta.remove();
            return true;
        } catch {
            return false;
        }
    };

    const normalizeKind = (a) => {
        const k = (a?.kind || a?.meta?.kind || "").toString().toLowerCase().trim();
        if (!k) return "unknown";
        return k;
    };

    const fetchAssets = useCallback(async () => {
        setRefreshing(true);
        try {
            const res = await axios.get(`${API_URL}/system/campaigns/gallery/images`);
            const items = res?.data?.items;
            setAssets(Array.isArray(items) ? items : []);
        } catch (e) {
            console.error(e);
            setAssets([]);
        } finally {
            setRefreshing(false);
        }
    }, []);

    useEffect(() => {
        let mounted = true;
        (async () => {
            setLoading(true);
            try {
                const res = await axios.get(`${API_URL}/system/campaigns/gallery/images`);
                const items = res?.data?.items;
                if (!mounted) return;
                setAssets(Array.isArray(items) ? items : []);
            } catch (e) {
                console.error(e);
                if (mounted) setAssets([]);
            } finally {
                if (mounted) setLoading(false);
            }
        })();
        return () => { mounted = false; };
    }, []);

    const kinds = useMemo(() => {
        const set = new Set();
        (assets || []).forEach((a) => set.add(normalizeKind(a)));
        const list = Array.from(set).filter(Boolean).sort();
        return ["all", ...list];
    }, [assets]);

    const filtered = useMemo(() => {
        const q = (query || "").trim().toLowerCase();
        return (assets || []).filter((a) => {
            const k = normalizeKind(a);
            if (kind !== "all" && k !== kind) return false;

            // Optional: hide NPC portraits (keeps the "cinematic gallery" cleaner during sessions)
            const isNpc = k.includes("npc") || k === "portrait" || (a?.meta?.npc_id || a?.meta?.npc_name);
            if (hideNpcPortraits && isNpc) return false;

            if (!q) return true;
            const hay = [
                a?.title, a?.caption, a?.prompt, a?.filename,
                a?.meta?.title, a?.meta?.caption, a?.meta?.prompt,
                a?.meta?.scene, a?.meta?.location, a?.meta?.tags
            ].filter(Boolean).join(" ").toLowerCase();
            return hay.includes(q);
        });
    }, [assets, query, kind, hideNpcPortraits]);

    const deriveTitle = (a) => {
        return a?.title || a?.meta?.title || a?.caption || a?.meta?.caption || a?.filename || "Untitled";
    };

    const deriveCaption = (a) => {
        return a?.caption || a?.meta?.caption || "";
    };

    const derivePrompt = (a) => {
        return a?.prompt || a?.meta?.prompt || "";
    };

    const deriveCreator = (a) => {
        return a?.created_by || a?.meta?.created_by || a?.meta?.author || "";
    };

    const deriveCreatedAt = (a) => {
        const v = a?.created_at || a?.meta?.created_at || a?.modified_epoch || a?.meta?.modified_epoch || null;
        return v;
    };

    const lightbox = selectedAsset ? (
        <div className="fixed inset-0 z-[9998] flex items-center justify-center bg-black/85 backdrop-blur-sm p-6 animate-fade-in">
            <div className="w-full max-w-6xl bg-[#0a0a0a]/95 border border-white/10 rounded-2xl shadow-2xl overflow-hidden">
                <div className="flex items-center justify-between px-6 py-4 border-b border-white/10 bg-white/5">
                    <div className="flex items-center gap-2">
                        <ImageIcon size={16} className="text-yellow-600" />
                        <span className="font-mono text-xs uppercase tracking-widest text-white">VISION ARCHIVE</span>
                    </div>
                    <button onClick={() => { setSelectedAsset(null); setShowPrompt(false); }} className="text-gray-500 hover:text-white transition-colors">
                        <X size={18} />
                    </button>
                </div>

                <div className="p-6">
                    <div className="bg-black/40 border border-white/10 rounded-xl overflow-hidden">
                        <img
                            src={`${API_URL}${selectedAsset.url}`}
                            alt={selectedAsset.filename || "asset"}
                            className="w-full max-h-[70vh] object-contain bg-black"
                        />
                    </div>

                    <div className="mt-4 flex flex-col md:flex-row md:items-start md:justify-between gap-4">
                        <div className="min-w-0">
                            <div className="flex items-center gap-2 flex-wrap">
                                <div className="font-mono text-[10px] uppercase tracking-widest text-gray-300 truncate">{deriveTitle(selectedAsset)}</div>
                                <span className="text-[10px] bg-yellow-900/40 px-2 py-1 rounded text-yellow-500 uppercase tracking-widest border border-yellow-500/20">
                                    {normalizeKind(selectedAsset)}
                                </span>
                                {selectedAsset?.meta?.tags && (
                                    <span className="text-[10px] bg-white/5 px-2 py-1 rounded text-gray-400 uppercase tracking-widest border border-white/10">
                                        {Array.isArray(selectedAsset.meta.tags) ? selectedAsset.meta.tags.join(", ") : String(selectedAsset.meta.tags)}
                                    </span>
                                )}
                            </div>

                            {deriveCaption(selectedAsset) && (
                                <div className="mt-2 text-sm text-gray-300 leading-relaxed">
                                    {deriveCaption(selectedAsset)}
                                </div>
                            )}

                            <div className="mt-3 font-mono text-[10px] text-gray-500 uppercase tracking-widest">
                                {null}
                                {selectedAsset.bytes ? <span> • {selectedAsset.bytes.toLocaleString()} bytes</span> : null}
                                {deriveCreatedAt(selectedAsset) ? <span> • {fmtEpoch(deriveCreatedAt(selectedAsset))}</span> : null}
                                {deriveCreator(selectedAsset) ? <span> • BY {deriveCreator(selectedAsset)}</span> : null}
                            </div>
                        </div>

                        <div className="flex items-center gap-2 md:justify-end flex-wrap">
                            
                            <input
                                ref={replaceInputRef}
                                type="file"
                                accept="image/png,image/jpeg,image/webp"
                                className="hidden"
                                onChange={(e) => {
                                    const f = e?.target?.files?.[0];
                                    if (f) apiReplaceImage(selectedAsset, f);
                                }}
                            />
                            
                            <button
                                onClick={() => apiDeleteImage(selectedAsset)}
                                className={S.btnDanger}
                                title="Delete Image"
                                disabled={replacing || deleting}
                            >
                                <Trash2 size={14}/> {deleting ? "Deleting..." : "Delete"}
                            </button>

                            {derivePrompt(selectedAsset) && (
                                <button
                                    onClick={() => setShowPrompt(p => !p)}
                                    className={S.btnSecondary}
                                    title="Toggle prompt"
                                >
                                    <Scroll size={14}/> {showPrompt ? "Hide Prompt" : "Show Prompt"}
                                </button>
                            )}

                            <a
                                href={`${API_URL}${selectedAsset.url}`}
                                target="_blank"
                                rel="noreferrer"
                                className={S.btnSecondary}
                            >
                                <Eye size={14}/> Open
                            </a>
                        </div>
                    </div>

                    {showPrompt && derivePrompt(selectedAsset) && (
                        <div className="mt-4 bg-black/40 border border-white/10 rounded-xl p-4">
                            <div className="flex items-center justify-between mb-2">
                                <div className="text-[10px] font-mono uppercase tracking-widest text-gray-500">PROMPT / CONTEXT</div>
                                <button
                                    onClick={() => copyText(derivePrompt(selectedAsset))}
                                    className="text-[10px] bg-white/5 border border-white/10 px-3 py-1 rounded uppercase font-bold text-gray-400 hover:text-white hover:bg-white/10 transition-colors flex items-center gap-2"
                                    title="Copy prompt"
                                >
                                    <Copy size={12}/> Copy
                                </button>
                            </div>
                            <div className="text-xs text-gray-300 whitespace-pre-wrap leading-relaxed">
                                {derivePrompt(selectedAsset)}
                            </div>

                            {selectedAsset?.meta && (selectedAsset.meta.scene || selectedAsset.meta.location || selectedAsset.meta.npc_name) && (
                                <div className="mt-3 pt-3 border-t border-white/10 flex flex-wrap gap-2">
                                    {selectedAsset.meta.scene && (
                                        <span className="text-[10px] bg-white/5 px-2 py-1 rounded text-gray-400 uppercase tracking-widest border border-white/10">
                                            SCENE: {String(selectedAsset.meta.scene)}
                                        </span>
                                    )}
                                    {selectedAsset.meta.location && (
                                        <span className="text-[10px] bg-white/5 px-2 py-1 rounded text-gray-400 uppercase tracking-widest border border-white/10">
                                            LOC: {String(selectedAsset.meta.location)}
                                        </span>
                                    )}
                                    {selectedAsset.meta.npc_name && (
                                        <span className="text-[10px] bg-yellow-900/30 px-2 py-1 rounded text-yellow-500 uppercase tracking-widest border border-yellow-500/20">
                                            NPC: {String(selectedAsset.meta.npc_name)}
                                        </span>
                                    )}
                                </div>
                            )}
                        </div>
                    )}
                </div>
            </div>
        </div>
    ) : null;

    return (
        <div className="animate-fade-in">
            {lightbox}

            <div className="flex items-center justify-between mb-4 gap-4">
                <div className="flex items-center gap-3 min-w-0">
                    <div className="text-[10px] font-mono uppercase tracking-widest text-gray-500">
                        IMAGES: <span className="text-gray-200">{filtered.length}</span>
                    </div>
                    <div className="hidden md:block text-[10px] font-mono uppercase tracking-widest text-gray-600 truncate">
                        SEARCHES TITLE / CAPTION / PROMPT / FILENAME
                    </div>
                </div>

                <div className="flex items-center gap-2 flex-wrap justify-end">
                    <select
                        value={kind}
                        onChange={(e) => setKind(e.target.value)}
                        className={S.input + " text-xs w-[160px] py-2"}
                        title="Filter by kind"
                    >
                        {kinds.map((k) => (
                            <option key={k} value={k}>{k.toUpperCase()}</option>
                        ))}
                    </select>

                    <input
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                        className={S.input + " w-[260px] text-xs"}
                        placeholder="Search gallery..."
                    />

                    <button
                        onClick={() => setHideNpcPortraits(p => !p)}
                        className={S.btnSecondary}
                        title="Toggle hiding NPC portraits"
                    >
                        {hideNpcPortraits ? <EyeOff size={14}/> : <Eye size={14}/>} {hideNpcPortraits ? "Show NPC" : "Hide NPC"}
                    </button>

                    <button
                        onClick={fetchAssets}
                        className={S.btnSecondary}
                        title="Refresh gallery"
                    >
                        <RefreshCw size={14} className={refreshing ? "animate-spin" : ""}/> Refresh
                    </button>
                </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
                {loading ? (
                    <div className="col-span-full text-gray-500 font-mono text-sm tracking-widest flex items-center gap-2">
                        <RefreshCw size={14} className="animate-spin" /> Loading Assets...
                    </div>
                ) : filtered.length === 0 ? (
                    <div className="col-span-full text-center text-gray-500 font-mono text-sm tracking-widest">
                        No campaign images found yet.
                    </div>
                ) : filtered.map((a, i) => {
                    const title = deriveTitle(a);
                    const k = normalizeKind(a);
                    const created = deriveCreatedAt(a);
                    const creator = deriveCreator(a);
                    const caption = deriveCaption(a);
                    const prompt = derivePrompt(a);
                    const contextText = (caption || prompt || "").toString();

                    const fullUrl = a?.url ? `${API_URL}${a.url}` : "";

                    return (
                        <div
                            key={a.url || a.filename || i}
                            onClick={() => a?.url && setSelectedAsset(a)}
                            className="bg-[#0a0a0a] border border-[#333] rounded-xl overflow-hidden group hover:border-yellow-600/50 transition-all cursor-pointer"
                            title={a.filename || "asset"}
                        >
                            <div className="h-48 relative bg-[#111] overflow-hidden">
                                {a.url ? (
                                    <img
                                        src={fullUrl}
                                        alt={a.filename || `asset-${i}`}
                                        className="w-full h-full object-cover opacity-50 group-hover:opacity-100 transition-opacity"
                                        onError={(e) => { try { e.target.style.display = 'none'; } catch {} }}
                                    />
                                ) : (
                                    <div className="w-full h-full flex items-center justify-center text-gray-700">
                                        <ImageIcon size={48} />
                                    </div>
                                )}

                                <div className="absolute bottom-0 left-0 w-full p-4 bg-gradient-to-t from-black to-transparent">
                                                                        <div className="mt-2 flex items-center gap-2 flex-wrap">
                                        <span className="text-[10px] bg-yellow-900/40 px-2 py-1 rounded text-yellow-500 uppercase tracking-widest backdrop-blur-sm border border-yellow-500/20">
                                            {k}
                                        </span>
                                        {creator && (
                                            <span className="text-[10px] bg-white/5 px-2 py-1 rounded text-gray-400 uppercase tracking-widest border border-white/10 truncate max-w-[220px]">
                                                {creator}
                                            </span>
                                        )}
                                    </div>
                                </div>
                            </div>

                            <div className="p-4">
<div className="flex justify-between text-[10px] text-gray-500 mb-2 font-mono uppercase tracking-widest">
                                    <span>{created ? "CAPTURED" : ""}</span>
                                    <span className="text-gray-400">{created ? fmtEpoch(created) : ""}</span>
                                </div>

                                <p className="text-xs text-gray-400 leading-relaxed mb-4 whitespace-pre-wrap line-clamp-4">
                                    {contextText || "No context captured yet."}
                                </p>

                                <div className="grid grid-cols-2 gap-2">
                                    <button
                                        onClick={(e) => { e.stopPropagation(); a?.url && setSelectedAsset(a); }}
                                        className="bg-white/5 border border-white/10 py-2 rounded text-[10px] uppercase font-bold text-gray-400 hover:text-white hover:bg-white/10 transition-colors"
                                    >
                                        View
                                    </button>

                                    
                                    
                                    <button
                                        onClick={(e) => { e.stopPropagation(); apiDeleteImage(a, false); }}
                                        className="bg-red-900/20 border border-red-500/20 py-2 rounded text-[10px] uppercase font-bold text-red-300 hover:text-red-200 hover:bg-red-900/30 transition-colors"
                                        disabled={replacing || deleting}
                                        title="Delete this image"
                                    >
                                        {deleting ? "Deleting..." : "Delete"}
                                    </button>
                                </div>
                            </div>
                        </div>
                    );
                })}
            </div>
        </div>
    )
}


function CharacterMatrix({ addLog, notify }) {
    const [roster, setRoster] = useState([]);

    // STARTING DATA
    const [view, setView] = useState("list");
    // FETCH (Mocked for now)
    useEffect(() => {
         // axios.get...
         setRoster([
             {name: "Valerius", level: 5, class_name: "Warlock"},
             {name: "Kaelen", level: 5, class_name: "Paladin"}
         ]);
    }, []);

    return (
        <div className="max-w-7xl mx-auto pb-20 animate-fade-in">
            <h2 className={S.header}>Hero Engine</h2>
            {/* Placeholder for future expansion */}
            <div className="bg-[#0a0a0a] border border-[#333] rounded-xl p-20 flex flex-col items-center justify-center text-center">
                <Hammer size={48} className="text-gray-700 mb-6" />
                <h3 className="font-cinematic text-2xl text-gray-500 mb-2">UNDER CONSTRUCTION</h3>
                <p className="text-xs font-mono text-gray-600 uppercase tracking-widest">Hero Matrix v2.0 Coming Soon</p>
            </div>
        </div>
    )
}

// -------------------------------------------------------------------------
// --- HELPER COMPONENTS ---
// -------------------------------------------------------------------------

function StatusCard({ title, value, icon: Icon, color, onClick, isInteractive }) {
    return (
        <div onClick={onClick} className={`bg-[#0a0a0a]/80 backdrop-blur-md border border-[#333] rounded-xl p-6 shadow-2xl transition-all duration-300 flex flex-col items-center justify-center text-center group min-h-[160px] relative overflow-hidden ${isInteractive ? "cursor-pointer hover:border-yellow-600/50 hover:bg-white/5 active:scale-95" : "hover:border-yellow-600/30"}`}>
            <Icon size={32} className={`${color} mb-4 group-hover:scale-110 
            transition-transform`} />
            <h3 className="text-[9px] uppercase tracking-[0.2em] text-gray-500 mb-2">{title}</h3>
            <p className="font-cinematic text-xl text-white capitalize">{value}</p>
            {isInteractive && <div className="absolute inset-0 bg-yellow-500/5 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none" />}
        </div>
    )
}

function ServiceRow({ name, id, onRestart, onViewLogs }) {
    return (
        <div className="flex items-center justify-between bg-white/5 p-4 rounded border border-white/5 hover:border-white/10 transition-colors">
            <div className="flex items-center gap-3"><div className="w-2 h-2 bg-green-500 rounded-full shadow-[0_0_5px_#22c55e]"></div><span className="font-mono text-xs text-gray-300 uppercase tracking-wide">{name}</span></div>
            <div className="flex gap-2"><button onClick={onViewLogs} className="p-2 hover:bg-white/10 rounded text-gray-500 hover:text-white transition-colors" title="View Logs"><Terminal size={14} /></button><button onClick={() => onRestart(id)} className="p-2 hover:bg-white/10 rounded text-gray-500 hover:text-yellow-500 transition-colors" title="Restart"><RefreshCw size={14} /></button></div>
        </div>
    )
}

function LogTerminal({ service, onClose, isModal }) {
    const [logs, setLogs] = useState("Fetching stream...");
    const fetch = async () => { 
        try { 
            const res = await axios.get(`${API_URL}/system/control/logs/${service}`); 
			// Backend returns text/plain; keep JSON compatibility if it ever changes.
			if (typeof res.data === "string") {
				setLogs(res.data.trim() ? res.data : "No logs available.");
			} else if (res.data && typeof res.data === "object") {
				setLogs(res.data.logs || JSON.stringify(res.data, null, 2));
			} else {
				setLogs("No logs available.");
			}
        } catch (e) { 
            setLogs(`[CONNECTION_ERROR] Failed to fetch logs for ${service}. \nCheck API is running on port 8000.`); 
        } 
    };

    useEffect(() => {
        fetch();
        const interval = setInterval(fetch, 3000); 
        return () => clearInterval(interval);
    }, [service]);

    return (
        <div className={isModal ? "fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-10 animate-fade-in" : "w-full h-full"}>
            <div className={isModal ? "w-full max-w-4xl h-[80vh] bg-[#0a0a0a] border border-white/20 rounded-xl shadow-2xl flex flex-col overflow-hidden" : "w-full h-full flex flex-col"}>
                <div className="h-12 border-b border-white/10 flex items-center justify-between px-6 bg-white/5"><div className="flex items-center gap-2"><Terminal size={16} className="text-yellow-600" /><span className="font-mono text-xs uppercase tracking-widest text-white">Live Terminal // {service}</span></div>
                <div className="flex gap-2">
                    <button onClick={fetch} className="text-gray-500 hover:text-white"><RefreshCw size={14} /></button>
                    {isModal && <button onClick={onClose} className="text-gray-500 hover:text-white"><X size={18} /></button>}
                </div>
                </div>
                <pre className="flex-1 p-6 font-mono text-[10px] text-gray-400 overflow-auto custom-scrollbar whitespace-pre-wrap">{logs}</pre>
            </div>
        </div>
    )
}

function CampaignSelector({ current, onClose, onSelect, notify }) { 
    const [view, setView] = useState("list");
    const [list, setList] = useState([]); 
    const [concept, setConcept] = useState(""); 
    const [draft, setDraft] = useState(null); 
    const [generating, setGenerating] = useState(false);
    const [forging, setForging] = useState(false); 
    useEffect(() => { axios.get(`${API_URL}/system/campaigns/list`).then(res => setList(res.data)); }, []);
    const activate = async (id) => { try { await axios.post(`${API_URL}/system/campaigns/activate`, {campaign_id: id}); onSelect(); onClose();
    } catch (e) { } };
    const deleteCampaign = async (id) => { if (!(await rqConfirm({ title: "Delete Campaign", message: `DELETE ${id}?`, confirmText: "Delete", cancelText: "Cancel", danger: true }))) return; try { await axios.delete(`${API_URL}/system/campaigns/delete/${id}`);
    setList(p => p.filter(c => c.id !== id)); notify("Campaign Deleted"); } catch(e) { notify("Delete Failed", "error"); } };
    const consultOracle = async () => { setGenerating(true); try { const res = await axios.post(`${API_URL}/system/campaigns/forge/preview`, { concept }); setDraft(res.data);
    } catch(e) { } setGenerating(false); };
    const forgeCartridge = async () => { setForging(true); try { await axios.post(`${API_URL}/system/campaigns/forge/create`, draft);
    const res = await axios.get(`${API_URL}/system/campaigns/list`); setList(res.data); setView("list"); notify("Campaign Forged!"); } catch (e) { notify("Forge Failed", "error"); } setForging(false); };
    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/90 backdrop-blur-md p-10 animate-fade-in">
            <div className="w-full max-w-5xl bg-[#0a0a0a] border border-white/20 rounded-xl shadow-2xl p-8 max-h-[90vh] overflow-hidden flex flex-col">
                <div className="flex justify-between items-center mb-8 border-b border-white/10 pb-4"><h2 className="font-cinematic text-2xl text-white">{view === 'list' ? "Campaign Library" : "The Deep Forge"}</h2><button onClick={onClose}><X size={24} className="text-gray-500 hover:text-white" /></button></div>
                {view 
                === 'list' && ( <div className="flex-1 overflow-auto custom-scrollbar"><div className="grid grid-cols-1 gap-4">{list.map((c) => ( <div key={c.id} className={`p-6 rounded-lg border flex justify-between items-center transition-all ${c.id === current ? "bg-yellow-900/20 border-yellow-600/50" : "bg-white/5 border-white/5 hover:bg-white/10"}`}><div><h3 className={`font-cinematic text-lg ${c.id === current ?
                "text-yellow-500" : "text-white"}`}>{c.name}</h3><p className="text-xs font-mono text-gray-500 mt-1">{c.description}</p><span className="text-[10px] font-mono text-gray-600 uppercase tracking-widest">{c.id}</span></div><div className="flex items-center gap-2">{c.id !== current && <button onClick={() => deleteCampaign(c.id)} className="p-2 text-red-900 hover:text-red-500"><Trash2 size={16} /></button>}{c.id === current ?
                <div className="flex items-center gap-2 text-green-500 text-xs font-bold uppercase tracking-widest bg-green-900/20 px-4 py-2 rounded border border-green-500/20"><CheckCircle size={14} /> Active</div> : <button onClick={() => activate(c.id)} className="px-6 py-2 bg-white/10 hover:bg-yellow-600 hover:text-black rounded text-xs font-bold uppercase tracking-widest transition-all">Load</button>}</div></div> ))}</div><div className="mt-6 pt-6 border-t border-white/10"><button onClick={() => setView('forge')} className="w-full py-4 border-2 border-dashed border-white/20 rounded-lg flex items-center justify-center gap-2 text-gray-400 hover:text-yellow-500 hover:border-yellow-500 hover:bg-yellow-900/10 transition-all group"><Sparkles size={18} className="group-hover:animate-pulse" /><span className="font-cinematic uppercase tracking-widest">Forge New Campaign</span></button></div></div> )}
                {view === 'forge' && ( <div className="flex-1 overflow-auto custom-scrollbar space-y-6">{!draft ?
                ( <div className="space-y-6"><p className="text-gray-400 text-sm font-mono text-center">Describe your vision. The Oracle will generate a comprehensive Campaign Bible (Scenes, Mysteries, Loot).</p><textarea className={S.textarea + " min-h-[150px] text-lg"} placeholder="e.g., A heist in a floating vampire city..." value={concept} onChange={e => setConcept(e.target.value)} /><button onClick={consultOracle} disabled={generating || !concept} className={S.btnPrimary + " w-full"}>{generating ? <RefreshCw className="animate-spin" /> : <Sparkles />} {generating ? "Consulting Oracle..." : "Generate Deep Blueprint"}</button></div> ) : ( <div className="space-y-6 animate-fade-in"><div className="grid grid-cols-2 gap-4"><div><label className={S.label}>Title</label><input className={S.input} value={draft.title} onChange={e => setDraft({...draft, title: e.target.value})} /></div><div><label className={S.label}>Villain</label><input className={S.input} value={draft.villain} onChange={e => setDraft({...draft, villain: e.target.value})} /></div></div><div><label className={S.label}>Pitch</label><textarea className={S.textarea} value={draft.pitch} onChange={e => setDraft({...draft, pitch: e.target.value})} /></div><div><label className={S.label}>Key Scenes (Beats)</label><div 
                className="space-y-2">{draft.scenes?.map((s, i) => (<div key={i} className="bg-white/5 p-3 rounded border border-white/5 flex gap-2 text-xs"><div className="w-1/4 font-bold text-yellow-500">{s.name}</div><div className="flex-1 text-gray-300">Goal: {s.goal} |
                Loc: {s.location}</div></div>))}</div></div><div className="grid grid-cols-2 gap-4"><div><label className={S.label}>Mysteries</label><div className="bg-black/30 p-4 rounded border border-white/5 h-32 overflow-auto text-xs text-gray-400 custom-scrollbar"><ul className="list-disc pl-4 space-y-1">{draft.mysteries?.map((m,i) => <li key={i}>{m}</li>)}</ul></div></div><div><label className={S.label}>Loot Table</label><div className="bg-black/30 p-4 rounded border border-white/5 h-32 overflow-auto text-xs text-gray-400 custom-scrollbar"><ul className="list-disc pl-4 space-y-1">{draft.loot_table?.map((l,i) => <li key={i}>{l}</li>)}</ul></div></div></div><div className="flex gap-4 pt-4 border-t border-white/10"><button onClick={() => setDraft(null)} className="flex-1 py-3 border border-white/20 rounded hover:bg-white/10 text-gray-400">Back</button><button onClick={forgeCartridge} disabled={forging} className={S.btnPrimary + " flex-1"}>{forging ?
                "Forging..." : <><Hammer size={16} /> Forge Deep Cartridge</>}</button></div></div> )}</div> )}
            </div>
        </div>
    )
}

function NavBtn({ icon: Icon, label, active, onClick }) { return ( <button onClick={onClick} className={`w-full flex items-center gap-4 px-6 py-5 text-xs font-bold uppercase tracking-widest transition-all duration-300 border-l-2 ${active ? 'bg-white/5 text-yellow-500 border-yellow-500' : 'border-transparent text-gray-500 hover:text-gray-300 hover:bg-white/5'}`}><Icon size={16} /><span 
className={active ? "text-yellow-500" : ""}>{label}</span></button> ) }
