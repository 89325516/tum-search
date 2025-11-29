import React, { useState, useEffect, useRef } from 'react';
import { Search, Zap, Shield, Activity, Share2, Globe, Cpu, ChevronRight, Shuffle, AlertCircle, Database, TrendingUp, Upload, Link2, FileText, X, CheckCircle2 } from 'lucide-react';

// ==========================================
// API CONFIGURATION (Import from config.js)
// ==========================================
// 注意：在实际项目中，应该从config.js导入
// 这里为了兼容性，我们内联配置
// 如果config.js被加载，window.API_CONFIG会被设置
const getAPIConfig = () => {
  if (typeof window !== 'undefined' && window.API_CONFIG) {
    return window.API_CONFIG;
  }
  // 默认配置（与config.js保持一致）
  const defaultConfig = {
    baseURL: typeof window !== 'undefined' ? window.location.origin : '',
    wsURL: (() => {
      if (typeof window === 'undefined') return '';
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      return `${protocol}//${window.location.host}`;
    })(),
    endpoints: {
      search: '/api/search',
      feedback: '/api/feedback',
      trending: '/api/trending',
      feed: '/api/feed',
      item: '/api/item',
      upload: {
        url: '/api/upload/url',
        text: '/api/upload/text',
        image: '/api/upload/image'
      }
    },
    getURL: function(endpoint) {
      if (endpoint.startsWith('http://') || endpoint.startsWith('https://')) {
        return endpoint;
      }
      return `${this.baseURL}${endpoint}`;
    },
    getWebSocketURL: function(path = '/ws') {
      return `${this.wsURL}${path}`;
    }
  };
  return defaultConfig;
};

// ==========================================
// COMPONENT: 3D PARTICLE NETWORK BACKGROUND
// ==========================================
const ParticleNetwork = () => {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    let animationFrameId;
    let width, height;
    let particles = [];

    const particleCount = 60;
    const connectionDistance = 150;
    const mouseDistance = 200;
    let mouse = { x: null, y: null };

    const resize = () => {
      width = window.innerWidth;
      height = window.innerHeight;
      canvas.width = width;
      canvas.height = height;
      initParticles();
    };

    class Particle {
      constructor() {
        this.x = Math.random() * width;
        this.y = Math.random() * height;
        this.vx = (Math.random() - 0.5) * 0.5;
        this.vy = (Math.random() - 0.5) * 0.5;
        this.size = Math.random() * 2 + 1;
        this.color = `rgba(${Math.random() * 50 + 100}, ${Math.random() * 100 + 155}, 255, ${Math.random() * 0.5 + 0.2})`;
      }

      update() {
        this.x += this.vx;
        this.y += this.vy;
        if (this.x < 0 || this.x > width) this.vx *= -1;
        if (this.y < 0 || this.y > height) this.vy *= -1;

        if (mouse.x != null) {
          let dx = mouse.x - this.x;
          let dy = mouse.y - this.y;
          let distance = Math.sqrt(dx * dx + dy * dy);
          if (distance < mouseDistance) {
            const forceDirectionX = dx / distance;
            const forceDirectionY = dy / distance;
            const force = (mouseDistance - distance) / mouseDistance;
            this.vx += forceDirectionX * force * 0.6;
            this.vy += forceDirectionY * force * 0.6;
          }
        }
      }

      draw() {
        ctx.beginPath();
        ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2);
        ctx.fillStyle = this.color;
        ctx.fill();
      }
    }

    const initParticles = () => {
      particles = [];
      for (let i = 0; i < particleCount; i++) {
        particles.push(new Particle());
      }
    };

    const animate = () => {
      ctx.clearRect(0, 0, width, height);
      
      for (let i = 0; i < particles.length; i++) {
        for (let j = i + 1; j < particles.length; j++) {
          let dx = particles[i].x - particles[j].x;
          let dy = particles[i].y - particles[j].y;
          let distance = Math.sqrt(dx * dx + dy * dy);

          if (distance < connectionDistance) {
            ctx.beginPath();
            ctx.strokeStyle = `rgba(100, 200, 255, ${1 - distance / connectionDistance})`;
            ctx.lineWidth = 0.5;
            ctx.moveTo(particles[i].x, particles[i].y);
            ctx.lineTo(particles[j].x, particles[j].y);
            ctx.stroke();
          }
        }
      }

      particles.forEach(particle => {
        particle.update();
        particle.draw();
      });

      animationFrameId = requestAnimationFrame(animate);
    };

    const handleMouseMove = (e) => {
      mouse.x = e.x;
      mouse.y = e.y;
    };

    window.addEventListener('resize', resize);
    window.addEventListener('mousemove', handleMouseMove);

    resize();
    animate();

    return () => {
      window.removeEventListener('resize', resize);
      window.removeEventListener('mousemove', handleMouseMove);
      cancelAnimationFrame(animationFrameId);
    };
  }, []);

  return (
    <canvas 
      ref={canvasRef} 
      className="fixed top-0 left-0 w-full h-full -z-10 bg-slate-900"
    />
  );
};

