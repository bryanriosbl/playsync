import requests
import getpass

def register_user(api_url):
   
    
    user_data = {
        "username": "juan",
        "password": "1234",
        "is_admin": True
    }
    
    response = requests.post(f"{api_url}/register", json=user_data)

    if response.status_code == 201:
        print("User registered successfully")
    else:
        print(f"Failed to register user: {response.json()}")

if __name__ == "__main__":
    api_url = "http://127.0.0.1:5000"  # Replace with your actual API URL
    register_user(api_url)