from flask import Flask, redirect, url_for, request, jsonify, session, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import urllib
import requests
import threading
import os
import json
import tidalapi
from pymongo import MongoClient
from play_sync import create_or_update_youtube_playlist, create_or_update_tidal_playlist, create_or_update_soundcloud_playlist
import concurrent.futures
from datetime import datetime


# MongoDB setup
mongo_client = MongoClient('mongodb://localhost:27017/')
db = mongo_client['migration_db']
migration_collection = db['migration_history']
sess_collection = db['sess_collection']
error_logs_collection = db['error_logs']
user_collection = db['users']  # New collection for storing user data
credentials_collection = db['credentials']  # New collection for storing credentials

app = Flask(__name__, static_folder='./build', static_url_path='/')
app.secret_key = 'supersecretkey'  # Change this to a more secure key in production

def get_credentials(platform):
    return credentials_collection.find_one({"platform": platform})

# Load credentials
spotify_creds = get_credentials('spotify')
youtube_creds = get_credentials('youtube')
tidal_creds = get_credentials('tidal')
soundcloud_creds = get_credentials('soundcloud')

# Spotify Credentials
CLIENT_ID = spotify_creds["client_id"]
CLIENT_SECRET = spotify_creds["client_secret"]
REDIRECT_URI = spotify_creds["redirect_uri"]
FRONTEND_HOST = "http://localhost:3000"

AUTH_URL = "https://accounts.spotify.com/authorize"
TOKEN_URL = "https://accounts.spotify.com/api/token"
API_BASE_URL = "https://api.spotify.com/v1/"

# YouTube Credentials
YOUTUBE_CLIENT_ID = youtube_creds["client_id"]
YOUTUBE_CLIENT_SECRET = youtube_creds["client_secret"]
YOUTUBE_REDIRECT_URI = youtube_creds["redirect_uri"]
YOUTUBE_AUTH_URL = "https://accounts.google.com/o/oauth2/auth"
YOUTUBE_TOKEN_URL = "https://oauth2.googleapis.com/token"
YOUTUBE_API_BASE_URL = "https://www.googleapis.com/youtube/v3/"

# TIDAL Credentials
TIDAL_CLIENT_ID = tidal_creds["client_id"]
TIDAL_CLIENT_SECRET = tidal_creds["client_secret"]
TIDAL_REDIRECT_URI = tidal_creds["redirect_uri"]
TIDAL_TOKEN_URL = "https://auth.tidal.com/v1/oauth2/token"
TIDAL_AUTH_URL = "https://login.tidal.com/authorize"


#Sound Cloud credentials
SOUNDCLOUD_CLIENT_ID = soundcloud_creds["client_id"]
SOUNDCLOUD_CLIENT_SECRET = soundcloud_creds["client_secret"]
SOUNDCLOUD_REDIRECT_URI = soundcloud_creds["redirect_uri"]
SOUNDCLOUD_CODE_VERIFIER = '3604440048217d04da94c51f24d7d6e331940ca96246abc454f57dfc'  # Securely stored and generated
SOUNDCLOUD_CODE_CHALLENGE = 'b1ffoyo3FDGmnq6yp5xhsmJ-Y43eWhAx7kUSZ5XFWGI'
SOUNDCLOUD_STATE = os.urandom(24).hex()  # Securely generate a random state


sync_in_progress = False
sync_progress_youtube = 0
sync_progress_tidal = 0
sync_progress_soundcloud = 0
sync_total_youtube = 0
playlists = []
sync_total_tidal = 0
sync_total_soundcloud = 0
last_synced_index = 0  # Default to start from the beginning
sess = {"spotify": dict(), "tidal": dict(), "youtube":dict(), "soundcloud":dict(), "manual_playlists": []}

