import io
import threading
import tkinter as tk
import urllib.request
from tkinter import font

import pystray
from colorthief import ColorThief
from PIL import Image, ImageDraw, ImageTk

class Overlay:
    def __init__(self, fetchTrack):
        # initialises tkinter overlay window, sets variables to be used for style and layout
        # creates fetchTrack function variable to be used for fetching track info in update loop

        self.fetchTrack = fetchTrack
        self.root = tk.Tk()

        # size variables - these make the overlay scale with resolution
        self.screenWidth = self.root.winfo_screenwidth()
        self.screenHeight = self.root.winfo_screenheight()
        self.overlayWidth = int(self.screenWidth * 0.14)
        self.overlayHeight = int(self.screenHeight * 0.05)
        self.overlayX = int(self.screenWidth * 1.0 - self.overlayWidth - 20)
        self.overlayY = int(self.screenHeight * 0.02)
        self.artSize = int(self.overlayHeight * 0.90)
        self.fontSizeName = int(self.overlayHeight * 0.16)
        self.fontSizeArtist = int(self.overlayHeight * 0.15)

        # main overlay window
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", 0.8)
        self.root.geometry(
            f"{self.overlayWidth}x{self.overlayHeight}+{self.overlayX}+{self.overlayY}"
        )
        self.root.configure(bg="black")
        self.hideTimer = None
        self.root.bind("<Enter>", self.onMouseEnter)
        self.accentBar = tk.Frame(self.root, bg="gray", width=5)
        self.accentBar.pack(side="left", fill="y")

        # album art attributes
        self.artLabel = tk.Label(self.root, bg="black")
        self.artLabel.pack(side="left", padx=int(self.overlayWidth * 0.02))

        # text area
        self.textFrame = tk.Frame(self.root, bg="black")
        self.textFrame.pack(side="left", fill="both", expand=True, padx=(0, 15))

        # song name attributes
        self.nameLabel = tk.Label(
            self.textFrame,
            text="Nothing playing",
            fg="white",
            bg="black",
            font=("Cambria", self.fontSizeName, "bold"),
            anchor="w",
        )
        self.nameLabel.pack(fill="x", expand=True)

        # artist name attributes
        self.artistLabel = tk.Label(
            self.textFrame,
            text="",
            fg="gray",
            bg="black",
            font=("Cambria", self.fontSizeArtist),
            anchor="w",
        )
        self.artistLabel.pack(fill="x", expand=True)

        if self.fetchTrack() is None:
            self.nameLabel.config(text="Nothing playing.")
            self.artistLabel.config(text="")
            self.artLabel.config(image="")
            self.accentBar.configure(bg="red")

    def fetchArt(self, url):
        # fetches album art from spotify, resizes it to fit the overlay
        # and returns both the image and raw data for color extraction (via colorthief)
        with urllib.request.urlopen(url) as response:
            data = response.read()
        img = Image.open(io.BytesIO(data))
        img = img.resize((self.artSize, self.artSize))
        return ImageTk.PhotoImage(img), data

    def truncateText(self, text, maxWidth):
        # truncates text to fit the overlay, replaces end with elipsis if too long
        f = font.Font(font=self.nameLabel.cget("font"))
        if f.measure(text) <= maxWidth:
            return text
        while f.measure(text + "...") > maxWidth:
            text = text[:-1]
        return text + "..."

    def onMouseEnter(self, event):
        # when mouse enters the overlay, cancels any hide timers and resets opacity to full, then starts polling mouse position
        if self.hideTimer:
            self.root.after_cancel(self.hideTimer)
            self.hideTimer = None
        self.root.attributes("-alpha", 0.0)
        self.pollMouse()

    def pollMouse(self):
        # polls mouse position every 100ms, starts fade out if mouse leaves the overlay
        x, y = self.root.winfo_pointerxy()
        winX = self.root.winfo_rootx()
        winY = self.root.winfo_rooty()
        winW = self.root.winfo_width()
        winH = self.root.winfo_height()

        if not (winX <= x <= winX + winW and winY <= y <= winY + winH):
            self.hideTimer = self.root.after(1000, self.fadeIn)
        else:
            self.root.after(100, self.pollMouse)

    def fadeIn(self, alpha=0.0):
        # function to fade in overlay once mouse leaves
        if alpha < 0.8:
            alpha = round(alpha + 0.05, 2)
            self.root.attributes("-alpha", alpha)
            self.hideTimer = self.root.after(20, lambda: self.fadeIn(alpha))
        else:
            self.hideTimer = None

    def createTrayIcon(self):
        # creates a windows taskbar icon
        img = Image.new("RGB", (64, 64), color="#1DB954")
        draw = ImageDraw.Draw(img)
        draw.ellipse([8, 8, 56, 56], fill="white")
        return img

    def getColors(self, imageData):
        # takes image data from album art, sets variables for dominant and accent colors to be used for overlay background and text
        ct = ColorThief(io.BytesIO(imageData))
        dominant = ct.get_color(quality=1)
        palette = ct.get_palette(color_count=2)
        accent = palette[1]
        return dominant, accent

    def getTextColor(self, bgColor):
        # uses contrast formula to determine whether text should be black or white based on background color for readability
        r, g, b = bgColor
        luminance = 0.299 * r + 0.587 * g + 0.114 * b
        return "#000000" if luminance > 128 else "#ffffff"

    def update(self):
        # updates the overlay with current track info, album art and colors, runs in a separate thread to avoid blocking the UI
        thread = threading.Thread(target=self.fetchAndUpdate, daemon=True)
        thread.start()
        self.root.after(1000, self.update)

    def fetchAndUpdate(self):
        # fetches track info, album art and colors, then applies updates to the UI on the main thread
        track = self.fetchTrack()
        if track:
            if track["name"] == self.nameLabel.cget("text") and track["artist"] == self.artistLabel.cget("text"):
                return  # no update needed if track info hasn't changed
            self.lastTrackName, self.lastTrackArtist = track["name"], track["artist"]
            art, imageData = self.fetchArt(track["art"])
            dominant, accent = self.getColors(imageData)
            bg = "#%02x%02x%02x" % dominant
            textColor = self.getTextColor(dominant)

            # update UI back on the main thread
            self.root.after(0, lambda: self.applyUpdate(track, art, bg, textColor))
        else:
            self.root.after(0, self.applyNoTrack)

    def applyUpdate(self, track, art, bg, textColor):
        # applies updates to the UI elements, truncates text if necessary to fit the overlay
        maxWidth = self.nameLabel.winfo_width()
        if maxWidth <= 1:
            maxWidth = self.overlayWidth - self.artSize - 40
        self.nameLabel.config(text=self.truncateText(track["name"], maxWidth))
        self.artistLabel.config(text=track["artist"])
        self.artLabel.config(image=art)
        self.artLabel.image = art  # type: ignore
        self.accentBar.configure(bg=bg)

    def applyNoTrack(self):
        # resets overlay to a neutral state when Spotify reports nothing is playing
        self.nameLabel.config(text="Nothing playing")
        self.artistLabel.config(text="")
        self.artLabel.config(image=None)
        self.artLabel.image = None  # type: ignore
        self.root.configure(bg="black")
        self.artLabel.configure(bg="black")
        self.textFrame.configure(bg="black")
        self.nameLabel.configure(bg="black", fg="white")
        self.artistLabel.configure(bg="black", fg="gray")

    def run(self):
        # starts the overlay and begins update loop
        self.update()

        # create system tray icon with quit option
        menu = pystray.Menu(pystray.MenuItem("Quit", self.quit))
        self.trayIcon = pystray.Icon(
            "anklebiter",
            self.createTrayIcon(),
            "Anklebiter Overlay",
            menu,
        )

        trayThread = threading.Thread(target=self.trayIcon.run, daemon=True)
        trayThread.start()

        self.root.mainloop()

    def quit(self, icon=None, item=None):
        # ends process when quit option is selected from tray icon
        self.trayIcon.stop()
        self.root.destroy()
