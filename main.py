from overlay import Overlay
from spotify import getCurrentTrack

app = Overlay(fetchTrack=getCurrentTrack)
app.run()
