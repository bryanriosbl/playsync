from plyer import notification
import tidalapi


session = tidalapi.Session()

login, future = session.login_oauth()

print("Open the URL to log in", login.verification_uri_complete)

future.result()
print(session.check_login())