import spotipy
from spotipy.oauth2 import SpotifyOAuth
from ytmusicapi import YTMusic
import requests
from PIL import Image
from io import BytesIO
import base64
import tidalapi
from time import sleep
import json
import io







# Fetch playlist details
playlist_id = "2y4Yco7ZZverIcHKC6cfey"

def get_playlist_names(data):
    """
    Extracts playlist names from the given data.
    
    Parameters:
        data (dict): A dictionary containing playlist information.
        
    Returns:
        list: A list of playlist names.
    """
    playlist_names = [playlist['name'] for playlist in data['items']]
    return playlist_names

def get_playlist_uris(data):
    """
    Extracts playlist URI codes from the given data.
    
    Parameters:
        data (dict): A dictionary containing playlist information.
        
    Returns:
        list: A list of playlist URI codes.
    """
    playlist_uris = [playlist['uri'].split(":")[-1] for playlist in data['items']]
    return playlist_uris

def get_pl_details(pl_id):
    # Set up the authentication
    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
        client_id="fbf1afe870c14dc1822779c3392a70ae",
        client_secret="e88eb639ce504530866228344f908038",
        redirect_uri="http://localhost:8080",
        scope="playlist-read-private"
    ))
    playlist = sp.playlist(playlist_id)

    # Extract playlist details
    playlist_name = playlist['name']
    playlist_description = playlist['description']
    playlist_owner = playlist['owner']['display_name']
    cover_image_url = playlist['images'][0]['url'] if playlist['images'] else None

    # Fetch tracks
    tracks = sp.playlist_tracks(playlist_id)
    track_details = []
    for item in tracks['items']:
        track = item['track']
        track_name = track['name']
        artists = ', '.join([artist['name'] for artist in track['artists']])
        track_details.append(f"{track_name} by {artists}")


    return {"name": playlist_name, "description":playlist_description, "visibility":"public", "owner":playlist_owner, "cover_image_url":cover_image_url, "tracks":track_details}




def get_image_data(url):
    response = requests.get(url)
    return response.content



def encode_image_to_base64(image_content):
    image = Image.open(BytesIO(image_content))
    buffered = BytesIO()
    image.save(buffered, format="JPEG")
    return base64.b64encode(buffered.getvalue()).decode('utf-8')



def search_song(song_name, artist_name):
    ytmusic = YTMusic()
    search_results = ytmusic.search(f"{song_name} {artist_name}", filter="songs")
    if search_results:
        # Return the videoId of the first result
        return search_results[0]['videoId']
    return None

def get_existing_playlist_id(ytmusic, playlist_name):
    playlists = ytmusic.get_library_playlists()
    for playlist in playlists:
        if playlist['title'].lower() == playlist_name.lower():
            return playlist['playlistId']
    return None


def download_image(image_url):
    response = requests.get(image_url, stream=True)
    if response.status_code == 200:
        return response.content
    else:
        raise Exception(f"Error downloading image: {response.status_code} - {response.text}")