def log_error(message, user_id):
    try:
        error_logs_collection.insert_one({
            "message": message,
            "user_id": user_id,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        print(f"Error logging error message: {e}")

def store_sess(user_id, spotify_username, sess):
    try:
        result = sess_collection.update_one(
            {"user_id": user_id, "spotify_username": spotify_username},
            {"$set": {"sess": sess, "timestamp": datetime.now()}},
            upsert=True
        )
        print(f'Successfully stored sess for user {user_id} and Spotify user {spotify_username}, Matched count: {result.matched_count}, Modified count: {result.modified_count}')
    except Exception as e:
        print(f"Error storing sess: {e}")

def fetch_sess_by_user(user_id, spotify_username=None):
    try:
        query = {"user_id": user_id}
        if spotify_username:
            query["spotify_username"] = spotify_username
        user_sess = list(sess_collection.find(query, {'_id': 0, 'spotify_username': 1, 'timestamp': 1}))
        print(f"Fetched sess for user_id: {user_id}, spotify_username: {spotify_username}, result: {user_sess}")
        return [{"spotify_username": sess["spotify_username"], "timestamp": sess["timestamp"]} for sess in user_sess]
    except Exception as e:
        print(f"Error fetching sess for user {user_id}: {e}")
        return []

def log_migration(event):
    try:
        migration_collection.insert_one(event)
    except Exception as e:
        print(f"Error logging migration: {e}")

def fetch_migration_history(user_id):
    try:
        return list(migration_collection.find({"user_id": user_id}, {'_id': 0}))[::-1]
    except Exception as e:
        print(f"Error fetching migration history: {e}")
        return []
    
# Function to store migration history
def save_migration_history(username, playlist_name, profile_name, platform):
    migration_collection.insert_one({
        "username": username,  # Adding username to migration history
        "timestamp": datetime.now().isoformat(),
        "playlist_name": playlist_name,
        "profile_name": profile_name,
        "platform": platform
    })


@app.route('/favicon.ico')
def favicon():
    return '', 204

@app.errorhandler(404)
def not_found(e):
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/api/migration-history', methods=['GET'])
def get_migration_history():
    user_id = session.get('user_id')
    username = session.get('username')
    if not username:
        return jsonify({"status": "failure", "error": "Not logged in"}), 401

    """
    if not user_id:
        return jsonify({"error": "User not logged in"}), 401
    history = fetch_migration_history(user_id)
    """
    history = None
    if username == 'admin':
        history = list(migration_collection.find({}))[::-1]
    else:
        history = list(migration_collection.find({"username": username}))[::-1]
    
        
    for event in history:
        event["_id"] = str(event["_id"])
    return jsonify(history), 200

def get_playlist_data(playlist_id, access_token):
    endpoint = f"https://api.spotify.com/v1/playlists/{playlist_id}"
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    response = requests.get(endpoint, headers=headers)
    
    if response.status_code != 200:
        print(f"Failed to fetch data for playlist: {playlist_id}, status code: {response.status_code}")
        return None

    playlist_info = response.json()
    name = playlist_info.get('name', 'No name')
    description = playlist_info.get('description', 'No description')
    owner_info = playlist_info.get('owner', {})
    owner = owner_info.get('display_name', 'Unknown')
    cover_image_url = playlist_info['images'][0]['url'] if playlist_info['images'] else None
    visibility = 'public' if playlist_info.get('public', False) else 'private'
    tracks = []
    for item in playlist_info.get('tracks', {}).get('items', []):
        track = item.get('track', {})
        track_name = track.get('name', 'Unknown track')
        artists = ", ".join(artist['name'] for artist in track.get('artists', []))
        tracks.append(f"{track_name} by {artists}")
    playlist_data = {
        'name': name,
        'description': description,
        'owner': owner,
        'cover_image_url': cover_image_url,
        'visibility': visibility,
        'tracks': tracks
    }
    print(playlist_data)
    return playlist_data

@app.errorhandler(405)
def method_not_allowed(e):
    return jsonify(error="Method not allowed"), 405

@app.errorhandler(500)
def internal_server_error(e):
    return jsonify(error="Internal server error"), 500

@app.errorhandler(Exception)
def handle_exception(e):
    response = e.get_response()
    response.data = json.dumps({
        "code": e.code,
        "name": e.name,
        "description": e.description,
    })
    response.content_type = "application/json"
    user_id = session.get('user_id', None)
    log_error(f"{e.name}: {e.description}", user_id)
    return response

@app.route('/api/sync', methods=['POST'])
def sync_playlists():
    global sync_in_progress, sync_progress_youtube, sync_progress_tidal, sync_progress_soundcloud, sync_total_youtube, sync_total_tidal, sync_total_soundcloud, sess, playlists, last_synced_index

    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "User not logged in"}), 401

    if sync_in_progress:
        return jsonify({"status": "Sync already in progress"}), 200

    playlists = get_manual_or_spotify_playlists()
    print("---> Fetched playlists:", playlists)
    
    if len(playlists) != sync_total_youtube + sync_total_tidal + sync_total_soundcloud:
        sync_progress_youtube = 0
        sync_progress_tidal = 0
        sync_progress_soundcloud = 0
        sync_total_youtube = 0
        sync_total_tidal = 0
        sync_total_soundcloud = 0
        last_synced_index = 0

    threading.Thread(target=backend_sync_task, args=(user_id,)).start()
    return jsonify({"status": "Sync started"}), 200

