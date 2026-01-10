import { useState, useEffect, useRef } from 'react'
import axios from 'axios'
import { Download, Search, CheckCircle, AlertCircle, Youtube, Film, Music } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'

const API_URL = 'http://localhost:8000';

function App() {
  const [url, setUrl] = useState('')
  const [loading, setLoading] = useState(false)
  const [videoInfo, setVideoInfo] = useState(null)
  const [selectedFormat, setSelectedFormat] = useState('')
  const [downloadStatus, setDownloadStatus] = useState(null) // { status, percent, filename, ... }
  const [error, setError] = useState('')

  const ws = useRef(null);

  useEffect(() => {
    // Connect to WebSocket
    ws.current = new WebSocket(`ws://localhost:8000/ws`);
    ws.current.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setDownloadStatus(data);
    };

    return () => {
      if (ws.current) ws.current.close();
    };
  }, []);

  const fetchInfo = async () => {
    if (!url) return;
    setLoading(true);
    setError('');
    setVideoInfo(null);
    setDownloadStatus(null);

    try {
      const res = await axios.post(`${API_URL}/info`, { url });
      setVideoInfo(res.data);
      if (res.data.formats && res.data.formats.length > 0) {
        setSelectedFormat(res.data.formats[0].format_id); // Default to first (best usually)
      }
    } catch (err) {
      console.error(err);
      setError('Failed to fetch video info. Please check the URL.');
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = async () => {
    if (!videoInfo || !selectedFormat) return;
    try {
      // Reset status locally first
      setDownloadStatus({ status: 'starting', percent: '0' });
      await axios.post(`${API_URL}/download`, {
        url,
        format_id: selectedFormat
      });
    } catch (err) {
      console.error(err);
      setError('Failed to start download.');
    }
  };

  // Auto-fetch when a valid YouTube URL is pasted
  useEffect(() => {
    const youtubeRegex = /^(https?:\/\/)?(www\.)?(youtube\.com|youtu\.be)\/.+$/;
    if (youtubeRegex.test(url) && !loading && !videoInfo) {
      const timer = setTimeout(() => {
        fetchInfo();
      }, 500); // 500ms debounce
      return () => clearTimeout(timer);
    }
  }, [url]);

  return (
    <div className="container">
      <div className="glass-panel animate-fade-in" style={{ padding: '2.5rem' }}>
        <header style={{ textAlign: 'center', marginBottom: '2rem' }}>
          <motion.div
            initial={{ scale: 0.8, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ duration: 0.5 }}
          >
            <Youtube size={48} color="#ef4444" style={{ filter: 'drop-shadow(0 0 10px rgba(239, 68, 68, 0.4))' }} />
          </motion.div>
          <h1>TubeDownloader</h1>
          <p style={{ color: 'var(--text-muted)' }}>Paste a YouTube link to get started</p>
        </header>

        <div className="input-group" style={{ display: 'flex', gap: '10px' }}>
          <input
            type="text"
            placeholder="Paste YouTube Link Here..."
            value={url}
            onChange={(e) => {
              setUrl(e.target.value);
              if (e.target.value === '') {
                setVideoInfo(null);
                setDownloadStatus(null);
              }
            }}
            onKeyDown={(e) => e.key === 'Enter' && fetchInfo()}
            style={{ flex: 1 }}
          />
          <button
            className="btn btn-primary"
            style={{ width: 'auto', padding: '0 1.5rem', whiteSpace: 'nowrap' }}
            onClick={fetchInfo}
            disabled={loading}
          >
            {loading ? <div className="spinner">...</div> : <>Get Video <Search size={18} /></>}
          </button>
        </div>

        {error && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className="error-msg"
            style={{ color: '#f87171', background: 'rgba(239,68,68,0.1)', padding: '0.8rem', borderRadius: '8px', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}
          >
            <AlertCircle size={18} />
            {error}
          </motion.div>
        )}

        <AnimatePresence>
          {videoInfo && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              style={{ overflow: 'hidden' }}
            >
              <div className="card">
                <img src={videoInfo.thumbnail} alt="Thumbnail" className="thumbnail" />
                <div className="info">
                  <h3>{videoInfo.title}</h3>
                  <p>{videoInfo.duration} seconds</p>
                </div>
              </div>

              <div className="options-grid">
                <div className="select-wrapper">
                  <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.85rem', color: 'var(--text-muted)' }}>Format</label>
                  <select
                    value={selectedFormat}
                    onChange={(e) => setSelectedFormat(e.target.value)}
                  >
                    {videoInfo.formats.map(f => (
                      <option key={f.format_id} value={f.format_id}>
                        {f.ext.toUpperCase()} - {f.resolution || 'Audio'} ({f.filesize ? (f.filesize / 1024 / 1024).toFixed(1) + ' MB' : 'N/A'})
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <button className="btn btn-primary" onClick={handleDownload}>
                <Download size={20} />
                Download Now
              </button>
            </motion.div>
          )}
        </AnimatePresence>

        {downloadStatus && (
          <motion.div
            initial={{ opacity: 0, marginTop: 0 }}
            animate={{ opacity: 1, marginTop: '1.5rem' }}
            className="status-panel"
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
              <span style={{ fontWeight: 600, fontSize: '0.9rem' }}>
                {downloadStatus.status === 'finished' ? 'Download Complete!' : 'Downloading...'}
              </span>
              <span style={{ fontSize: '0.9rem', color: 'var(--primary)' }}>{downloadStatus.percent}%</span>
            </div>

            <div className="progress-container">
              <div
                className="progress-bar"
                style={{ width: `${downloadStatus.percent || 0}%` }}
              />
            </div>

            <div className="status-text">
              <span>{downloadStatus.filename}</span>
              {downloadStatus.status === 'downloading' && (
                <span>{downloadStatus.speed} • ETA {downloadStatus.eta}</span>
              )}
            </div>

            {downloadStatus.status === 'finished' && (
              <motion.div
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                style={{ textAlign: 'center', marginTop: '1rem', color: '#4ade80' }}
              >
                <CheckCircle size={32} style={{ margin: '0 auto' }} />
                <p>Saved to downloads folder</p>
              </motion.div>
            )}
          </motion.div>
        )}
      </div>
    </div>
  )
}

export default App
