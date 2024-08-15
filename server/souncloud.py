from flask import Flask, request, redirect, session
import requests
import base64
import os

app = Flask(__name__)
app.secret_key = os.urandom(24)  # Securely generate a random secret key

# Configuration
CLIENT_ID = 'VgctLM9VC8rTv60ZYPcbml5sdpOnUwpC'
CLIENT_SECRET = 'GuDFSbgqgJEPZWd3h61Tp8mlG909HCQj'
REDIRECT_URI = 'http://localhost:5000/callback'
CODE_VERIFIER = '3604440048217d04da94c51f24d7d6e331940ca96246abc454f57dfc'  # Securely stored and generated
CODE_CHALLENGE = 'b1ffoyo3FDGmnq6yp5xhsmJ-Y43eWhAx7kUSZ5XFWGI'
STATE = os.urandom(24).hex()  # Securely generate a random state

@app.route('/')
def home():
    # Generate the authorization URL
    auth_url = (
        f'https://secure.soundcloud.com/authorize?'
        f'client_id={CLIENT_ID}&'
        f'redirect_uri={REDIRECT_URI}&'
        f'response_type=code&'
        f'code_challenge={CODE_CHALLENGE}&'
        f'code_challenge_method=S256&'
        f'state={STATE}'
    )
    # Redirect user to the authorization URL
    return redirect(auth_url)

@app.route('/callback')
def callback():
    # Extract the authorization code from the callback
    code = request.args.get('code')
    state = request.args.get('state')
    
    # Verify the state parameter for CSRF protection
    if state != STATE:
        return 'State mismatch. Possible CSRF attack.', 400

    # Exchange the authorization code for an access token
    token_url = 'https://secure.soundcloud.com/oauth/token'
    data = {
        'grant_type': 'authorization_code',
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'redirect_uri': REDIRECT_URI,
        'code_verifier': CODE_VERIFIER,
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
    
    return f'Access Token: {access_token}, Refresh Token: {refresh_token}'

@app.route('/me')
def me():
    # Use the access token to make an authenticated request
    access_token = session.get('access_token')
    if not access_token:
        return 'User not authenticated.', 401
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'accept': 'application/json; charset=utf-8'
    }
    response = requests.get('https://api.soundcloud.com/me', headers=headers)
    return response.json()

if __name__ == '__main__':
    app.run(debug=True)
