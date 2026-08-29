import os

import spotipy
from dotenv import load_dotenv
from spotipy.oauth2 import SpotifyOAuth

load_dotenv()

CLIENT_ID = "3d6586d75b104859b0e1228e0b2c810f"

sp = spotipy.Spotify(
    auth_manager=SpotifyOAuth(
        client_id=CLIENT_ID,
        client_secret=os.getenv("SPOTIPY_CLIENT_SECRET"),
        redirect_uri="http://127.0.0.1:8888/callback",
        scope="user-read-currently-playing",
    )
)

def getCurrentTrack():
    track = sp.current_user_playing_track()

    if track:
        name = track["item"]["name"]
        artist = track["item"]["artists"][0]["name"]
        art = track["item"]["album"]["images"][0]["url"]
        return {
            "name": name,
            "artist": artist,
            "art": art,
        }
    else:
        print("Nothing playing.")
        return None