@app.route('/api/error-logs', methods=['GET'])
def get_error_logs():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "User not logged in"}), 401
    try:
        error_logs = list(error_logs_collection.find({"user_id": user_id}, {'_id': 0}))
        return jsonify(error_logs)
    except Exception as e:
        print(f"Error fetching error logs: {e}")
        return jsonify({"error": "Failed to fetch error logs"}), 500



import concurrent.futures
import threading
from datetime import datetime

# Initialize locks for thread-safe updates
youtube_lock = threading.Lock()
soundcloud_lock = threading.Lock()
tidal_lock = threading.Lock()

def backend_sync_task(user_id):
    global sync_in_progress, sync_progress_youtube, sync_progress_tidal, sync_progress_soundcloud
    global sync_total_youtube, sync_total_tidal, sync_total_soundcloud, sess, playlists, last_synced_index

    sync_in_progress = True
    sync_total_youtube = min(len(playlists), 20)
    sync_total_tidal = min(len(playlists), 2000)
    sync_total_soundcloud = min(len(playlists), 20)

    print("HERE USERNAME", username)

    def create_or_update_playlist(platform, create_or_update_func, pl, oauth, event):
        try:
            create_or_update_func(pl, oauth)
            if platform == "YouTube":
                with youtube_lock:
                    global sync_progress_youtube
                    sync_progress_youtube += 1
                    print(f"Sync YouTube progress: {sync_progress_youtube}/{sync_total_youtube}")
            elif platform == "SoundCloud":
                with soundcloud_lock:
                    global sync_progress_soundcloud
                    sync_progress_soundcloud += 1
                    print(f"Sync SoundCloud progress: {sync_progress_soundcloud}/{sync_total_soundcloud}")
            elif platform == "Tidal":
                with tidal_lock:
                    global sync_progress_tidal
                    sync_progress_tidal += 1
                    print(f"Sync Tidal progress: {sync_progress_tidal}/{sync_total_tidal}")

            event["platform"] = platform
            log_migration(event)
            #save_migration_history(sess['username'], pl['name'], sess["spotify"]["user_id"], platform)
        except Exception as e:
            log_error(f"Error syncing playlist {pl['name']} on {platform}: {e}", user_id)
            sync_in_progress = False

    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = []
        for i in range(last_synced_index, len(playlists)):
            pl = playlists[i]
            event = {
                "playlist_name": pl['name'],
                "profile_name": sess["spotify"]["user_id"],
                "timestamp": datetime.now().isoformat(),
                "user_id": user_id,
                "username": username
            }
            if i < 20:
                futures.append(executor.submit(create_or_update_playlist, "YouTube", create_or_update_youtube_playlist, pl, "oauth.json", event))
                futures.append(executor.submit(create_or_update_playlist, "SoundCloud", create_or_update_soundcloud_playlist, pl, sess["soundcloud"]["oauth"], event))

            if i < 2000:
                futures.append(executor.submit(create_or_update_playlist, "Tidal", create_or_update_tidal_playlist, pl, sess["tidal"]["oauth"], event))

            last_synced_index = i + 1  # Update the last synced index only on success

        concurrent.futures.wait(futures)

    sync_in_progress = False
    sync_progress_youtube = 0
    sync_progress_tidal = 0
    sync_progress_soundcloud = 0
    sync_total_youtube = 0
    sync_total_tidal = 0
    sync_total_soundcloud = 0
    last_synced_index = 0  # Reset for next full sync
    sess["manual_playlists"] = []



