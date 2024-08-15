import React, { useState, useEffect } from 'react';
import './App.css';
import './Playlists.css';
import { useNavigate } from 'react-router-dom';

const App = () => {
  const [authorized, setAuthorized] = useState(false);
  const [playlists, setPlaylists] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [isSyncing, setIsSyncing] = useState(false);
  const [syncStatus, setSyncStatus] = useState("Unsynced");
  const [syncProgressYouTube, setSyncProgressYouTube] = useState(0);
  const [syncTotalYouTube, setSyncTotalYouTube] = useState(0);
  const [syncProgressTidal, setSyncProgressTidal] = useState(0);
  const [syncTotalTidal, setSyncTotalTidal] = useState(0);
  const [syncProgressSoundCloud, setSyncProgressSoundCloud] = useState(0);
  const [syncTotalSoundCloud, setSyncTotalSoundCloud] = useState(0);
  const [showHistory, setShowHistory] = useState(false);
  const [history, setHistory] = useState([]);
  const [manualPlaylistSelections, setManualPlaylistSelections] = useState([]);
  const [showAuthorizedAccounts, setShowAuthorizedAccounts] = useState(false);
  const [authorizedAccounts, setAuthorizedAccounts] = useState([]);
  const [userId, setUserId] = useState(null);
  const [progressYoutube, setProgressYoutube] = useState(0);
  const [progressTidal, setProgressTidal] = useState(0);
  const [progressSoundCloud, setProgressSoundCloud] = useState(0);
  const [totalYoutube, setTotalYoutube] = useState(0);
  const [totalTidal, setTotalTidal] = useState(0);
  const [totalSoundCloud, setTotalSoundCloud] = useState(0);
  const [showErrorLogs, setShowErrorLogs] = useState(false);
  const [errorLogs, setErrorLogs] = useState([]);
  const [isRegistering, setIsRegistering] = useState(false);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [authError, setAuthError] = useState('');
  const [filterUsername, setFilterUsername] = useState(''); // New state for username filter
  const [filterMonth, setFilterMonth] = useState(''); // New state for month filter
  const navigate = useNavigate();

  useEffect(() => {
    const path = window.location.pathname;
    if (path.includes('/spotify-callback') || path === '/playlists') {
      setAuthorized(true);
      fetchPlaylists();
    }
  }, [navigate]);

  useEffect(() => {
    if (authorized) {
      const fetchUserData = async () => {
        try {
          const response = await fetch('/api/user-id');
          if (response.ok) {
            const data = await response.json();
            setUserId(data.user_id);
            fetchPlaylists();
          } else {
            console.error("Failed to fetch user ID", response);
          }
        } catch (err) {
          console.error("Error fetching user ID:", err);
        }
      };
      
      fetchUserData();
    }
  }, [authorized]);

  const handleLogin = async () => {
    try {
      const response = await fetch('/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ username, password }),
      });
      if (response.ok) {
        const data = await response.json();
        setAuthorized(true);
        setUserId(data.user_id);
        setAuthError('');
        navigate('/playlists');
      } else {
        const errorData = await response.json();
        setAuthError(errorData.error);
      }
    } catch (error) {
      console.error("Login error:", error);
    }
  };

  const handleRegistration = async () => {
    try {
      const response = await fetch('/register', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ username, password }),
      });
      if (response.ok) {
        await handleLogin();
        setIsRegistering(false);
      } else {
        const errorData = await response.json();
        setAuthError(errorData.error);
      }
    } catch (error) {
      console.error("Registration error:", error);
    }
  };

  const handleLogout = async () => {
    try {
      await fetch('/logout', { method: 'POST' });
      setAuthorized(false);
      setPlaylists([]);
      setManualPlaylistSelections([]);
      setShowHistory(false);
      setHistory([]);
      setShowAuthorizedAccounts(false);
      setAuthorizedAccounts([]);
      setShowErrorLogs(false);
      setErrorLogs([]);
      setSyncStatus("Unsynced");
      setUserId(null);

      navigate('/');
    } catch (error) {
      console.error("Logout error:", error);
    }
  };

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
          setSyncProgressSoundCloud(data.progress_soundcloud);
          setSyncTotalSoundCloud(data.total_soundcloud);
          console.log(`Progress YouTube: ${data.progress_youtube}/${data.total_youtube}, Tidal: ${data.progress_tidal}/${data.total_tidal}, SoundCloud: ${data.progress_soundcloud}/${data.total_soundcloud}`);
          if (data.progress_youtube >= data.total_youtube && ((data.total_youtube + data.total_tidal + data.total_tidal) !== 0) && data.progress_tidal >= data.total_tidal && data.progress_soundcloud >= data.total_soundcloud) {
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

  const handleAuthorize = () => {
    window.location.href = 'http://localhost:5000/authorize';
  };

  const handleSync = async () => {
    setIsSyncing(true);
    setSyncStatus("Synchronizing");

    try {
      await fetch('/api/select-playlists/manual', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ playlists: manualPlaylistSelections }),
      });

      const response = await fetch('/api/sync', { method: 'POST' });
      const data = await response.json();
      if (data.status === "Sync already in progress") {
        setSyncStatus("Sync already in progress");
      } else {
        const interval = setInterval(async () => {
          try {
            const statusResponse = await fetch('/api/sync/progress');
            const statusData = await statusResponse.json();
            setProgressYoutube(statusData.progress_youtube);
            setProgressTidal(statusData.progress_tidal);
            setProgressSoundCloud(statusData.progress_soundcloud);
            setTotalYoutube(statusData.total_youtube);
            setTotalTidal(statusData.total_tidal);
            setTotalSoundCloud(statusData.total_soundcloud);
            
            if (statusData.progress_youtube >= statusData.total_youtube
                && statusData.progress_tidal >= statusData.total_tidal) {
              setIsSyncing(false);
              setSyncStatus("Synced");
              clearInterval(interval);
            }
          } catch (error) {
            console.error("Error fetching sync progress:", error);
          }
        }, 1000);
      }
    } catch (error) {
      console.error("Error starting sync:", error);
      setIsSyncing(false);
      setSyncStatus("Failed to start sync");
    }
  };

  const handleShowErrorLogs = async () => {
    try {
      const response = await fetch('/api/error-logs');
      const data = await response.json();
      setErrorLogs(data);
    } catch (error) {
      console.error("Error fetching error logs:", error);
    }
    setShowErrorLogs(true);
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
  
  const handleFilterHistory = () => {
    const filteredHistory = history.filter(event => {
      const eventDate = new Date(event.timestamp || "");
      const eventMonth = (`0${eventDate.getMonth() + 1}`).slice(-2);
      const filterMonthFormatted = filterMonth ? filterMonth.padStart(2, '0') : '';
      
      const usernameMatch = filterUsername ? (event.username || '').includes(filterUsername) : true;
      const monthMatch = filterMonthFormatted ? eventMonth === filterMonthFormatted : true;

      return usernameMatch && monthMatch;
    });
    return filteredHistory;
  }

  const handleCloseHistory = () => setShowHistory(false);

  const handleCloseErrorLogs = () => setShowErrorLogs(false);

  const handleManualSelection = (e, index) => {
    const { checked, value } = e.target;
    if (checked) {
      setManualPlaylistSelections([...manualPlaylistSelections, value]);
    } else {
      setManualPlaylistSelections(manualPlaylistSelections.filter(playlist => playlist !== value));
    }
  };

  const handleShowAuthorizedAccounts = async () => {
    if (!userId) {
      console.error("User ID is not set");
      return;
    }
    try {
      const response = await fetch(`/api/sess/${userId}?spotify_username=`);
      const data = await response.json();
      console.log("Authorized accounts:", data);
      setAuthorizedAccounts(data);
    } catch (error) {
      console.error("Error fetching authorized accounts:", error);
    }
    setShowAuthorizedAccounts(true);
  };

  const handleFetchUserPlaylists = async (spotifyUsername) => {
    try {
      const response = await fetch(`/api/fetch-playlists/${userId}/${spotifyUsername}`);
      if (response.ok) {
        const data = await response.json();
        setPlaylists(data.names);
      } else {
        console.error("Failed to fetch user playlists", response);
      }
    } catch (error) {
      console.error("Error fetching user playlists:", error);
    }
  };

  const handleRemoveUserSession = async (spotifyUsername) => {
    try {
      const response = await fetch(`/api/remove-user/${userId}/${spotifyUsername}`, { method: 'DELETE' });
      if (response.ok) {
        const data = await response.json();
        setAuthorizedAccounts(authorizedAccounts.filter(account => account.spotify_username !== spotifyUsername));
        console.log(data.message);
      } else {
        console.error("Failed to remove user session", response);
      }
    } catch (error) {
      console.error("Error removing user session:", error);
    }
  };

  const handleCloseAuthorizedAccounts = () => setShowAuthorizedAccounts(false);

  const handleSearchChange = (event) => {
    setSearchTerm(event.target.value);
  };

  const handleCloseRegisterModal = () => {
    setIsRegistering(false);
  };

  const filteredPlaylists = playlists.filter(playlist =>
    playlist.toLowerCase().includes(searchTerm.toLowerCase())
  );

  if (!authorized) {
    return (
      <div className="auth-container">
        <div className="auth-box">
          <h2>Login</h2>
          <div className="auth-input-wrapper">
            <input type="text" value={username} onChange={(e) => setUsername(e.target.value)} placeholder="Username" />
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Password" />
          </div>
          <div className="auth-button-wrapper">
            <button onClick={handleLogin}>Login</button>
          </div>
          {authError && <p className="error">{authError}</p>}
        </div>
      </div>
    );
  }

  return (
    <div className="App">
      <header className="App-header">
        Playlist Syncer
        {authorized && <button onClick={handleLogout} className="button logout-button">Logout</button>}
      </header>
      <div className="container">
        <div className="left-column">
          <div className="playlists-header">
            <h2 className="playlists-title">My Playlists</h2>
            <input
              type="text"
              placeholder="Search playlists..."
              value={searchTerm}
              onChange={handleSearchChange}
              className="search-bar"
            />
          </div>
          <ul className="playlists-list">
            {filteredPlaylists.map((playlist, index) => (
              <li key={index} className="playlist-item">
                <input type="checkbox" id={`playlist-${index}`} name={playlist} value={playlist} onChange={(e) => handleManualSelection(e, index)} />
                <label htmlFor={`playlist-${index}`}>{playlist}</label>
              </li>
            ))}
          </ul>
        </div>
        <div className="right-column">
          <div className="sync-row">
            <button onClick={handleSync} disabled={isSyncing} className="button">Sync</button>
            <button onClick={handleAuthorize} disabled={false} className="button">Add Account</button>
            <button onClick={handleShowHistory} className="button">Show History</button>
            <button onClick={handleShowAuthorizedAccounts} className="button">Show Authorized Accounts</button>
            <button onClick={handleShowErrorLogs} className="button">Show Error Logs</button>
            {username === 'admin' && (
              <button onClick={() => setIsRegistering(true)} className="button">Register</button>
            )}
            {isSyncing ? <p>Synchronizing...</p> : <p>{syncStatus}</p>}
          </div>
          {isSyncing && (
            <>
              <div className="progress-bar-container">
                <div className="progress-bar" style={{ width: totalYoutube ? `${(progressYoutube / totalYoutube) * 100}%` : '0%' }}>
                  <span className="progress-label">YouTube</span>
                </div>
              </div>
              <div className="progress-bar-container">
                <div className="progress-bar" style={{ width: totalTidal ? `${(progressTidal / totalTidal) * 100}%` : '0%' }}>
                  <span className="progress-label">Tidal</span>
                </div>
              </div>
              <div className="progress-bar-container">
                <div className="progress-bar" style={{ width: totalSoundCloud ? `${(progressSoundCloud / totalSoundCloud) * 100}%` : '0%' }}>
                  <span className="progress-label">SoundCloud</span>
                </div>
              </div>
            </>
          )}
          {showHistory && (
            <div className="history-modal">
              <div className="history-modal-content">
                <span className="history-close" onClick={handleCloseHistory}>&times;</span>
                <h2>Migration History</h2>
                <div className="filter-container">
                    <input
                      type="text"
                      placeholder="Filter by username"
                      value={filterUsername}
                      onChange={e => setFilterUsername(e.target.value)}
                      className="filter-input"
                    />
                    <input
                      type="text"
                      placeholder="Filter by month (MM)"
                      value={filterMonth}
                      onChange={e => setFilterMonth(e.target.value)}
                      className="filter-input"
                    />
                </div>
                <div className="table-container">
                  <table className="history-table">
                    <thead>
                      <tr>
                        <th>Username</th> {/* Add Username header */}
                        <th>Timestamp</th>
                        <th>Playlist Name</th>
                        <th>Profile Name</th>
                        <th>Platform</th>
                      </tr>
                    </thead>
                    <tbody>
                      {handleFilterHistory().map((event, index) => (
                        <tr key={index}>
                          <td>{event.username || 'N/A'}</td> {/* Show Username in the table */}
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
            </div>
          )}
          {showErrorLogs && (
            <div className="history-modal">
              <div className="history-modal-content">
                <span className="history-close" onClick={handleCloseErrorLogs}>&times;</span>
                <h2>Error Logs</h2>
                <div className="table-container">
                  <table className="history-table">
                    <thead>
                      <tr>
                        <th>Timestamp</th>
                        <th>Message</th>
                      </tr>
                    </thead>
                    <tbody>
                      {errorLogs.map((log, index) => (
                        <tr key={index}>
                          <td>{log.timestamp}</td>
                          <td>{log.message}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}
          {showAuthorizedAccounts && (
            <div className="history-modal">
              <div className="history-modal-content">
                <span className="history-close" onClick={handleCloseAuthorizedAccounts}>&times;</span>
                <h2>Authorized Spotify Accounts</h2>
                <div className="table-container">
                  <table className="history-table">
                  <thead>
                      <tr>
                        <th>Spotify Username</th>
                        <th>Timestamp</th>
                        <th>Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {authorizedAccounts.map((account, index) => (
                        <tr key={index}>
                          <td>{account.spotify_username}</td>
                          <td>{account.timestamp}</td>
                          <td>
                            <button className="button" onClick={() => handleFetchUserPlaylists(account.spotify_username)}>Fetch Playlists</button>
                            <button className="button" onClick={() => handleRemoveUserSession(account.spotify_username)}>Remove</button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
      {isRegistering && (
        <div className="auth-overlay">
          <div className="auth-box">
            <span className="auth-close" onClick={handleCloseRegisterModal}>&times;</span>
            <h2>Register</h2>
            <div className="auth-input-wrapper">
              <input type="text" value={username} onChange={(e) => setUsername(e.target.value)} placeholder="Username" />
              <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Password" />
            </div>
            <div className="auth-button-wrapper">
              <button onClick={handleRegistration}>Register</button>
            </div>
            {authError && <p className="error">{authError}</p>}
          </div>
        </div>
      )}
    </div>
  );
};

export default App;