def create_or_update_soundcloud_playlist(playlist_data, auth_tokens):
    base_url = "https://api.soundcloud.com"
    headers = {
        "Authorization": f"OAuth {auth_tokens['access_token']}"
    }
    
    # Step 1: Retrieve the current user's playlists
    me_url = f"{base_url}/me/playlists"
    me_response = requests.get(me_url, headers=headers)
    
    if me_response.status_code != 200:
        raise Exception(f"Error retrieving user's playlists: {me_response.text}")
    
    playlists = me_response.json()
    
    playlist_id = None
    for playlist in playlists:
        if playlist['title'].lower() == playlist_data['name'].lower():
            playlist_id = playlist['id']
            break
    
    def get_track_id(track_title):
        track_search_url = f"{base_url}/tracks?q={track_title}&limit=1"
        track_response = requests.get(track_search_url, headers=headers)
        if track_response.status_code != 200:
            print(f"Error searching track '{track_title}': {track_response.text}")
            return None
        tracks = track_response.json()
        if not tracks:
            print(f"Track '{track_title}' not found")
            return None
        return tracks[0]['id']
    
    track_ids = []
    for track in playlist_data['tracks']:
        track_id = get_track_id(track)
        if track_id:
            track_ids.append(track_id)
    
    # Download the cover image
    cover_image_bytes = download_image(playlist_data['cover_image_url'])
    
    # Prepare the multipart form data
    multipart_data = {
        'playlist[title]': (None, playlist_data['name']),
        'playlist[description]': (None, playlist_data['description']),
        'playlist[sharing]': (None, playlist_data['visibility']),
        'playlist[artwork_data]': ('cover.jpg', cover_image_bytes, 'image/jpeg')
    }

    # Add tracks to the multipart data
    files = []
    for track_id in track_ids:
        files.append(('playlist[tracks][][id]', (None, str(track_id))))

    files.extend(multipart_data.items())

    # Step 2 & 3: Create or update the playlist
    if not playlist_id:
        # Playlist does not exist, create it
        create_playlist_url = f"{base_url}/playlists"
        create_response = requests.post(create_playlist_url, headers=headers, files=files)
        if create_response.status_code != 201:
            raise Exception(f"Error creating playlist: {create_response.text}")
        print("Playlist created successfully")
    else:
        # Playlist exists, update it
        update_playlist_url = f"{base_url}/playlists/{playlist_id}"
        update_response = requests.put(update_playlist_url, headers=headers, files=files)
        if update_response.status_code != 200:
            if update_response.status_code == 403:
                print("Insufficient permissions to update the playlist or the playlist does not belong to the authenticated user.")
            elif update_response.status_code == 404:
                print("Playlist not found.")
            else:
                print(f"Unexpected error updating playlist: {update_response.text}")
            
            raise Exception(f"Error updating playlist: {update_response.text}")
        print("Playlist updated successfully")

def create_or_update_youtube_playlist(playlist_json, oauth_path):
    print(">> YTMUSIC")
    ytmusic = YTMusic(oauth_path)
    playlist_name = playlist_json['name']
    playlist_description = playlist_json['description']
    visibility = 'PUBLIC' if playlist_json.get('visibility', 'public').lower() == 'public' else 'PRIVATE'
    
    # Check if the playlist already exists
    playlist_id = get_existing_playlist_id(ytmusic, playlist_name)
    
    if playlist_id:
        print(f">> Updating existing playlist: {playlist_name}")
    else:
        print(f">> Creating new playlist: {playlist_name}")
        playlist_id = ytmusic.create_playlist(playlist_name, playlist_description, privacy_status=visibility)
    
    # Add songs to the playlist
    track_ids = []
    for track in playlist_json['tracks']:
        song_name, artist_name = track.split(' by ')
        search_results = ytmusic.search(f"{song_name} {artist_name}", filter='songs')
        
        if search_results:
            def priority(result):
                title = result['title'].lower()
                if 'official video' in title or 'vídeo oficial' in title:
                    return 1
                elif 'lyric video' in title or 'official lyric video' in title or 'official video lyric' in title:
                    return 2
                elif 'visualizer' in title:
                    return 3
                else:
                    return 4
            
            # Sort search results by priority
            search_results.sort(key=priority)
            video_id = search_results[0]['videoId']
            track_ids.append(video_id)
    
    if track_ids:
        ytmusic.add_playlist_items(playlist_id, track_ids)
        print(f">> Playlist '{playlist_name}' updated successfully with {len(track_ids)} tracks.")
    else:
        print("No tracks were added to the playlist.")
    
    return playlist_id




# Define your function to search for a track
def search_track(session, track_name):
    try:
        search_results = session.search('show must go on')
        #print(search_results)
        tracks = search_results["tracks"]
        if tracks:
            return tracks[0].id
        else:
            print(f">> Track '{track_name}' not found on TIDAL.")
            return None
    except ValueError as e:
        print(f">> Error searching for track '{track_name}': {e}")
        return None