// ==========================================
// COMPONENT: ALGORITHM VISUALIZER
// ==========================================
const AlgorithmStep = ({ label, active, completed, icon: Icon, color }) => (
  <div className={`flex items-center gap-3 transition-all duration-300 ${active ? 'scale-105 opacity-100' : 'opacity-50'}`}>
    <div className={`w-8 h-8 rounded-full flex items-center justify-center border ${
      active || completed ? `border-${color}-500 bg-${color}-500/20 text-${color}-400` : 'border-slate-700 bg-slate-800 text-slate-600'
    }`}>
      {completed ? <div className="w-2 h-2 rounded-full bg-current" /> : <Icon size={14} />}
    </div>
    <div className="flex flex-col">
      <span className={`text-xs font-mono uppercase tracking-wider ${active ? `text-${color}-400` : 'text-slate-500'}`}>
        {label}
      </span>
      {active && (
        <span className="text-[10px] text-slate-400 animate-pulse">Processing...</span>
      )}
    </div>
  </div>
);

// ==========================================
// COMPONENT: SEARCH RESULT CARD
// ==========================================
const ResultCard = ({ item, index, onItemClick, onRecordInteraction }) => {
  const isExploration = item.is_exploration;
  const isHighTrust = item.pr > 0.8;
  
  const handleClick = (e) => {
    e.preventDefault();
    if (onRecordInteraction) {
      onRecordInteraction(item.id, item.url);
    }
    if (onItemClick) {
      onItemClick(item.id);
    }
  };
  
  return (
    <div 
      className={`group relative overflow-hidden rounded-xl border backdrop-blur-md transition-all duration-500 hover:-translate-y-1 hover:shadow-2xl cursor-pointer
        ${isExploration 
          ? 'bg-purple-900/20 border-purple-500/50 hover:border-purple-400' 
          : 'bg-slate-800/40 border-slate-700 hover:border-cyan-500/50'
        }
      `}
      onClick={handleClick}
      style={{ animationDelay: `${index * 100}ms` }}
    >
      <div className={`absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-500 bg-gradient-to-r 
        ${isExploration ? 'from-purple-600/10 to-pink-600/10' : 'from-cyan-600/10 to-blue-600/10'}`} 
      />

      <div className="p-6 relative z-10">
        <div className="flex justify-between items-start mb-3">
          <div className="flex gap-2">
             {isExploration && (
               <span className="flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-purple-500/20 text-purple-300 border border-purple-500/30">
                 <Shuffle size={10} /> Serendipity
               </span>
             )}
             {isHighTrust && (
               <span className="flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-orange-500/20 text-orange-300 border border-orange-500/30">
                 <Shield size={10} /> High Trust
               </span>
             )}
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-mono text-slate-500">SIM:</span>
            <span className={`text-sm font-bold font-mono ${isExploration ? 'text-purple-400' : 'text-cyan-400'}`}>
              {((item.score || 0) * 100).toFixed(1)}%
            </span>
          </div>
        </div>

        <h3 className="text-lg font-bold text-slate-100 mb-1 group-hover:text-cyan-300 transition-colors line-clamp-1">
          {item.url || 'Untitled Neural Node'}
        </h3>
        <div className="text-xs font-mono text-slate-500 mb-3 truncate flex items-center gap-1">
          <Globe size={10} /> {item.url}
        </div>

        <p className="text-sm text-slate-400 leading-relaxed line-clamp-3 font-light" 
           dangerouslySetInnerHTML={{
             __html: item.highlighted_snippet 
               ? item.highlighted_snippet.replace(
                   /\[\[HIGHLIGHT\]\](.*?)\[\[\/HIGHLIGHT\]\]/gi, 
                   '<strong class="font-bold text-cyan-400 bg-cyan-500/20 px-1 rounded">$1</strong>'
                 )
               : (item.content || "No neural trace available for this node.")
           }}
        />

        <div className="mt-4 pt-4 border-t border-slate-700/50 flex justify-between items-center text-xs text-slate-500">
           <div className="flex gap-3">
             <span className="flex items-center gap-1 hover:text-slate-300 transition-colors">
               <Activity size={12} /> ID: {item.id ? item.id.substring(0,6) : 'N/A'}
             </span>
           </div>
           <button className={`flex items-center gap-1 font-bold transition-colors ${isExploration ? 'text-purple-400 hover:text-purple-300' : 'text-cyan-600 hover:text-cyan-400'}`}>
             ACCESS NODE <ChevronRight size={12} />
           </button>
        </div>
      </div>
    </div>
  );
};