@app.route('/api/sync/progress', methods=['GET'])
def sync_progress_status():
    global sync_progress_youtube, sync_total_youtube, sync_progress_tidal, sync_total_tidal, sync_progress_soundcloud, sync_total_soundcloud
    print(f"Fetching progress: YouTube {sync_progress_youtube}/{sync_total_youtube}, Tidal {sync_progress_tidal}/{sync_total_tidal}, SoundCloud {sync_progress_soundcloud}/{sync_total_soundcloud}")  
    return jsonify({
        "progress_youtube": sync_progress_youtube, 
        "total_youtube": sync_total_youtube, 
        "progress_tidal": sync_progress_tidal, 
        "total_tidal": sync_total_tidal,
        "progress_soundcloud": sync_progress_soundcloud, 
        "total_soundcloud": sync_total_soundcloud
    })

@app.route('/api/select-playlists/tidal', methods=['GET'])
def select_tidal_playlists():
    global sess
    sess["tidal"]["playlists_uri"] = sess["tidal"]["playlists_uri"][:2000]
    return jsonify({"status": "selected", "count": len(sess["tidal"]["playlists_uri"])})

@app.route('/api/select-playlists/youtube', methods=['GET'])
def select_youtube_playlists():
    global sess
    sess["youtube"]["playlists_uri"] = sess["youtube"]["playlists_uri"][:20]
    return jsonify({"status": "selected", "count": len(sess["youtube"]["playlists_uri"])})

@app.route('/api/select-playlists/soundcloud', methods=['GET'])
def select_soundcloud_playlists():
    global sess
    sess["soundcloud"]["playlists_uri"] = sess["soundcloud"]["playlists_uri"][:20]
    return jsonify({"status": "selected", "count": len(sess["soundcloud"]["playlists_uri"])})

@app.route('/api/select-playlists/manual', methods=['POST'])
def select_manual_playlists():
    global sess
    data = request.get_json()
    sess["manual_playlists"] = data['playlists']
    print(sess["manual_playlists"])
    return jsonify({"status": "Manual playlists selection received"})

def get_manual_or_spotify_playlists():
    global sess
    return get_pls()

@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/authorize')
def authorize():
    scope = "user-read-private user-read-email playlist-read-private"
    params = {
        'client_id': CLIENT_ID,
        'response_type': 'code',
        'scope': scope,
        'redirect_uri': REDIRECT_URI,
        'show_dialog': True
    }
    auth_url = f"{AUTH_URL}?{urllib.parse.urlencode(params)}"
    return redirect(auth_url)

@app.route('/spotify-callback')
def spotify_callback():
    global sess
    if 'error' in request.args:
        return jsonify({"error": request.args['error']})

    if 'code' in request.args:
        req_body = {
            'code': request.args['code'],
            'grant_type': 'authorization_code',
            'redirect_uri': REDIRECT_URI,
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET
        }
        response = requests.post(TOKEN_URL, data=req_body)

        try:
            token_info = response.json()
        except requests.exceptions.JSONDecodeError:
            print("Failed to retrieve JSON response for token exchange")
            return jsonify({"error": "Failed to retrieve access token"}), 500

        if 'access_token' not in token_info:
            print("Access token not found in token info:", token_info)
            return jsonify({"error": "Failed to retrieve access token"}), 500

        access_token = token_info['access_token']
        refresh_token = token_info.get('refresh_token')
        expires_at = datetime.now().timestamp() + token_info.get('expires_in', 3600)  # Default to 1 hour

        session['access_token'] = access_token
        session['refresh_token'] = refresh_token
        session['expires_at'] = expires_at

        # Get user's profile information
        headers = {
            'Authorization': f'Bearer {access_token}'
        }
        user_profile_url = "https://api.spotify.com/v1/me"
        user_response = requests.get(user_profile_url, headers=headers)

        try:
            user_info = user_response.json()
        except requests.exceptions.JSONDecodeError as e:
            print(f"Error parsing Spotify user profile response: {e}")
            return jsonify({"error": "Failed to retrieve user information", "details": str(e)}), 500

        if 'id' not in user_info:
            print("User ID not found in user info:", user_info)
            return jsonify({"error": "Failed to retrieve user information"}), 500

        spotify_username = user_info['id']

        session['spotify_username'] = spotify_username
        sess = {
            "spotify": {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "expires_at": expires_at,
                "user_id": spotify_username,
                "username": user_info.get('display_name', spotify_username)
            }
        }

        user_id = session.get('user_id')
        if user_id:
            print("Storing Spotify credentials in MongoDB")
            store_sess(user_id, spotify_username, sess)
        else:
            print("User ID missing, cannot store session data")
    return redirect('/youtube-authorize')