def create_or_update_tidal_playlist(playlist_data, header):
    # Login session
    print(">> TIDAL:")
    session = tidalapi.Session()
    session.load_oauth_session(
        "Bearer", 
        header["access_token"], 
        header["refresh_token"], 
        header["expires_at"]
    )
    
    if not session.check_login():
        print("Login failed.")
        return
    
    print("Login successful.")
    
    user = session.user
    playlists = user.playlists()
    
    # Check if the playlist already exists
    playlist = None
    for pl in playlists:
        if pl.name == playlist_data['name']:
            playlist = pl
            break
    
    if playlist:
        print(f">> Updating existing playlist: {playlist_data['name']}")
        playlist.description = playlist_data['description']
    else:
        print(f">> Creating new playlist: {playlist_data['name']}")
        playlist = user.create_playlist(
            playlist_data['name'], 
            playlist_data['description']
        )
    playlist.is_public = (playlist_data['visibility'] == 'public')

    
    # Update cover image
    if playlist_data.get('cover_image_url'):
        playlist.cover_url = playlist_data['cover_image_url']
    
    # Search and add tracks to the playlist
    track_ids = []
    for track in playlist_data['tracks']:
        track_id = search_track(session, track)
        if track_id:
            track_ids.append(track_id)
    
    if track_ids:
        playlist.add(track_ids)
        print(f">> Playlist '{playlist_data['name']}' updated with {len(track_ids)} tracks.")
    else:
        print("No tracks were added to the playlist.")





# Example usage
playlist_data = {
    'name': 'Groove-ando alto',
    'description': 'Música para caminar bailandito por la calle. @rengi.enmarte',
    'owner': 'Juan Rengifo',
    'cover_image_url': 'https://image-cdn-ak.spotifycdn.com/image/ab67706c0000da840ca24d5c3aca698410a08503',
    'visibility': 'public',  # or 'private'
    'tracks': [
        '¿Y si te vas tú primero? by Disco en Marte',
        'La Vida Está Rara by Duplat, Lika Nova',
        'Buscándote by Xavier Martinex',
        'Sigo Esperando by Disco en Marte',
        'tu liga del pelo by babas tutsipop',
        # Add other tracks as needed
    ]
}

def update(playlist_data, tidal_headers):
    create_or_update_youtube_playlist(playlist_data, "../client/src/oauth.json")
    create_or_update_tidal_playlist(playlist_data, tidal_headers)
    
#https://open.spotify.com/playlist/5LkuQ6ApkqtchiyZzBmh9u?si=35974d4c42d54061

def main():
    playlist_id = "5LkuQ6ApkqtchiyZzBmh9u"
    u = dict()
    first = 1

    while 1:
        playlist_data = get_pl_details(playlist_id)
        if u != playlist_data:
            if not first: print(">> Updating...")
            first=0
            update(playlist_data)
            u = playlist_data
        sleep(5)
        print(">> idle...")

#main()
        
"""
import requests

CLIENT_ID = 'VgctLM9VC8rTv60ZYPcbml5sdpOnUwpC'
CLIENT_SECRET = 'GuDFSbgqgJEPZWd3h61Tp8mlG909HCQj'
REDIRECT_URI = 'http://localhost:5000/callback'
CODE_VERIFIER = '3604440048217d04da94c51f24d7d6e331940ca96246abc454f57dfc'  # Store this securely and generate accordingly
CODE_CHALLENGE = 'b1ffoyo3FDGmnq6yp5xhsmJ-Y43eWhAx7kUSZ5XFWGI'

def get_tokens():
    # Step 1: Redirect user to SoundCloud’s authorization URL
    auth_url = (
        f"https://secure.soundcloud.com/authorize?response_type=code&client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}&code_challenge={CODE_CHALLENGE}&code_challenge_method=S256"
    )
    print(f"Please go to this URL and authorize the app: {auth_url}")

    # Step 2: User manually retrieves code from redirect_uri
    authorization_code = input("Enter the authorization code from the URL: ").strip()

    # Step 3: Exchange authorization code for access and refresh tokens
    token_url = "https://secure.soundcloud.com/oauth/token"

    payload = {
        'grant_type': 'authorization_code',
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'redirect_uri': REDIRECT_URI,
        'code_verifier': CODE_VERIFIER,
        'code': authorization_code
    }

    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': 'application/json; charset=utf-8'
    }

    response = requests.post(token_url, data=payload, headers=headers)

    if response.status_code != 200:
        print("Failed to obtain tokens.")
        print(response.json())  # Print the error message for debugging purposes
        return None

    tokens = response.json()
    access_token = tokens.get('access_token')
    refresh_token = tokens.get('refresh_token')

    return {
        'access_token': access_token,
        'refresh_token': refresh_token
    }

# Call the function to get the tokens
tokens = get_tokens()
if tokens:
    print(f"Access Token: {tokens['access_token']}")
    print(f"Refresh Token: {tokens['refresh_token']}")"""