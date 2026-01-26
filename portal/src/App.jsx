//===============================================================
//Script Name: App.jsx (v18.2 - Systems Online)
//Script Location: /opt/RealmQuest/portal/src/App.jsx
//Date: 2026-01-24
//Created By: T03KNEE
//Github: https://github.com/To3Knee/RealmQuest
//Version: 18.2.0
//About: Port Fixes, Audio Sync, Discord Live, & Config Patch
//===============================================================

import { useState, useEffect, useRef } from 'react'
import axios from 'axios'
import { 
  LayoutDashboard, Users, Mic2, Settings, Terminal, Play, 
  Palette, Server, Volume2, Lock, Eye, EyeOff, Plus, Save, 
  ShieldAlert, Key, Activity, RefreshCw, Power, Database, X,
  Sword, Shield, Heart, Coins, FolderOpen, CheckCircle, Sparkles, Hammer, Map, Trash2,
  BookOpen, HelpCircle, Gift, UserPlus, Music, Radio, Dices, UserCircle, 
  Image as ImageIcon, Scroll, Link as LinkIcon, Edit3, Send, Skull, Feather, Flame, Zap,
  Upload, ChevronDown, Repeat, Eraser, Crosshair, Headphones, Signal, CloudLightning
} from 'lucide-react'

// --- DYNAMIC CONNECTION (Fixes Port 8000/8001 mismatch) ---
const getApiUrl = () => {
    const host = window.location.hostname;
    // Default to port 8000 based on docker-compose
    return `http://${host}:8000`;
};
const API_URL = getApiUrl();

