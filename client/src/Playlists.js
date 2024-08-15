// Playlists.js

import React, { useEffect, useState } from 'react';
import './Playlists.css';

const Playlists = () => {
  const [playlists, setPlaylists] = useState([]);
  const [isSyncing, setIsSyncing] = useState(false);
  const [syncStatus, setSyncStatus] = useState("Unsynced");
  const [syncProgressYouTube, setSyncProgressYouTube] = useState(0);
  const [syncTotalYouTube, setSyncTotalYouTube] = useState(0);
  const [syncProgressTidal, setSyncProgressTidal] = useState(0);
  const [syncTotalTidal, setSyncTotalTidal] = useState(0);
  const [showHistory, setShowHistory] = useState(false);
  const [history, setHistory] = useState([]);
  const [manualPlaylistSelections, setManualPlaylistSelections] = useState([]);

  useEffect(() => {
    const fetchPlaylists = async () => {
      try {
        const response = await fetch('/api/playlists');
        if (response.ok) {
          const data = await response.json();
          setPlaylists(data.names);
        } else {
          console.error("Failed to fetch playlists", response);
        }
      } catch (err) {
        console.error("Error fetching playlists:", err);
      }
    };

    fetchPlaylists();
  }, []);

  useEffect(() => {
    if (isSyncing) {
      const interval = setInterval(async () => {
        try {
          const response = await fetch('/api/sync/progress');
          const data = await response.json();
          setSyncProgressYouTube(data.progress_youtube);
          setSyncTotalYouTube(data.total_youtube);
          setSyncProgressTidal(data.progress_tidal);
          setSyncTotalTidal(data.total_tidal);
          console.log(`Progress YouTube: ${data.progress_youtube}/${data.total_youtube}, Tidal: ${data.progress_tidal}/${data.total_tidal}`);  // Debug output
          if (data.progress_youtube >= data.total_youtube && ((data.total_youtube + data.total_tidal) != 0) && data.progress_tidal >= data.total_tidal) {
            setIsSyncing(false);
            setSyncStatus("Synced");
            clearInterval(interval);
          }
        } catch (error) {
          console.error("Error fetching sync progress:", error);
        }
      }, 1000);

      return () => clearInterval(interval);
    }
  }, [isSyncing]);

  const handleSync = async () => {
    setIsSyncing(true);
    setSyncStatus("Synchronizing");

    // Send the manual selections to the backend
    try {
      await fetch('/api/select-playlists/manual', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ playlists: manualPlaylistSelections }),
      });
    } catch (error) {
      console.error("Error sending manual playlist selections:", error);
      setIsSyncing(false);
      setSyncStatus("Failed to start sync");
      return;
    }

    try {
      const response = await fetch('/api/sync', { method: 'POST' });
      const data = await response.json();
      if (data.status === "Sync already in progress") {
        setSyncStatus("Sync already in progress");
        setIsSyncing(true);
      }
    } catch (error) {
      console.error("Error starting sync:", error);
      setIsSyncing(false);
      setSyncStatus("Failed to start sync");
    }
  };

  const handleShowHistory = async () => {
    try {
      const response = await fetch('/api/migration-history');
      const data = await response.json();
      setHistory(data);
    } catch (error) {
      console.error("Error fetching migration history:", error);
    }
    setShowHistory(true);
  };

  const handleCloseHistory = () => setShowHistory(false);

  const handleSelectTidalPlaylists = async () => {
    try {
      const response = await fetch('/api/select-playlists/tidal');
      const data = await response.json();
      console.log(`Selected ${data.count} Tidal playlists`);
    } catch (error) {
      console.error("Error selecting Tidal playlists:", error);
    }
  };

  const handleSelectYouTubePlaylists = async () => {
    try {
      const response = await fetch('/api/select-playlists/youtube');
      const data = await response.json();
      console.log(`Selected ${data.count} YouTube playlists`);
    } catch (error) {
      console.error("Error selecting YouTube playlists:", error);
    }
  };

  const handleManualSelection = (e, index) => {
    const { checked, value } = e.target;
    if (checked) {
      setManualPlaylistSelections([...manualPlaylistSelections, value]);
    } else {
      setManualPlaylistSelections(manualPlaylistSelections.filter(playlist => playlist !== value));
    }
  };

  return (
    <div className="container">
      <div className="left-column">
        <h2 className="playlists-title">My Playlists</h2>
        <ul className="playlists-list">
          {playlists.map((playlist, index) => (
            <li key={index} className="playlist-item">
              <input 
                type="checkbox" 
                id={`playlist-${index}`} 
                name={playlist} 
                value={playlist} 
                onChange={(e) => handleManualSelection(e, index)} 
              /> 
              <label htmlFor={`playlist-${index}`}>{playlist}</label>
            </li>
          ))}
        </ul>
      </div>
      <div className="right-column">
        <div className="sync-row">
          <button onClick={handleSync} disabled={isSyncing} className="sync-button">
            Sync
          </button>
          <button onClick={handleShowHistory} className="sync-button">
            Show History
          </button>
          <button onClick={handleSelectTidalPlaylists} className="sync-button">
            Select Last 2000 Tidal Playlists
          </button>
          <button onClick={handleSelectYouTubePlaylists} className="sync-button">
            Select Last 20 YouTube Playlists
          </button>
          {isSyncing ? <p>Synchronizing...</p> : <p>{syncStatus}</p>}
        </div>
        {isSyncing && (
          <>
            <div className="progress-bar-container">
              <div className="progress-bar" style={{ width: syncTotalYouTube ? `${(syncProgressYouTube / syncTotalYouTube) * 100}%` : '0%' }}></div>
            </div>
            <div className="progress-bar-container">
              <div className="progress-bar" style={{ width: syncTotalTidal ? `${(syncProgressTidal / syncTotalTidal) * 100}%` : '0%' }}></div>
            </div>
          </>
        )}
        {showHistory && (
          <div className="history-modal">
            <div className="history-modal-content">
              <span className="history-close" onClick={handleCloseHistory}>&times;</span>
              <h2>Migration History</h2>
              <table>
                <thead>
                  <tr>
                    <th>Timestamp</th>
                    <th>Playlist Name</th>
                    <th>Profile Name</th>
                    <th>Platform</th>
                  </tr>
                </thead>
                <tbody>
                  {history.map((event, index) => (
                    <tr key={index}>
                      <td>{event.timestamp}</td>
                      <td>{event.playlist_name}</td>
                      <td>{event.profile_name}</td>
                      <td>{event.platform}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default Playlists;