// ==========================================
// COMPONENT: PROGRESS TOAST
// ==========================================
const ProgressToast = ({ visible, count, message, onClose }) => {
  if (!visible) return null;
  
  return (
    <div className="fixed bottom-6 right-6 z-50 transform transition-all duration-300">
      <div className="bg-slate-800 rounded-xl shadow-xl border border-slate-700 p-4 w-80">
        <div className="flex items-center justify-between mb-2">
          <h4 className="text-sm font-bold text-slate-100">Ingesting Knowledge...</h4>
          <span className="text-xs font-mono text-cyan-600 bg-cyan-900/30 px-2 py-0.5 rounded-full">
            {count} items
          </span>
        </div>
        <div className="w-full bg-slate-700 rounded-full h-1.5 mb-2 overflow-hidden">
          <div className="bg-cyan-600 h-1.5 rounded-full animate-pulse" style={{ width: '70%' }} />
        </div>
        <p className="text-xs text-slate-400 truncate">{message || 'Processing...'}</p>
      </div>
    </div>
  );
};

// ==========================================
// COMPONENT: NOTIFICATION TOAST
// ==========================================
const NotificationToast = ({ visible, message, onClose }) => {
  if (!visible) return null;
  
  return (
    <div className="fixed bottom-5 right-5 z-50 transform transition-all duration-300">
      <div className="bg-slate-900 text-white px-6 py-4 rounded-lg shadow-2xl flex items-center gap-4 max-w-md border border-slate-700">
        <div className="flex-1">
          <h4 className="font-bold text-sm text-cyan-400 mb-1">System Update</h4>
          <p className="text-xs text-slate-300">{message}</p>
        </div>
        <button onClick={onClose} className="text-slate-500 hover:text-white">
          <X size={16} />
        </button>
      </div>
    </div>
  );
};

