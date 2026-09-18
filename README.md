# Bengaluru Weather Post-Credit Video Player

A self-contained Python web application that plays a main video and, when the video ends, checks the **current weather in Bengaluru** and automatically plays a matching **YouTube post-credit advertisement**.

The application supports:

- YouTube videos
- Direct browser-playable video URLs, such as MP4 and WebM
- Local video files specified by full path
- Play, pause, restart, rewind, fast-forward, and playback-speed controls
- A collapsible settings panel
- Live Bengaluru weather from Open-Meteo
- Configurable weather-to-YouTube-ad mappings saved in the browser

## How It Works

1. Start the Python application.
2. Enter a YouTube URL, direct video URL, or local video path.
3. Play the main video.
4. When the main video finishes, the application retrieves Bengaluru's current weather.
5. The weather is classified into one of eight categories.
6. The corresponding YouTube advertisement is shown as the post-credit video.

## Requirements

- **Python 3.9 or newer** is recommended.
- A modern web browser such as Chrome, Edge, Firefox, or Safari.
- Internet access for:
  - Bengaluru weather retrieval
  - YouTube playback
  - Direct online video URLs

The application uses only Python standard-library modules, so no `pip install` command is required.

## Project File

```text
weather_youtube_player.py
```

The Python file contains the HTTP server, HTML interface, CSS, JavaScript, weather classification, local video streaming, and default YouTube mappings.

## Run the Application

Open a terminal in the folder containing the script and run:

```bash
python weather_youtube_player.py
```

On systems where Python 3 uses a separate command:

```bash
python3 weather_youtube_player.py
```

The application starts at:

```text
http://127.0.0.1:8765
```

It should open automatically in the default browser. Press **Ctrl+C** in the terminal to stop the server.

## Start with a Video Source

You can optionally pass the initial video source as a command-line argument.

### Local file on Windows

```bash
python weather_youtube_player.py "D:\Brahma_AI\movie.mp4"
```

### Local file on Linux or macOS

```bash
python3 weather_youtube_player.py "/home/user/videos/movie.mp4"
```

### YouTube URL

```bash
python weather_youtube_player.py "https://www.youtube.com/watch?v=VIDEO_ID"
```

Short YouTube URLs are also accepted:

```bash
python weather_youtube_player.py "https://youtu.be/VIDEO_ID"
```

### Direct video URL

```bash
python weather_youtube_player.py "https://example.com/videos/movie.mp4"
```

A direct URL must point to a format the browser can play. The remote server must also permit browser access and support video byte-range requests.

## Using the Interface

### Load the main video

Enter one of the following in **Main video source** and select **Load**:

- A full YouTube URL
- A YouTube video ID
- A direct MP4 or WebM URL
- A full local file path

Examples:

```text
https://youtu.be/TUVcZfQe-Kw
D:\Brahma_AI\movie.mp4
https://example.com/movie.mp4
```

### Playback controls

| Control | Action |
|---|---|
| Play | Starts or resumes the main video |
| Pause | Pauses playback |
| Back 10s | Rewinds by 10 seconds |
| Forward 10s | Fast-forwards by 10 seconds |
| Restart | Returns to the beginning and plays the video |
| Speed | Selects 0.5×, 1×, 1.25×, 1.5×, or 2× playback |