// --- STYLING CONSTANTS ---
const S = {
  card: "bg-[#0a0a0a]/90 backdrop-blur-md border border-[#333] rounded-xl p-6 shadow-2xl transition-all duration-300 hover:border-yellow-600/30",
  input: "w-full bg-black/50 border border-[#333] rounded-lg px-4 py-2 text-sm text-gray-200 focus:border-yellow-500 focus:outline-none focus:ring-1 focus:ring-yellow-500/50 transition-all font-mono",
  editableText: "bg-transparent border-b border-transparent hover:border-[#333] focus:border-yellow-600 focus:outline-none transition-colors text-center w-full",
  btnPrimary: "bg-gradient-to-r from-yellow-700 to-yellow-600 text-black font-bold uppercase tracking-widest px-6 py-3 rounded shadow-[0_0_15px_rgba(202,138,4,0.3)] hover:scale-105 hover:shadow-[0_0_25px_rgba(202,138,4,0.5)] transition-all flex items-center justify-center gap-2 text-xs cursor-pointer",
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
  const [userIsAuthenticated, setUserIsAuthenticated] = useState(false);
  const [notification, setNotification] = useState(null);

  useEffect(() => {
    const init = async () => {
        try {
            await axios.get(`${API_URL}/`);
            setStatus("online");
            // Check auth status (if endpoint exists)
	            try {
	                const authRes = await axios.get(`${API_URL}/system/auth/status`);
	                // `locked` => whether the UI should be blocked; `has_pin` => whether a PIN is configured.
	                setSystemHasPin(!!authRes.data?.has_pin);
	                setUserIsAuthenticated(!authRes.data?.locked);
	            } catch (e) { console.warn("Auth check failed, skipping lock"); }
            
            refreshData();
        } catch (e) { 
           console.error("API Connection Failed", e);
           setStatus("offline"); 
        }
    };
    init();
    const interval = setInterval(init, 10000);
    return () => clearInterval(interval);
  }, []);

  const refreshData = async () => {
      try {
        const confRes = await axios.get(`${API_URL}/system/config`);
        setConfig(confRes.data);
      } catch (e) { console.error("Config Sync error", e); }
  };

  const addLog = (source, message) => {
    const ts = new Date().toLocaleTimeString([], { hour12: false });
    setLogs(prev => [`[${ts}] [${source}] ${message}`, ...prev].slice(0, 50));
  };

  const notify = (msg, type = "info") => {
      setNotification({ msg, type });
      setTimeout(() => setNotification(null), 3000);
  };

  const showLockScreen = activeTab === 'settings' && systemHasPin && !userIsAuthenticated;

  return (
    <div className="flex h-screen bg-[#050505] text-gray-200 font-sans selection:bg-yellow-600 selection:text-black overflow-hidden relative">
      <aside className="w-80 border-r border-[#222] bg-[#080808] flex flex-col relative z-20 shadow-[5px_0_30px_rgba(0,0,0,0.5)]">
        <div className="p-8 pb-6 border-b border-[#111]">
          <h1 className="font-cinematic text-3xl font-bold tracking-widest text-white drop-shadow-[0_0_10px_rgba(255,255,255,0.2)]">REALM<span className="text-yellow-600">QUEST</span></h1>
          <div className="mt-4 flex items-center gap-3 text-[10px] font-mono tracking-[0.2em] uppercase text-gray-600">
             <div className={`w-2 h-2 rounded-full ${status === 'online' ? 'bg-green-500 shadow-[0_0_8px_#22c55e]' 
             : 'bg-red-500 animate-pulse'}`} /><span>v18.2.0 // {status}</span>
          </div>
        </div>
        <nav className="flex-1 px-6 space-y-2 mt-8 overflow-y-auto custom-scrollbar">
          <NavBtn icon={LayoutDashboard} label="Command Center" active={activeTab === 'overview'} onClick={() => setActiveTab('overview')} />
          <NavBtn icon={UserCircle} label="Player Portal" active={activeTab === 'player'} onClick={() => setActiveTab('player')} />
          <NavBtn icon={Mic2} label="Audio Matrix" active={activeTab === 'audio'} onClick={() => setActiveTab('audio')} />
          
          <div className="my-6 border-t border-[#111]" />
          
          <div className="relative group">
            <NavBtn icon={Settings} label="Neural Config" active={activeTab === 'settings'} onClick={() => setActiveTab('settings')} />
            {systemHasPin && <Lock size={14} className={`absolute right-4 top-4 ${userIsAuthenticated ?
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
        </header>
        
        <div className="flex-1 overflow-auto p-10 relative z-10 custom-scrollbar">
           {activeTab === 'overview' && <OverviewView config={config} logs={logs} addLog={addLog} onRefresh={refreshData} notify={notify} />}
           {activeTab === 'player' && <PlayerPortalView notify={notify} addLog={addLog} />}
           {activeTab === 'settings' && (showLockScreen ? <LockScreen onUnlock={() => setUserIsAuthenticated(true)} notify={notify} /> : <ConfigView onUpdate={refreshData} notify={notify} showLogout={systemHasPin && userIsAuthenticated} onLogout={async () => { await fetchJSON("system/auth/lock", { method: "POST" }); setShowLockScreen(true); await refreshData(); }} />)}
           {activeTab === 'audio' && <AudioMatrix config={config} onUpdate={refreshData} notify={notify} />}
           {activeTab === 'chars' && <CharacterMatrix addLog={addLog} notify={notify} />}
           {activeTab === 'logs' && <SystemLogsView notify={notify} />}
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

// -------------------------------------------------------------------------
// --- 1. OVERVIEW (COMMAND CENTER) ---
// -------------------------------------------------------------------------
function OverviewView({ config, logs, addLog, onRefresh, notify }) {
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
        if(!confirm("Restart ENTIRE Stack?")) return;
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
                            {logs.map((log, i) => (<div key={i} className="mb-2 border-l-2 border-yellow-900/30 pl-3 hover:bg-white/5"><span className="text-yellow-600 mr-2">{log.split(']')[0]}]</span><span className={log.includes("ERR") ? "text-red-400" : "text-gray-300"}>{log.split(']').slice(1).join(']')}</span></div>))}
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
        if(confirm(`Delete ${key} from .env? This cannot be undone.`)) {
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
                <div className="flex justify-between items-center mb-6 pb-6 border-b border-white/5">
                    <div>
                        <h3 className="font-cinematic text-xl text-white">Environment Vault (.env)</h3>
                        <p className="text-xs text-red-400 font-mono mt-2">WARNING: Direct modification of system environment variables.</p>
                    </div>
                </div>
                
                
                    {showLogout && (
                      <button
                        className="px-3 py-2 rounded bg-red-700 hover:bg-red-600 text-white text-sm"
                        onClick={async () => {
                          try {
                            if (onLogout) await onLogout();
                          } catch (e) {}
                        }}
                      >
                        Log out
                      </button>
                    )}
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
function PlayerPortalView({ notify, addLog }) {
    // STARTING DATA (Would be fetched from API in real usage)
    const [selectedChar, setSelectedChar] = useState(null);
    const [view, setView] = useState("sheet"); 
    
    // MOCK LOBBY
    const availableChars = [
        { id: 1, name: "Valerius The Void", class_name: "Warlock", level: 5, race: "Human", hp: "34", hp_max: "42", ac: "14", init: "+2", speed: "30", stats: { STR: 10, DEX: 14, CON: 16, INT: 12, WIS: 10, CHA: 18 } },
        { id: 2, name: "Kaelen Stonefist", class_name: "Paladin", level: 5, race: "Dwarf", hp: "45", hp_max: "45", ac: "18", init: "0", speed: "25", stats: { STR: 16, DEX: 10, CON: 16, INT: 8, WIS: 12, CHA: 14 } },
        { id: 3, name: "Elara Moonwhisper", class_name: "Rogue", level: 4, race: "Elf", hp: "28", hp_max: "28", ac: "15", init: "+4", speed: "35", stats: { STR: 8, DEX: 18, CON: 12, INT: 14, WIS: 12, CHA: 12 } }
    ];

    if (!selectedChar) {
        return (
            <div className="h-full flex flex-col items-center justify-center animate-fade-in">
                <div className="text-center mb-10">
                    <h1 className="font-cinematic text-5xl text-white mb-2 tracking-widest">SELECT YOUR <span className="text-yellow-600">AVATAR</span></h1>
                    <p className="text-gray-500 font-mono text-sm tracking-widest">THE REALM AWAITS YOUR PRESENCE</p>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                    {availableChars.map(c => (
                        <div key={c.id} onClick={() => setSelectedChar(c)} className="bg-[#0a0a0a] border border-[#333] rounded-xl p-8 hover:border-yellow-600 hover:scale-105 transition-all cursor-pointer group relative overflow-hidden w-64 text-center">
                            <div className="w-24 h-24 mx-auto bg-black rounded-full border-2 border-[#444] flex items-center justify-center mb-6 group-hover:border-yellow-600 transition-colors shadow-[0_0_30px_rgba(0,0,0,0.5)]">
                                <span className="font-cinematic text-4xl text-gray-500 group-hover:text-yellow-600 transition-colors">{c.name.charAt(0)}</span>
                            </div>
                            <h3 className="font-cinematic text-xl text-white mb-1 group-hover:text-yellow-500 transition-colors">{c.name}</h3>
                            <p className="text-xs font-mono text-gray-500 uppercase tracking-widest">{c.race} {c.class_name}</p>
                            <div className="mt-6 pt-6 border-t border-[#222]">
                                <span className="text-[10px] font-bold bg-white/5 px-3 py-1 rounded text-gray-400">LEVEL {c.level}</span>
                            </div>
                            <div className="absolute inset-0 bg-gradient-to-t from-yellow-900/20 to-transparent opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none" />
                        </div>
                    ))}
                </div>
            </div>
        )
    }

    // UPDATE HANDLER
    const updateChar = (field, value) => {
        setSelectedChar(prev => ({ ...prev, [field]: value }));
    };

    return (
        <div className="max-w-7xl mx-auto pb-20 animate-fade-in h-full flex flex-col">
            <PlayerHeader char={selectedChar} onUpdate={updateChar} onLogout={() => setSelectedChar(null)} notify={notify} />
            
            {/* NAVIGATION TABS */}
            <div className="flex border-b border-[#222] mb-6 overflow-x-auto custom-scrollbar">
                {[
                    {id: 'sheet', icon: Scroll, label: 'Character Sheet'}, 
                    {id: 'dice', icon: Dices, label: 'Dice Engine'}, 
                    {id: 'notes', icon: Edit3, label: 'Grimoire'}, 
                    {id: 'gallery', icon: ImageIcon, label: 'Art Gallery'},
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
function PlayerHeader({ char, onUpdate, onLogout, notify }) {
    const [discordId, setDiscordId] = useState("Link Discord");
    const [isEditingDiscord, setIsEditingDiscord] = useState(false);
    const fileInputRef = useRef(null);

    const handleAvatarClick = () => { fileInputRef.current.click(); };
    const handleFileChange = (e) => { 
        if(e.target.files[0]) notify("Avatar Updated (Mock)"); 
    };

    return (
        <div className="flex justify-between items-end mb-8 bg-[#111] p-6 rounded-xl border border-[#333] relative overflow-hidden shadow-2xl">
            <input type="file" ref={fileInputRef} className="hidden" onChange={handleFileChange} />
            
            <div className="relative z-10 flex gap-6 items-center">
                {/* CLICKABLE AVATAR */}
                <div onClick={handleAvatarClick} className="w-20 h-20 bg-black rounded-full border-2 border-yellow-600 flex items-center justify-center shadow-[0_0_20px_rgba(202,138,4,0.3)] cursor-pointer hover:scale-105 transition-transform group relative overflow-hidden">
                    <span className="font-cinematic text-3xl text-yellow-600 group-hover:opacity-0 transition-opacity">{char.name.charAt(0)}</span>
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
                                onBlur={(e) => { setDiscordId(e.target.value); setIsEditingDiscord(false); notify("Soul Linked"); }}
                                onKeyDown={(e) => { if(e.key === 'Enter') e.target.blur(); }}
                             />
                        </div>
                    ) : (
                        <button onClick={() => setIsEditingDiscord(true)} className="text-[10px] bg-indigo-900/30 text-indigo-400 border border-indigo-500/30 px-3 py-1 rounded hover:bg-indigo-500 hover:text-white transition-all uppercase tracking-widest flex items-center gap-2">
                            <LinkIcon size={12} /> {discordId}
                        </button>
                    )}
                    
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
function DiceEngine({ notify }) {
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
        setRolling(false);
    };

    const clearHistory = () => { if(confirm("Clear Roll Log?")) setHistory([]); };

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
function NPCCodex() {
    // MOCK DATA - In production, 'img_url' would come from your API/Storage
    const npcs = [
        {name: "Thalor", role: "Innkeeper", race: "Human", loc: "The Rusty Anchor", img_url: "https://i.imgur.com/8Q8q1Qy.png", desc: "A burly man with a eyepatch and a heart of gold. Knows all the rumors."},
        {name: "Lyra", role: "Spy", race: "Tiefling", loc: "Undercity", img_url: "https://i.imgur.com/J5y9QyM.png", desc: "Whispers say she serves a darker master. Always asking for a price."},
        {name: "Grum", role: "Smith", race: "Half-Orc", loc: "Market", img_url: "https://i.imgur.com/4Q4q4Qy.png", desc: "Doesn't talk much. Makes the best steel in the city."}
    ];

    return (
        <div className="animate-fade-in">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {npcs.map((n, i) => (
                    <div key={i} className="bg-[#0a0a0a] border border-[#333] rounded-xl overflow-hidden group hover:border-yellow-600/50 transition-all cursor-pointer">
                        {/* DYNAMIC IMAGE HANDLER */}
                        <div className="h-48 relative bg-[#111] overflow-hidden">
                             {n.img_url ? (
                                <img src={n.img_url} alt={n.name} className="w-full h-full object-cover opacity-50 group-hover:opacity-100 transition-opacity" onError={(e) => e.target.style.display='none'} />
                             ) : <div className="w-full h-full flex items-center justify-center text-gray-700"><UserCircle size={48} /></div>}
                             
                            <div className="absolute bottom-0 left-0 w-full p-4 bg-gradient-to-t from-black to-transparent">
                                <h3 className="font-cinematic text-2xl text-white drop-shadow-md">{n.name}</h3>
                                <span className="text-[10px] bg-yellow-900/40 px-2 py-1 rounded text-yellow-500 uppercase tracking-widest backdrop-blur-sm border border-yellow-500/20">{n.role}</span>
                            </div>
                        </div>
                        <div className="p-4">
                            <div className="flex justify-between text-xs text-gray-500 mb-2 font-mono">
                                <span>{n.race}</span>
                                <span className="text-gray-400">{n.loc}</span>
                            </div>
                            <p className="text-xs text-gray-400 leading-relaxed mb-4">{n.desc}</p>
                            <div className="flex gap-2">
                                <button className="flex-1 bg-white/5 border border-white/10 py-2 rounded text-[10px] uppercase font-bold text-gray-400 hover:text-white hover:bg-white/10 transition-colors">Stats</button>
                                <button className="flex-1 bg-white/5 border border-white/10 py-2 rounded text-[10px] uppercase font-bold text-gray-400 hover:text-white hover:bg-white/10 transition-colors">Chat</button>
                            </div>
                        </div>
                    </div>
                ))}
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

function ArtGallery() {
    return (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 animate-fade-in">
             {[1,2,3,4,5,6,7,8].map(i => (
                 <div key={i} className="aspect-square bg-[#0a0a0a] border border-[#222] rounded-lg flex items-center justify-center hover:border-yellow-600 transition-colors cursor-pointer group relative overflow-hidden">
                     <ImageIcon className="text-gray-700 group-hover:text-gray-500" size={32} />
                     <div className="absolute inset-0 bg-black/80 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                         <span className="text-[10px] uppercase tracking-widest text-white border border-white/20 px-3 py-1 rounded">View Asset</span>
                     </div>
                 </div>
             ))}
        </div>
    )
}

function CharacterMatrix({ addLog, notify }) {
    // STARTING DATA
    const [view, setView] = useState("list");
    const [roster, setRoster] = useState([]);
    
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
            <div className={S.card}>
                <p className="text-gray-500 text-center py-10 font-mono">Hero Matrix v2.0 Coming Soon</p>
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
    const deleteCampaign = async (id) => { if(!confirm(`DELETE ${id}?`)) return; try { await axios.delete(`${API_URL}/system/campaigns/delete/${id}`);
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