// ==========================================
// COMPONENT: EDUCATIONAL CARDS
// ==========================================
const EducationalCards = () => (
  <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mb-16">
    <div className="bg-slate-800/40 backdrop-blur-md p-6 rounded-xl border border-slate-700 hover:border-cyan-500/50 transition-all">
      <div className="w-10 h-10 bg-cyan-500/20 rounded-lg flex items-center justify-center mb-4 text-cyan-400">
        <Database size={20} />
      </div>
      <h3 className="text-lg font-bold text-slate-100 mb-2">Knowledge Commons</h3>
      <p className="text-sm text-slate-400">
        The raw data layer where all crawled information resides. It serves as the foundation for semantic retrieval.
      </p>
    </div>
    <div className="bg-slate-800/40 backdrop-blur-md p-6 rounded-xl border border-slate-700 hover:border-orange-500/50 transition-all">
      <div className="w-10 h-10 bg-orange-500/20 rounded-lg flex items-center justify-center mb-4 text-orange-400">
        <Shield size={20} />
      </div>
      <h3 className="text-lg font-bold text-slate-100 mb-2">Curated Core</h3>
      <p className="text-sm text-slate-400">
        A curated layer of "Novelty Anchors". Only unique, high-entropy knowledge is promoted here to form the network's backbone.
      </p>
    </div>
    <div className="bg-slate-800/40 backdrop-blur-md p-6 rounded-xl border border-slate-700 hover:border-purple-500/50 transition-all">
      <div className="w-10 h-10 bg-purple-500/20 rounded-lg flex items-center justify-center mb-4 text-purple-400">
        <Zap size={20} />
      </div>
      <h3 className="text-lg font-bold text-slate-100 mb-2">Transitive Trust</h3>
      <p className="text-sm text-slate-400">
        Authority flows through user navigation. If you trust A, and A links to B, then B gains trust.
      </p>
    </div>
  </div>
);