@app.route('/youtube-authorize')
def youtube_authorize():
    scope = "https://www.googleapis.com/auth/youtube.readonly"
    params = {
        'client_id': YOUTUBE_CLIENT_ID,
        'response_type': 'code',
        'scope': scope,
        'redirect_uri': YOUTUBE_REDIRECT_URI,
        'access_type': 'offline',
        'prompt': 'consent'
    }
    auth_url = f"{YOUTUBE_AUTH_URL}?{urllib.parse.urlencode(params)}"
    return redirect(auth_url)

@app.route('/youtube-callback')
def youtube_callback():
    if 'error' in request.args:
        return jsonify({"error": request.args['error']})
    if 'code' in request.args:
        req_body = {
            'code': request.args['code'],
            'grant_type': 'authorization_code',
            'redirect_uri': YOUTUBE_REDIRECT_URI,
            'client_id': YOUTUBE_CLIENT_ID,
            'client_secret': YOUTUBE_CLIENT_SECRET
        }
        response = requests.post(YOUTUBE_TOKEN_URL, data=req_body)
        token_info = response.json()
        session['youtube_access_token'] = token_info['access_token']
        session['youtube_refresh_token'] = token_info.get('refresh_token')
        session['youtube_expires_at'] = datetime.now().timestamp() + token_info['expires_in']
        session['youtube_expires_in'] = token_info["expires_in"]
        user_id = session.get('user_id')
        youtube_oauth = {
            "scope": "https://www.googleapis.com/auth/youtube",
            "token_type": "Bearer",
            "access_token": session['youtube_access_token'],
            "refresh_token": session['youtube_refresh_token'],
            "expires_at": session['youtube_expires_at'],
            "expires_in": session['youtube_expires_in']
        }
        sess["youtube"] = {"oauth": youtube_oauth}
        
        if user_id:
            store_sess(user_id, session['spotify_username'], sess)

        with open('../client/src/youtube_oauth.json', 'w') as fp:
            json.dump(youtube_oauth, fp)
    return redirect('/authorize-tidal')

@app.route('/authorize-tidal')
def authorize_tidal():
    global sess
    tidal_session = tidalapi.Session()
    login, future = tidal_session.login_oauth()
    import webbrowser as wb
    link = "https://" + login.verification_uri_complete
    wb.open_new_tab(link)
    print("Open the URL to log in", link)
    future.result()
    session['tidal_access_token'] = tidal_session.access_token
    session['tidal_refresh_token'] = tidal_session.refresh_token
    session['tidal_expires_at'] = tidal_session.expiry_time
    sess["tidal"] = {"oauth": {
        "access_token": tidal_session.access_token,
        "refresh_token": tidal_session.refresh_token,
        "expires_at": tidal_session.expiry_time
    }}

    

    return redirect('/soundcloud-authorize')

    


@app.route('/soundcloud-authorize')
def soundcloud_authorize():
    # Generate the authorization URL
    auth_url = (
        f'https://secure.soundcloud.com/authorize?'
        f'client_id={SOUNDCLOUD_CLIENT_ID}&'
        f'redirect_uri={SOUNDCLOUD_REDIRECT_URI}&'
        f'response_type=code&'
        f'code_challenge={SOUNDCLOUD_CODE_CHALLENGE}&'
        f'code_challenge_method=S256&'
        f'state={SOUNDCLOUD_STATE}'
    )
    # Redirect user to the authorization URL
    return redirect(auth_url)

@app.route('/api/users', methods=['GET'])
def get_all_users():
    try:
        users = list(user_collection.find({}, {'_id': 1, 'username': 1, 'email': 1}))
        return jsonify(users)
    except Exception as e:
        print(f"Error fetching users: {e}")
        return jsonify({"error": "Failed to fetch users"}), 500


@app.route('/api/user-info/<user_id>', methods=['GET'])
def get_user_info(user_id):
    try:
        user_data = user_collection.find_one({"_id": ObjectId(user_id)}, {'_id': 0})
        if not user_data:
            return jsonify({"error": "User not found"}), 404
        return jsonify(user_data)
    except Exception as e:
        print(f"Error fetching user info: {e}")
        return jsonify({"error": "Failed to fetch user info"}), 500


