import React, { useState, useEffect } from 'react';
import './App.css';
import './Playlists.css';
import { useNavigate } from 'react-router-dom';
import { toast, ToastContainer } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';
import DatePicker from 'react-datepicker';
import 'react-datepicker/dist/react-datepicker.css';
import { format } from 'date-fns'; // Import the format function from date-fns

const App = () => {
  const [authorized, setAuthorized] = useState(false);
  const [playlists, setPlaylists] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [modalSearchTerm, setModalSearchTerm] = useState('');
  const [isSyncing, setIsSyncing] = useState(false);
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
  const [filterUsername, setFilterUsername] = useState('');
  const [owners, setOwners] = useState([]);
  const [mainFilterUsername, setMainFilterUsername] = useState('');
  const [startDate, setStartDate] = useState(null);
  const [endDate, setEndDate] = useState(null);
  const [validatedPlaylists, setValidatedPlaylists] = useState({ valid_playlists: [], invalid_playlists: [] });
  const [showValidationModal, setShowValidationModal] = useState(false);
  const [filterDescriptionLength, setFilterDescriptionLength] = useState(200);  
  const [filterPlaylistId, setFilterPlaylistId] = useState('');
  const [filterPlaylistName, setFilterPlaylistName] = useState('');
  const [filterStartDate, setFilterStartDate] = useState(null);
  const [filterEndDate, setFilterEndDate] = useState(null);
  
const sortedErrorLogs = errorLogs.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));

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
          const response = await fetch('http://localhost/api/user-id');
          if (response.ok) {
            const data = await response.json();
            setUserId(data.user_id);
            await fetchPlaylists();
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

  const formatDate = (timestamp) => {
    return format(new Date(timestamp), 'yyyy-MM-dd HH:mm:ss');
  };

  const handleLogin = async () => {
    try {
      const response = await fetch('http://localhost/login', {
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
      const response = await fetch('http://localhost/register', {
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
      await fetch('http://localhost/logout', {
        method: 'POST',
      });
      setAuthorized(false);
      setPlaylists([]);
      setManualPlaylistSelections([]);
      setShowHistory(false);
      setHistory([]);
      setShowAuthorizedAccounts(false);
      setAuthorizedAccounts([]);
      setShowErrorLogs(false);
      setErrorLogs([]);
      setUserId(null);

      navigate('/');
    } catch (error) {
      console.error("Logout error:", error);
    }
  };

  const fetchPlaylists = async () => {
    try {
      const response = await fetch('http://localhost/api/playlists', {
      });
      if (response.ok) {
        const data = await response.json();
        if (data && data.items) {
          // Set playlists
          setPlaylists(data.items);
  
          // Extract and set distinct owners for main page
          const distinctOwners = Array.from(new Set(data.items.map(pl => pl.owner.display_name)));
          setOwners(distinctOwners);
        } else {
          console.error("No items field in response data"); // Error log
        }
      } else {
        console.error("Failed to fetch playlists", response.status); // Log response status
      }
    } catch (err) {
      console.error("Error fetching playlists:", err);
    }
  };


  
  useEffect(() => {
    if (isSyncing) {
      const interval = setInterval(async () => {
        try {
          const response = await fetch('http://localhost/api/sync/progress', {
          });
          const data = await response.json();
          setSyncProgressYouTube(data.progress_youtube);
          setSyncTotalYouTube(data.total_youtube);
          setSyncProgressTidal(data.progress_tidal);
          setSyncTotalTidal(data.total_tidal);
          setSyncProgressSoundCloud(data.progress_soundcloud);
          setSyncTotalSoundCloud(data.total_soundcloud);
          if (
            data.progress_youtube >= data.total_youtube && 
            data.progress_tidal >= data.total_tidal &&
            data.progress_soundcloud >= data.total_soundcloud
          ) {
            setIsSyncing(false);
            toast.success("Synchronization completed successfully!");
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
    window.location.href = 'http://localhost/authorize';
  };

  const handleSync = async () => {
    setIsSyncing(true);

    try {
      await fetch('http://localhost/api/select-playlists/manual', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ playlists: manualPlaylistSelections }),
      });

      const response = await fetch('http://localhost/api/sync', {
        method: 'POST',
      });
      const data = await response.json();
      if (data.status === "Sync already in progress") {
        toast.info("Sync already in progress");
      } else {
        const interval = setInterval(async () => {
          try {
            const statusResponse = await fetch('http://localhost/api/sync/progress', {
            });
            const statusData = await statusResponse.json();
            setProgressYoutube(statusData.progress_youtube);
            setProgressTidal(statusData.progress_tidal);
            setProgressSoundCloud(statusData.progress_soundcloud);
            setTotalYoutube(statusData.total_youtube);
            setTotalTidal(statusData.total_tidal);
            setTotalSoundCloud(statusData.total_soundcloud);

            if (
              statusData.progress_youtube >= statusData.total_youtube &&
              statusData.progress_tidal >= statusData.total_tidal &&
              statusData.progress_soundcloud >= statusData.total_soundcloud
            ) {
              setIsSyncing(false);
              toast.success("Synchronization completed successfully!");
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
      toast.error("Failed to start sync");
    }
  };

  const handleShowErrorLogs = async () => {
    try {
      const response = await fetch('http://localhost/api/error-logs', {
      });
      const data = await response.json();
      setErrorLogs(data);
    } catch (error) {
      console.error("Error fetching error logs:", error);
    }
    setShowErrorLogs(true);
  };

  const handleShowHistory = async () => {
    try {
      const response = await fetch('http://localhost/api/migration-history', {
      });
      const data = await response.json();
      setHistory(data.reverse());
    } catch (error) {
      console.error("Error fetching migration history:", error);
    }
    setShowHistory(true);
  };

  const handleFilterHistory = () => {
    const filteredHistory = history.filter(event => {
      const eventDate = new Date(event.timestamp || "");
      const usernameMatch = filterUsername ? (event.username || '').includes(filterUsername) : true;
      const dateMatch = (!startDate || eventDate >= startDate) && (!endDate || eventDate <= endDate);
      const playlistNameMatch = filterPlaylistName ? (event.playlist_name || '').includes(filterPlaylistName) : true;
  
      return usernameMatch && dateMatch && playlistNameMatch;
    });
    return filteredHistory;
  };

  const sortedHistory = handleFilterHistory().sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
  
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
      const response = await fetch(`http://localhost/api/sess/${userId}?spotify_username=`, {
      });
      const data = await response.json();
      setAuthorizedAccounts(data);
    } catch (error) {
      console.error("Error fetching authorized accounts:", error);
    }
    setShowAuthorizedAccounts(true);
  };

  const handleFetchUserPlaylists = async (spotifyUsername) => {
    try {
      const response = await fetch(`http://localhost/api/fetch-playlists/${userId}/${spotifyUsername}`, {
      });
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
      const response = await fetch(`http://localhost/api/remove-user/${userId}/${spotifyUsername}`, {
        method: 'DELETE',
      });
      if (response.ok) {
        const data = await response.json();
        setAuthorizedAccounts(authorizedAccounts.filter(account => account.spotify_username !== spotifyUsername));
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

  const handleModalSearchChange = (event) => {
    setModalSearchTerm(event.target.value);
  };

  const handleMainFilterChange = (event) => {
    setMainFilterUsername(event.target.value);
  };

  const handleCloseRegisterModal = () => {
    setIsRegistering(false);
  };

  // Ensure playlists is defined before attempting to filter
  const filteredPlaylists = playlists?.filter(playlist =>
    (!mainFilterUsername || playlist.owner.display_name === mainFilterUsername) &&
    playlist.name.toLowerCase().includes(searchTerm.toLowerCase())
  ) ?? [];


  const handleShowValidationModal = async () => {
    setShowValidationModal(true);
    await handleFetchValidations(); // Fetch all playlists initially
  };

  const handleFetchValidations = async () => {
    const url = new URL('http://localhost/api/validate-playlists', window.location.origin);
    // Add the filter parameters to the URL
    url.searchParams.append('description_length', filterDescriptionLength);
    if (filterUsername) {
      url.searchParams.append('filter_username', filterUsername);
    }
    if (filterPlaylistId) {
      url.searchParams.append('filter_playlist_id', filterPlaylistId);
    }
    if (filterStartDate) {
      url.searchParams.append('start_date', filterStartDate.toISOString());
    }
    if (filterEndDate) {
      url.searchParams.append('end_date', filterEndDate.toISOString());
    }
  
    const response = await fetch(url, {
    });
    const data = await response.json();
  
    // Extract and set distinct owners
    const distinctOwners = Array.from(new Set(data.valid_playlists.concat(data.invalid_playlists).map(pl => pl.owner.display_name)));
    setOwners(distinctOwners);
  
    setValidatedPlaylists(data);
  };

  const handleCloseValidationModal = () => setShowValidationModal(false);

  const filteredModalPlaylists = (playlists) => {
    return playlists?.filter(playlist =>
      (!filterUsername || playlist.owner.display_name === filterUsername) &&
      (modalSearchTerm === '' || playlist.name.toLowerCase().includes(modalSearchTerm.toLowerCase()))
    ) ?? [];
  };

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
      <ToastContainer />
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
            <select
              value={mainFilterUsername}
              onChange={handleMainFilterChange}
              className="filter-input"
            >
              <option value="">All Owners</option>
              {owners.map((owner, index) => (
                <option key={index} value={owner}>{owner}</option>
              ))}
            </select>
          </div>
          <ul className="playlists-list">
            {filteredPlaylists.map((playlist, index) => {
              const displayName = playlist.name.length > 30 ? `${playlist.name.substring(0, 30)}...` : playlist.name;
              return (
                <li key={index} className="playlist-item">
                  <input type="checkbox" id={`playlist-${index}`} name={playlist.name} value={playlist.name} onChange={(e) => handleManualSelection(e, index)} />
                  <label htmlFor={`playlist-${index}`} title={playlist.name}>{displayName}</label>
                </li>
              );
            })}
          </ul>
        </div>
        <div className="right-column">
          <div className="sync-row">
            <button onClick={handleSync} disabled={isSyncing} className="button">Sync</button>
            <button onClick={handleAuthorize} disabled={false} className="button">Add Account</button>
            <button onClick={handleShowHistory} className="button">Show History</button>
            <button onClick={handleShowAuthorizedAccounts} className="button">Show Authorized Accounts</button>
            <button onClick={handleShowErrorLogs} className="button">Show Error Logs</button>
            <button onClick={handleShowValidationModal} className="button">Show Validated Playlists</button>
            {username === 'admin' && (
              <button onClick={() => setIsRegistering(true)} className="button">Register</button>
            )}
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
                  <select
                    className="filter-input"
                    value={filterPlaylistName}
                    onChange={e => setFilterPlaylistName(e.target.value)}
                  >
                    <option value="">All Playlists</option>
                    {Array.from(new Set(history.map(event => event.playlist_name))).map((playlistName, index) => (
                      <option key={index} value={playlistName}>{playlistName}</option>
                    ))}
                  </select>
                  <div className="date-picker-container">
                    <DatePicker
                      selected={startDate}
                      onChange={date => setStartDate(date)}
                      selectsStart
                      startDate={startDate}
                      endDate={endDate}
                      dateFormat="yyyy/MM/dd"
                      className="filter-input"
                      placeholderText="Start Date"
                    />
                    <DatePicker
                      selected={endDate}
                      onChange={date => setEndDate(date)}
                      selectsEnd
                      startDate={startDate}
                      endDate={endDate}
                      dateFormat="yyyy/MM/dd"
                      className="filter-input"
                      placeholderText="End Date"
                    />
                  </div>
                </div>
                <div className="table-container">
                  <table className="history-table">
                    <thead>
                      <tr>
                        <th>Username</th>
                        <th>Timestamp</th>
                        <th>Playlist Name</th>
                        <th>Profile Name</th>
                        <th>Platform</th>
                      </tr>
                    </thead>
                    <tbody>
                      {sortedHistory.map((event, index) => (
                        <tr key={index}>
                          <td>{event.username || 'N/A'}</td>
                          <td>{formatDate(event.timestamp)}</td>
                          <td className="truncated-cell" title={event.playlist_name}>
                            <a href={`https://open.spotify.com/playlist/${event.playlist_id}`} target="_blank" rel="noopener noreferrer">
                              {event.playlist_name}
                            </a>
                          </td>
                          <td className="truncated-cell" title={event.profile_name}>{event.profile_name}</td>
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
                        <th>Platform</th>
                      </tr>
                    </thead>
                    <tbody>
                      {sortedErrorLogs.map((log, index) => (
                        <tr key={index}>
                          <td>{formatDate(log.timestamp)}</td>
                          <td className="truncated-cell" title={log.message}>{log.message}</td>
                          <td>{log.platform || 'N/A'}</td>
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
                            <button className="button" onClick={() => handleFetchUserPlaylists(account.spotify_username)}>
                              Fetch Playlists
                            </button>
                            <button className="button" onClick={() => handleRemoveUserSession(account.spotify_username)}>
                              Remove
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}
          {showValidationModal && (
            <div className="history-modal">
              <div className="history-modal-content">
                <span className="history-close" onClick={handleCloseValidationModal}>&times;</span>
                <h2>Validated Playlists</h2>
                <div className="filter-container">
                  <select
                    value={filterUsername}
                    onChange={e => setFilterUsername(e.target.value)}
                    className="filter-input"
                  >
                    <option value="">All Owners</option>
                    {owners.map((owner, index) => (
                      <option key={index} value={owner}>{owner}</option>
                    ))}
                  </select>
                  <input
                    type="text"
                    placeholder="Filter by playlist name"
                    value={modalSearchTerm}
                    onChange={handleModalSearchChange}
                    className="filter-input"
                  />
                  <input
                    type="number"
                    placeholder="Description length"
                    value={filterDescriptionLength}
                    onChange={e => setFilterDescriptionLength(e.target.value)}
                    className="filter-input"
                  />
                  <select
                    value={filterPlaylistId}
                    onChange={(e) => {
                      console.log("Selected Playlist ID:", e.target.value); // Debugging log
                      setFilterPlaylistId(e.target.value);
                    }}
                    className="filter-input"
                  >
                    <option value="">Select Playlist A</option>
                    {playlists.map((playlist) => (
                      <option key={playlist.id} value={playlist.id}>{playlist.name}</option>
                    ))}
                  </select>
                  <div className="date-picker-container">
                    <DatePicker
                      selected={filterStartDate}
                      onChange={date => setFilterStartDate(date)}
                      selectsStart
                      startDate={filterStartDate}
                      endDate={filterEndDate}
                      dateFormat="yyyy/MM/dd"
                      className="filter-input"
                      placeholderText="Start Date"
                    />
                    <DatePicker
                      selected={filterEndDate}
                      onChange={date => setFilterEndDate(date)}
                      selectsEnd
                      startDate={filterStartDate}
                      endDate={filterEndDate}
                      dateFormat="yyyy/MM/dd"
                      className="filter-input"
                      placeholderText="End Date"
                    />
                  </div>
                  <button onClick={handleFetchValidations} className="button">Apply Filters</button>
                </div>
                <div className="table-container">
                  {filteredModalPlaylists(validatedPlaylists.valid_playlists).length > 0 && (
                    <>
                      <h3>Valid Playlists</h3>
                      <table className="history-table">
                        <thead>
                          <tr>
                            <th>Owner</th>
                            <th>Name</th>
                            <th>Description</th>
                            <th>Visibility</th>
                            <th>Cover Image</th>
                            <th>Tracks</th>
                          </tr>
                        </thead>
                        <tbody>
                          {filteredModalPlaylists(validatedPlaylists.valid_playlists).map((playlist, index) => (
                            <tr key={index}>
                              <td className="truncated-cell" title={playlist.owner.display_name}>{playlist.owner.display_name}</td>
                              <td className="truncated-cell"
 title={playlist.name}><a href={playlist.external_urls.spotify} target="_blank" rel="noopener noreferrer">{playlist.name}</a></td>
                              <td className="truncated-cell" title={playlist.description}>{playlist.description}</td>
                              <td>{playlist.public ? "Public" : "Private"}</td>
                              <td>{playlist.images && playlist.images.length > 0 ? <img src={playlist.images[0].url} alt="Cover" style={{ width: '50px' }} /> : 'No Image'}</td>
                              <td>{playlist.tracks.total}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </>
                  )}
                  {filteredModalPlaylists(validatedPlaylists.invalid_playlists).length > 0 && (
                    <>
                      <h3>Invalid Playlists</h3>
                      <table className="history-table">
                        <thead>
                          <tr>
                            <th>Owner</th>
                            <th>Name</th>
                            <th>Description</th>
                            <th>Visibility</th>
                            <th>Cover Image</th>
                            <th>Tracks</th>
                            <th>Reason</th>
                          </tr>
                        </thead>
                        <tbody>
                          {filteredModalPlaylists(validatedPlaylists.invalid_playlists).map((playlist, index) => (
                            <tr key={index}>
                              <td className="truncated-cell" title={playlist.owner.display_name}>{playlist.owner.display_name}</td>
                              <td className="truncated-cell" title={playlist.name}><a href={playlist.external_urls.spotify} target="_blank" rel="noopener noreferrer">{playlist.name}</a></td>
                              <td className="truncated-cell" title={playlist.description}>{playlist.description}</td>
                              <td>{playlist.public ? "Public" : "Private"}</td>
                              <td>{playlist.images && playlist.images.length > 0 ? <img src={playlist.images[0].url} alt="Cover" style={{ width: '50px' }} /> : 'No Image'}</td>
                              <td>{playlist.tracks ? playlist.tracks.total : 0}</td>
                              <td className="truncated-cell" title={playlist.reason}>{playlist.reason}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </>
                  )}
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