// ==========================================
// COMPONENT: KNOWLEDGE INJECTION PANEL
// ==========================================
const KnowledgeInjectionPanel = ({ apiConfig, onNotification }) => {
  const [urlInput, setUrlInput] = useState('');
  const [urlPassword, setUrlPassword] = useState('');
  const [textInput, setTextInput] = useState('');
  const [isUploading, setIsUploading] = useState(false);

  const handleUploadUrl = async () => {
    if (!urlInput.trim()) {
      if (onNotification) {
        onNotification("请输入URL", "error");
      }
      return;
    }
    
    if (!urlPassword.trim()) {
      if (onNotification) {
        onNotification("请输入密码", "error");
      }
      return;
    }
    
    setIsUploading(true);
    try {
      const formData = new FormData();
      formData.append('url', urlInput);
      formData.append('password', urlPassword);
      
      const response = await fetch(apiConfig.getURL(apiConfig.endpoints.upload.url), {
        method: 'POST',
        body: formData
      });
      
      const result = await response.json();
      
      if (response.ok) {
        setUrlInput('');
        setUrlPassword('');
        if (onNotification) {
          onNotification(result.message || "URL injected into the cortex. Processing...");
        }
      } else {
        if (onNotification) {
          onNotification(result.detail || "密码错误，爬取被拒绝", "error");
        }
      }
    } catch (e) {
      console.error("Failed to upload URL", e);
      if (onNotification) {
        onNotification("上传失败: " + e.message, "error");
      }
    } finally {
      setIsUploading(false);
    }
  };

  const handleUploadText = async () => {
    if (!textInput.trim()) return;
    setIsUploading(true);
    try {
      const formData = new FormData();
      formData.append('text', textInput);
      await fetch(apiConfig.getURL(apiConfig.endpoints.upload.text), {
        method: 'POST',
        body: formData
      });
      setTextInput('');
      if (onNotification) {
        onNotification("Text fragment absorbed. Processing...");
      }
    } catch (e) {
      console.error("Failed to upload text", e);
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="mt-24 border-t border-slate-700/50 pt-12">
      <h2 className="text-2xl font-bold text-slate-100 mb-6 text-center">Inject Knowledge</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 max-w-4xl mx-auto">
        <div className="bg-slate-800/40 backdrop-blur-md p-6 rounded-xl border border-slate-700">
          <h3 className="font-semibold mb-4 flex items-center text-slate-100">
            <span className="bg-cyan-500/20 text-cyan-400 text-xs font-medium mr-2 px-2.5 py-0.5 rounded border border-cyan-500/30">URL</span>
            Crawl & Absorb
          </h3>
          <div className="space-y-2">
            <input
              type="text"
              value={urlInput}
              onChange={(e) => setUrlInput(e.target.value)}
              placeholder="https://tum.de/..."
              className="w-full bg-slate-900 border border-slate-600 text-slate-100 text-sm rounded-lg focus:ring-cyan-500 focus:border-cyan-500 block p-2.5"
              onKeyPress={(e) => e.key === 'Enter' && handleUploadUrl()}
            />
            <div className="flex gap-2">
              <input
                type="password"
                value={urlPassword}
                onChange={(e) => setUrlPassword(e.target.value)}
                placeholder="输入密码..."
                className="flex-1 bg-slate-900 border border-slate-600 text-slate-100 text-sm rounded-lg focus:ring-cyan-500 focus:border-cyan-500 block p-2.5"
                onKeyPress={(e) => e.key === 'Enter' && handleUploadUrl()}
              />
              <button
                onClick={handleUploadUrl}
                disabled={isUploading}
                className="text-white bg-cyan-600 hover:bg-cyan-700 disabled:opacity-50 font-medium rounded-lg text-sm px-5 py-2.5 transition-colors"
              >
                <Upload size={16} />
              </button>
            </div>
          </div>
        </div>
        <div className="bg-slate-800/40 backdrop-blur-md p-6 rounded-xl border border-slate-700">
          <h3 className="font-semibold mb-4 flex items-center text-slate-100">
            <span className="bg-slate-500/20 text-slate-300 text-xs font-medium mr-2 px-2.5 py-0.5 rounded border border-slate-500/30">TEXT</span>
            Direct Input
          </h3>
          <div className="flex gap-2">
            <input
              type="text"
              value={textInput}
              onChange={(e) => setTextInput(e.target.value)}
              placeholder="Paste knowledge snippet..."
              className="flex-1 bg-slate-900 border border-slate-600 text-slate-100 text-sm rounded-lg focus:ring-slate-500 focus:border-slate-500 block p-2.5"
              onKeyPress={(e) => e.key === 'Enter' && handleUploadText()}
            />
            <button
              onClick={handleUploadText}
              disabled={isUploading}
              className="text-white bg-slate-700 hover:bg-slate-600 disabled:opacity-50 font-medium rounded-lg text-sm px-5 py-2.5 transition-colors"
            >
              <Upload size={16} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

// ==========================================
// COMPONENT: TRENDING SECTION
// ==========================================
const TrendingSection = ({ apiConfig, onItemClick, onRecordInteraction }) => {
  const [trending, setTrending] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadTrending = async () => {
      try {
        const response = await fetch(apiConfig.getURL(`${apiConfig.endpoints.trending}?limit=3`));
        const data = await response.json();
        if (data.results) {
          setTrending(data.results);
        }
      } catch (e) {
        console.error("Failed to load trending", e);
      } finally {
        setLoading(false);
      }
    };
    loadTrending();
  }, [apiConfig]);

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto mb-16 px-4">
        <h2 className="text-2xl font-bold text-slate-100 mb-6 flex items-center gap-2">
          <span className="w-2 h-8 bg-orange-500 rounded-full"></span>
          🔥 Trending Now
        </h2>
        <div className="text-center py-8 text-slate-400">Loading hot topics...</div>
      </div>
    );
  }

  if (trending.length === 0) {
    return (
      <div className="max-w-7xl mx-auto mb-16 px-4">
        <h2 className="text-2xl font-bold text-slate-100 mb-6 flex items-center gap-2">
          <span className="w-2 h-8 bg-orange-500 rounded-full"></span>
          🔥 Trending Now
        </h2>
        <div className="text-center py-8 text-slate-400">No trending topics yet. Start exploring!</div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto mb-16 px-4">
      <h2 className="text-2xl font-bold text-slate-100 mb-6 flex items-center gap-2">
        <span className="w-2 h-8 bg-orange-500 rounded-full"></span>
        🔥 Trending Now
      </h2>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {trending.map((item, index) => {
          const p = item.payload || {};
          return (
            <div
              key={item.id || index}
              onClick={() => {
                if (onRecordInteraction) onRecordInteraction(item.id, p.url);
                if (onItemClick) onItemClick(item.id);
              }}
              className="bg-gradient-to-br from-orange-900/30 to-slate-800/40 p-5 rounded-xl border border-orange-500/30 shadow-sm hover:shadow-md transition-all relative overflow-hidden cursor-pointer backdrop-blur-md"
            >
              <div className="absolute top-0 right-0 bg-orange-500/20 text-orange-400 text-xs font-bold px-3 py-1 rounded-bl-xl">
                #{index + 1}
              </div>
              <div className="text-xs font-bold text-orange-400 mb-2 uppercase tracking-wider">Hot Topic</div>
              <div className="text-lg font-bold text-slate-100 mb-2 line-clamp-1">{p.url || 'Untitled'}</div>
              <div className="text-sm text-slate-400 line-clamp-2 mb-3">{p.content_preview || ''}</div>
              <div className="flex items-center gap-2 text-xs text-slate-400 font-mono">
                <span className="flex items-center gap-1 text-orange-500 font-bold">
                  <TrendingUp size={12} />
                  {item.clicks || 0} Clicks
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

// ==========================================
// COMPONENT: FEED SECTION
// ==========================================
const FeedSection = ({ apiConfig, onItemClick, onRecordInteraction }) => {
  const [feed, setFeed] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadFeed = async () => {
      try {
        const response = await fetch(apiConfig.getURL(`${apiConfig.endpoints.feed}?limit=6`));
        const data = await response.json();
        if (data.points) {
          setFeed(data.points);
        }
      } catch (e) {
        console.error("Failed to load feed", e);
      } finally {
        setLoading(false);
      }
    };
    loadFeed();
  }, [apiConfig]);

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto mb-16 px-4">
        <h2 className="text-2xl font-bold text-slate-100 mb-6 flex items-center gap-2">
          <span className="w-2 h-8 bg-cyan-600 rounded-full"></span>
          Recent Knowledge Ingestions
        </h2>
        <div className="text-center py-8 text-slate-400">Loading feed...</div>
      </div>
    );
  }

  if (feed.length === 0) {
    return (
      <div className="max-w-7xl mx-auto mb-16 px-4">
        <h2 className="text-2xl font-bold text-slate-100 mb-6 flex items-center gap-2">
          <span className="w-2 h-8 bg-cyan-600 rounded-full"></span>
          Recent Knowledge Ingestions
        </h2>
        <div className="text-center py-8 text-slate-400">No knowledge found in the Commons.</div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto mb-16 px-4">
      <h2 className="text-2xl font-bold text-slate-100 mb-6 flex items-center gap-2">
        <span className="w-2 h-8 bg-cyan-600 rounded-full"></span>
        Recent Knowledge Ingestions
      </h2>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {feed.map((pt) => {
          const p = pt.payload || {};
          return (
            <div
              key={pt.id}
              onClick={() => {
                if (onRecordInteraction) onRecordInteraction(pt.id, p.url);
                if (onItemClick) onItemClick(pt.id);
              }}
              className="bg-slate-800/40 backdrop-blur-md p-5 rounded-lg border border-slate-700 shadow-sm hover:shadow-md transition-all cursor-pointer"
            >
              <div className="text-xs font-bold text-slate-400 mb-2 uppercase tracking-wider">{p.type || 'Unknown'}</div>
              <div className="text-base font-bold text-slate-100 hover:text-cyan-400 mb-2 line-clamp-1">{p.url || 'Untitled'}</div>
              <div className="text-sm text-slate-400 line-clamp-3 mb-3">{p.content_preview || ''}</div>
              <div className="text-xs text-slate-500 font-mono">ID: {pt.id ? pt.id.substring(0, 6) : 'N/A'}...</div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

// ==========================================
// MAIN APP COMPONENT
// ==========================================
export default function App() {
  const [query, setQuery] = useState("");
  const [isSearching, setIsSearching] = useState(false);
  const [results, setResults] = useState([]);
  const [searchStep, setSearchStep] = useState(0);
  const [showIntro, setShowIntro] = useState(true);
  const [progressToast, setProgressToast] = useState({ visible: false, count: 0, message: '' });
  const [notification, setNotification] = useState({ visible: false, message: '' });
  const [ws, setWs] = useState(null);
  const apiConfig = getAPIConfig();

  // WebSocket连接
  useEffect(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = apiConfig.getWebSocketURL();
    const websocket = new WebSocket(wsUrl);

    websocket.onmessage = (event) => {
      const data = JSON.parse(event.data);

      if (data.type === 'progress') {
        setProgressToast({
          visible: true,
          count: data.count || 0,
          message: data.message || data.details || 'Processing...'
        });
      } else if (data.type === 'system_update') {
        setProgressToast({
          visible: true,
          count: 'Done',
          message: data.message || 'Synchronization Complete.'
        });
        setTimeout(() => {
          setProgressToast({ visible: false, count: 0, message: '' });
        }, 5000);
        // 刷新feed和trending
        window.location.reload();
      } else if (data.type === 'error') {
        setNotification({
          visible: true,
          message: `System Error: ${data.message}`
        });
      }
    };

    websocket.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    setWs(websocket);

    return () => {
      websocket.close();
    };
  }, [apiConfig]);

  // 记录用户交互
  const recordInteraction = async (itemId, url) => {
    try {
      const formData = new FormData();
      formData.append('item_id', itemId);
      formData.append('action', 'click');
      await fetch(apiConfig.getURL(apiConfig.endpoints.feedback), {
        method: 'POST',
        body: formData,
        keepalive: true
      });
      console.log("Interaction recorded for", itemId);
    } catch (e) {
      console.error("Failed to record interaction", e);
    }
  };

  // 导航到详情页面
  const handleItemClick = (itemId) => {
    window.location.href = `/view/${itemId}`;
  };

  // 显示通知
  const showNotification = (message) => {
    setNotification({ visible: true, message });
    setTimeout(() => {
      setNotification({ visible: false, message: '' });
    }, 5000);
  };

  // 搜索功能
  const handleSearch = async (e) => {
    e?.preventDefault();
    if (!query.trim()) return;

    setIsSearching(true);
    setShowIntro(false);
    setResults([]);
    setSearchStep(1);

    setTimeout(() => {
      setSearchStep(2);
      setTimeout(() => {
        setSearchStep(3);
        setTimeout(async () => {
          try {
            const res = await fetch(apiConfig.getURL(`${apiConfig.endpoints.search}?q=${encodeURIComponent(query)}`));
            if (!res.ok) throw new Error("Backend offline");
            const data = await res.json();
            setResults(data.results || []);
          } catch (err) {
            console.warn("Backend unavailable, using mock data.");
            setResults([]);
          }
          setSearchStep(4);
          setIsSearching(false);
        }, 800);
      }, 800);
    }, 800);
  };

  return (
    <div className="min-h-screen text-slate-200 font-sans selection:bg-cyan-500/30 selection:text-cyan-200 overflow-x-hidden">
      <ParticleNetwork />

      <nav className="fixed top-0 w-full z-50 border-b border-slate-800/50 bg-slate-900/60 backdrop-blur-md">
        <div className="max-w-7xl mx-auto px-6 h-16 flex justify-between items-center">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-gradient-to-br from-cyan-500 to-blue-600 rounded-lg flex items-center justify-center shadow-[0_0_15px_rgba(6,182,212,0.5)]">
              <span className="font-bold text-white font-mono">N</span>
            </div>
            <span className="font-bold text-xl tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-cyan-400 to-blue-500">
              TUM Neural Cortex
            </span>
          </div>
          <div className="flex items-center gap-4 text-xs font-mono text-slate-400">
            <span className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
              SYSTEM ONLINE
            </span>
            <span className="opacity-50">|</span>
            <span>SPACE_X::LOADED</span>
          </div>
        </div>
      </nav>

      <main className="pt-32 pb-20 px-4 max-w-7xl mx-auto relative z-10">
        {showIntro && (
          <>
            <div className="text-center mb-16">
              <h1 className="text-5xl md:text-7xl font-extrabold mb-6 tracking-tight">
                Query the <br/>
                <span className="bg-clip-text text-transparent bg-gradient-to-r from-cyan-300 via-blue-400 to-purple-400">
                  Collective Intelligence
                </span>
              </h1>
              <p className="text-slate-400 max-w-2xl mx-auto text-lg mb-12 font-light">
                Access the high-dimensional knowledge vector space of TUM. 
                Powered by CLIP embeddings, consistency checks, and serendipity algorithms.
              </p>
            </div>

            <EducationalCards />
          </>
        )}

        <form onSubmit={handleSearch} className="relative max-w-2xl mx-auto group mb-16">
          <div className="absolute -inset-1 bg-gradient-to-r from-cyan-500 via-blue-500 to-purple-600 rounded-xl blur opacity-30 group-hover:opacity-100 transition duration-1000 group-hover:duration-200" />
          <div className="relative flex bg-slate-900 rounded-xl border border-slate-700/50 shadow-2xl overflow-hidden">
            <input 
              type="text" 
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Input neural query pattern (e.g., 'Robotics Research')..."
              className="flex-1 bg-transparent border-none text-slate-100 px-6 py-4 text-lg focus:outline-none placeholder:text-slate-600 font-light"
            />
            <button 
              type="submit" 
              disabled={isSearching}
              className="bg-slate-800 hover:bg-slate-700 text-cyan-400 px-8 py-2 font-medium transition-colors border-l border-slate-700 flex items-center gap-2"
            >
              {isSearching ? <Activity className="animate-spin" /> : <Search />}
              IGNITE
            </button>
          </div>
        </form>

        {(isSearching || searchStep > 0) && (
          <div className="mt-8 max-w-2xl mx-auto grid grid-cols-3 gap-4 p-4 rounded-xl bg-slate-900/50 border border-slate-800 backdrop-blur-sm mb-16">
            <AlgorithmStep 
              label="CLIP Embedding" 
              icon={Cpu} 
              color="cyan" 
              active={searchStep === 1} 
              completed={searchStep > 1}
            />
            <AlgorithmStep 
              label="Vector Search" 
              icon={Globe} 
              color="blue" 
              active={searchStep === 2} 
              completed={searchStep > 2}
            />
            <AlgorithmStep 
              label="Consistency & Ranking" 
              icon={Shield} 
              color="purple" 
              active={searchStep === 3} 
              completed={searchStep > 3}
            />
          </div>
        )}

        {!showIntro && searchStep === 4 && (
          <div className="mt-8 mb-16">
            <div className="flex items-center justify-between mb-6 px-2">
              <h2 className="text-xl font-bold text-slate-100 flex items-center gap-2">
                <Activity className="text-cyan-500" size={20} />
                Neural Responses
              </h2>
              <span className="text-xs font-mono text-slate-500 bg-slate-800 px-3 py-1 rounded-full">
                {results.length} NODES ACTIVATED
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {results.map((item, idx) => (
                <ResultCard 
                  key={item.id || idx} 
                  item={item} 
                  index={idx}
                  onItemClick={handleItemClick}
                  onRecordInteraction={recordInteraction}
                />
              ))}
            </div>
            
            {results.length === 0 && (
              <div className="text-center py-20 text-slate-500">
                <AlertCircle className="mx-auto mb-4 opacity-50" size={48} />
                <p>No convergent nodes found in the vector space.</p>
              </div>
            )}
          </div>
        )}

        {showIntro && (
          <>
            <TrendingSection 
              apiConfig={apiConfig}
              onItemClick={handleItemClick}
              onRecordInteraction={recordInteraction}
            />
            <FeedSection 
              apiConfig={apiConfig}
              onItemClick={handleItemClick}
              onRecordInteraction={recordInteraction}
            />
          </>
        )}

        <KnowledgeInjectionPanel 
          apiConfig={apiConfig}
          onNotification={showNotification}
        />
      </main>
      
      <ProgressToast 
        visible={progressToast.visible}
        count={progressToast.count}
        message={progressToast.message}
        onClose={() => setProgressToast({ visible: false, count: 0, message: '' })}
      />
      
      <NotificationToast 
        visible={notification.visible}
        message={notification.message}
        onClose={() => setNotification({ visible: false, message: '' })}
      />
      
      <div className="fixed bottom-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-cyan-500/50 to-transparent z-50 opacity-50" />
    </div>
  );
}