@app.route('/callback')
def callback():
    global sess
    # Extract the authorization code from the callback
    code = request.args.get('code')
    state = request.args.get('state')
    
    # Verify the state parameter for CSRF protection
    if state != SOUNDCLOUD_STATE:
        return 'State mismatch. Possible CSRF attack.', 400

    # Exchange the authorization code for an access token
    token_url = 'https://secure.soundcloud.com/oauth/token'
    data = {
        'grant_type': 'authorization_code',
        'client_id': SOUNDCLOUD_CLIENT_ID,
        'client_secret': SOUNDCLOUD_CLIENT_SECRET,
        'redirect_uri': SOUNDCLOUD_REDIRECT_URI,
        'code_verifier': SOUNDCLOUD_CODE_VERIFIER,
        'code': code
    }
    response = requests.post(token_url, data=data)
    token_response = response.json()
    
    # Extract and store tokens
    access_token = token_response.get('access_token')
    refresh_token = token_response.get('refresh_token')
    
    # Store tokens in session for demonstration purposes (in production, store in a secure storage)
    session['access_token'] = access_token
    session['refresh_token'] = refresh_token

    session['soundcloud_access_token'] = access_token
    session['soundcloud_refresh_token'] = refresh_token
    sess["soundcloud"] = {"oauth": {
        "access_token": access_token,
        "refresh_token": refresh_token,
    }}

    print(sess["soundcloud"])

    user_profile = sess.get("spotify", {})
    spotify_username = sess["spotify"]["user_id"] if "user_id" in sess["spotify"] else ""

    user_id = session.get('user_id')
    if user_id and spotify_username:
        print("Storing session data in MongoDB")
        store_sess(user_id, spotify_username, sess)
    else:
        print("User ID or Spotify username missing, cannot store session data")

    return redirect(f'{FRONTEND_HOST}/playlists')

@app.route('/api/sess/<user_id>', methods=['GET'])
def get_user_sess(user_id):
    spotify_username = request.args.get('spotify_username', None)
    if session.get('user_id') != user_id:
        return jsonify({"error": "Unauthorized access"}), 401
    user_sess = fetch_sess_by_user(user_id, spotify_username)
    return jsonify(user_sess)

@app.route('/api/user-id', methods=['GET'])
def get_user_id():
    user_id = session.get('user_id', None)
    if user_id:
        return jsonify({"user_id": user_id})
    return jsonify({"error": "User not logged in"}), 401

@app.route('/tidal-callback')
def tidal_callback():
    if 'error' in request.args:
        return jsonify({"error": request.args['error'], "error_description": request.args['error_description']})
    if 'code' in request.args and 'state' in request.args:
        code = request.args['code']
        state = request.args['state']
        if state != session.pop('state', None):
            return jsonify({"error": "State mismatch"}), 400
        code_verifier = session.pop('code_verifier', None)
        if not code_verifier:
            return jsonify({"error": "Code verifier missing"}), 400
        token_url = "https://auth.tidal.com/v1/oauth2/token"
        req_body = {
            'grant_type': 'authorization_code',
            'client_id': TIDAL_CLIENT_ID,
            'code': code,
            'redirect_uri': TIDAL_REDIRECT_URI,
            'code_verifier': code_verifier
        }
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        response = requests.post(token_url, headers=headers, data=req_body)
        token_info = response.json()
        if 'access_token' in token_info:
            session['tidal_access_token'] = token_info['access_token']
            session['tidal_refresh_token'] = token_info.get('refresh_token')
            session['tidal_expires_at'] = datetime.now().timestamp() + token_info['expires_in']
            user_id = session.get('user_id')
            if user_id:
                sess["tidal"] = {"oauth": {
                    "access_token": token_info['access_token'],
                    "refresh_token": token_info.get('refresh_token'),
                    "expires_at": session['tidal_expires_at']
                }}
                store_sess(user_id, session['spotify_username'], sess)
            return redirect(f'{FRONTEND_HOST}/playlists')
        else:
            return jsonify({"error": "Failed to obtain access token", "response": token_info}), 400
    else:
        return jsonify({"error": "Authorization code or state not found"}), 400

@app.route('/api/fetch-playlists/<user_id>/<spotify_username>', methods=['GET'])
def fetch_playlists_for_user(user_id, spotify_username):
    global sess
    if session.get('user_id') != user_id:
        return jsonify({"error": "Unauthorized access"}), 401
    try:
        # Reset manual playlists
        sess["manual_playlists"] = []

        user_sess = sess_collection.find_one({"user_id": user_id, "spotify_username": spotify_username})
        if not user_sess:
            return jsonify({"error": "User session not found"}), 404
        
        sess = user_sess.get('sess', {})
        spotify_sess = sess.get('spotify', {})

        if not spotify_sess:
            return jsonify({"error": "Spotify session data not found"}), 401

        access_token = spotify_sess.get('access_token')
        expires_at = spotify_sess.get('expires_at')

        if expires_at and datetime.now().timestamp() > expires_at:
            return redirect(f'/refresh-token/{user_id}/{spotify_username}')
        
        headers = {'Authorization': f"Bearer {access_token}"}
        response = requests.get(API_BASE_URL + 'me/playlists', headers=headers)

        if response.status_code == 401:
            return redirect(f'/refresh-token/{user_id}/{spotify_username}')

        if response.status_code != 200:
            return jsonify({"error": "Failed to fetch playlists"}), response.status_code

        playlists = response.json()
        playlist_names = [playlist['name'] for playlist in playlists['items']]
        playlist_uris = [playlist['uri'].split(":")[-1] for playlist in playlists['items']]
        sess["spotify"]["playlists_uri"] = playlist_uris
        sess["spotify"]["playlist_names"] = playlist_names
        return jsonify({"names": playlist_names, "uris": playlist_uris})
    except Exception as e:
        print(f"Error fetching playlists: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/api/remove-user/<user_id>/<spotify_username>', methods=['DELETE'])
def remove_user_session(user_id, spotify_username):
    if session.get('user_id') != user_id:
        return jsonify({"error": "Unauthorized access"}), 401
    try:
        delete_result = sess_collection.delete_many({"user_id": user_id, "spotify_username": spotify_username})
        if delete_result.deleted_count == 0:
            return jsonify({"error": "User session not found"}), 404
        return jsonify({"status": "success", "message": "User session removed"})
    except Exception as e:
        print(f"Error removing user session: {e}")
        return jsonify({"error": "Internal server error"}), 500
    
@app.route('/api/playlists')
def get_playlists():
    global sess
    user_id = session.get('user_id')
    spotify_username = session.get('spotify_username')

    if not user_id or not spotify_username:
        return jsonify({"error": "User ID or Spotify username not found in session"}), 401

    user_sess = sess_collection.find_one({"user_id": user_id, "spotify_username": spotify_username})

    if not user_sess:
        return jsonify({"error": "User session data not found"}), 404

    sess = user_sess.get('sess', {})
    spotify_sess = sess.get('spotify', {})

    if not spotify_sess:
        return jsonify({"error": "Spotify session data not found, reauthorization required"}), 401

    access_token = spotify_sess.get('access_token')
    expires_at = spotify_sess.get('expires_at')

    if expires_at is None:
        return jsonify({"error": "Token expiration time is missing, reauthorization required"}), 401

    if datetime.now().timestamp() > expires_at:
        return redirect('/refresh-token')

    headers = {'Authorization': f"Bearer {access_token}"}
    response = requests.get(API_BASE_URL + 'me/playlists', headers=headers)

    if response.status_code == 401:
        return redirect('/refresh-token')

    if response.status_code != 200:
        return jsonify({"error": "Failed to fetch playlists"}), response.status_code

    playlists = response.json()
    playlist_names = [playlist['name'] for playlist in playlists['items']]
    playlist_uris = [playlist['uri'].split(":")[-1] for playlist in playlists['items']]
    session["playlists"] = {"names": playlist_names, "uris": playlist_uris}
    session["playlists_uri"] = playlist_uris
    sess["spotify"]["playlists_uri"] = playlist_uris
    sess["spotify"]["playlist_names"] = playlist_names
    return jsonify(session["playlists"])

@app.route('/refresh-token')
def refresh_token():
    user_id = session.get('user_id')
    spotify_username = session.get('spotify_username')

    if not user_id or not spotify_username:
        return redirect("/authorize")

    user_sess = sess_collection.find_one({"user_id": user_id, "spotify_username": spotify_username})

    if not user_sess:
        return redirect("/authorize")

    sess = user_sess.get('sess', {})
    spotify_sess = sess.get('spotify', {})

    if 'refresh_token' not in spotify_sess:
        return redirect("/authorize")

    req_body = {
        'grant_type': 'refresh_token',
        'refresh_token': spotify_sess['refresh_token'],
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET
    }
    response = requests.post(TOKEN_URL, data=req_body)
    new_token_info = response.json()

    if 'access_token' not in new_token_info:
        return redirect("/authorize")

    expires_at = datetime.now().timestamp() + new_token_info.get('expires_in', 3600)

    spotify_sess['access_token'] = new_token_info['access_token']
    spotify_sess['expires_at'] = expires_at

    session['access_token'] = spotify_sess['access_token']
    session['expires_at'] = spotify_sess['expires_at']

    if user_id and spotify_username:
        print("Updating refreshed tokens in MongoDB")
        store_sess(user_id, spotify_username, sess)
    else:
        print("Failed to update refreshed tokens, user ID or Spotify username missing")

    return redirect(f'{FRONTEND_HOST}/playlists')

def get_pls():
    global sess
    ans = []
    print("get_pls ", sess["spotify"]["playlists_uri"])
    print(sess["manual_playlists"])
    for uri, name in zip(sess["spotify"]["playlists_uri"], sess["spotify"]["playlist_names"]):
        if sess["manual_playlists"] == [] or name in sess["manual_playlists"]:
            pl_data = get_playlist_data(uri, sess["spotify"]["access_token"])
            if pl_data is not None:
                ans.append(pl_data)
    return ans

@app.route('/api/sync/status', methods=['GET'])
def sync_status():
    global sync_in_progress
    return jsonify({"syncInProgress": sync_in_progress})

@app.route('/<path:path>')
def catch_all(path):
    if path.startswith('api'):
        return jsonify({"error": "Not Found"}), 404
    return send_from_directory(app.static_folder, 'index.html')

@app.errorhandler(404)
def not_found(e):
    return send_from_directory(app.static_folder, 'index.html')

# User registration route
@app.route('/register', methods=['POST'])
def register():
    data = request.json
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"error": "Username and password are required"}), 400

    hashed_password = generate_password_hash(password)
    existing_user = user_collection.find_one({"username": username})
    if existing_user:
        return jsonify({"error": "User already exists"}), 409

    user_collection.insert_one({"username": username, "password": hashed_password})
    return jsonify({"message": "User registered successfully"}), 201

username = ""

# User login route
@app.route('/login', methods=['POST'])
def login():
    global sess, username
    data = request.json
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"error": "Username and password are required"}), 400

    user = user_collection.find_one({"username": username})
    if not user or not check_password_hash(user["password"], password):
        return jsonify({"error": "Invalid credentials"}), 401

    session['user_id'] = str(user["_id"])
    session['username'] = username
    sess['username'] = username
    return jsonify({"message": "Logged in successfully"}), 200

# User logout route
@app.route('/logout', methods=['POST'])
def logout():
    global sync_in_progress, sync_progress_youtube, sync_progress_tidal, sync_total_youtube, playlists, sync_total_tidal, sync_total_soundcloud, sync_progress_soundcloud, last_synced_index, sess
    session.pop('user_id', None)
    session.pop('username', None)
    session.pop('access_token', None)
    session.pop('refresh_token', None)
    session.pop('expires_at', None)
    session.pop('spotify_username', None)
    session.pop('youtube_access_token', None)
    session.pop('youtube_refresh_token', None)
    session.pop('youtube_expires_at', None)
    session.pop('tidal_access_token', None)
    session.pop('tidal_refresh_token', None)
    session.pop('tidal_expires_at', None)
    session.pop('soundcloud_access_token', None)
    session.pop('soundcloud_refresh_token', None)
    
    # Reset any global variables
    sync_in_progress = False
    sync_progress_youtube = 0
    sync_progress_tidal = 0
    sync_progress_soundcloud = 0
    sync_total_youtube = 0
    sync_total_soundcloud = 0
    playlists = []
    sync_total_tidal = 0
    last_synced_index = 0
    sess = {"spotify": dict(), "tidal": dict(), "soundcloud":dict(), "manual_playlists": []}

    return jsonify({"message": "Logged out successfully"}), 200

if __name__ == '__main__':
    app.run(debug=True)