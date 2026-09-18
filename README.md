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

### Hide the settings panel

Select **Hide settings** to give the video more screen space. Select **Show settings** to restore the panel.

### Check the weather manually

Select **Check weather now** to retrieve and display the current Bengaluru weather without waiting for the main video to finish.

### Return from the advertisement

After a post-credit advertisement appears, select **Return to main video** when that button is displayed. Restarting or playing the main video also closes the post-credit layer.

## Weather-to-Advertisement Mapping

The default mappings are:

| Weather category | Suggested product | Default YouTube video |
|---|---|---|
| Sunny / bright | Sunscreen | `r1ir5gcue4M` |
| Rain or drizzle | Umbrella | `l0TbsIz3PJI` |
| Thunderstorm | Raincoat | `A25J5xT74sY` |
| Partly cloudy | Sunglasses | `nrOX6ackB14` |
| Overcast | Moisturizer | `h0n8ThYTulY` |
| Fog | Headlights | `jlkS-tPqFPU` |
| Very hot, at least 34°C and dry | Air conditioner | `uCphB_FzX7c` |
| Cool, 18°C or below | Hot coffee | `Y-jNMHruAts` |

You can replace any mapping in the **YouTube ad mapping** section. Paste either a full YouTube URL or an 11-character video ID, then select **Save YouTube mappings**.

Custom mappings are stored in the browser's `localStorage`. They apply only to that browser profile and computer. Clearing browser site data removes them.

## Weather Classification Rules

The application requests current conditions for Bengaluru at approximately:

```text
Latitude: 12.9716
Longitude: 77.5946
Timezone: Asia/Kolkata
```

Classification is applied in this priority order:

1. **Thunderstorm** for Open-Meteo weather codes 95, 96, or 99.
2. **Rain or drizzle** for rain/drizzle codes or measured precipitation, rain, or showers above zero.
3. **Fog** for weather codes 45 or 48.
4. **Very hot** when the temperature is at least 34°C and conditions are dry.
5. **Cool** when the temperature is 18°C or below.
6. **Partly cloudy** for mainly clear or partly cloudy codes 1 and 2.
7. **Overcast** for code 3.
8. **Sunny / bright** for remaining clear conditions.

Hazardous precipitation is checked before temperature, so a hot thunderstorm is classified as a thunderstorm rather than very hot.

## Customization

### Change the default YouTube advertisements

Edit `DEFAULT_YOUTUBE_ADS` near the top of `weather_youtube_player.py`:

```python
DEFAULT_YOUTUBE_ADS = {
    "sunny": "https://www.youtube.com/watch?v=VIDEO_ID",
    "rain": "https://www.youtube.com/watch?v=VIDEO_ID",
    "thunderstorm": "https://www.youtube.com/watch?v=VIDEO_ID",
    "partly_cloudy": "https://www.youtube.com/watch?v=VIDEO_ID",
    "overcast": "https://www.youtube.com/watch?v=VIDEO_ID",
    "fog": "https://www.youtube.com/watch?v=VIDEO_ID",
    "very_hot": "https://www.youtube.com/watch?v=VIDEO_ID",
    "cool": "https://www.youtube.com/watch?v=VIDEO_ID",
}
```

### Change the city

The current implementation is configured specifically for Bengaluru. To use another location, change:

```python
BENGALURU_LATITUDE = 12.9716
BENGALURU_LONGITUDE = 77.5946
```

You may also want to update the interface labels, `WEATHER_META`, the returned place name, and the timezone parameter.

### Change the server port

If port `8765` is unavailable, change:

```python
PORT = 8765
```

to another unused port, for example:

```python
PORT = 8766
```

Then open:

```text
http://127.0.0.1:8766
```

## Troubleshooting

### `OSError: [Errno 98] Address already in use`

Another process is already using port `8765`, often because an earlier copy of the application is still running.

First, check whether the existing application is available at:

```text
http://127.0.0.1:8765
```

Otherwise, stop the old process or change the `PORT` value.

#### Linux

```bash
lsof -i :8765
kill <PID>
```

Or:

```bash
fuser -k 8765/tcp
```

#### macOS

```bash
lsof -i :8765
kill <PID>
```

#### Windows

```bat
netstat -ano | findstr :8765
taskkill /PID <PID> /F
```

Replace `<PID>` with the process ID shown by the first command.

### YouTube says the video is unavailable

The application accepts standard YouTube URLs, short `youtu.be` URLs, Shorts URLs, live URLs, embed URLs, and 11-character video IDs. However, YouTube or the video owner may still block embedded playback.

Common YouTube player errors include:

| Error | Meaning |
|---|---|
| 2 | Invalid YouTube video ID |
| 5 | The video could not be played in the HTML5 player |
| 100 | Video removed, private, unavailable, or not found |
| 101 or 150 | The owner disabled playback on embedded websites |
| 153 | YouTube did not receive acceptable origin or referrer information |

Errors 101 and 150 cannot be bypassed by this application. Choose a video whose owner permits embedding.

A video may also be unavailable because of age restrictions, regional restrictions, account requirements, copyright controls, or YouTube policy.

### The main YouTube video has no standard YouTube controls

This is intentional. The embedded player uses the application's custom controls. Use the Play, Pause, Back, Forward, Restart, and Speed controls below the video.

### A direct video URL does not play

Confirm that:

- The URL points directly to a video file rather than a webpage.
- The file format and codecs are supported by the browser.
- The remote server permits cross-origin browser access.
- The server supports HTTP byte-range requests.

For widest browser compatibility, use an MP4 file encoded with H.264 video and AAC audio.

### A local video does not play

Confirm that:

- The path is absolute and correctly typed.
- The file exists and the Python process has permission to read it.
- The video uses browser-supported codecs.
- A Windows path containing spaces is enclosed in quotes when supplied on the command line.

### Weather cannot be retrieved

Check the internet connection and try again. The weather endpoint depends on Open-Meteo. If the weather request fails when the main video ends, the application displays a weather-unavailable message instead of selecting an advertisement.

### The selected ad does not autoplay

Browsers may block autoplay, especially playback with sound, unless the user has already interacted with the page. Select Play or interact with the page before the main video ends. Browser privacy settings and YouTube restrictions can also affect autoplay.

### Saved mappings disappeared

Mappings are stored in browser `localStorage`. They may disappear if you:

- Clear browser data
- Use private/incognito mode
- Change browsers or browser profiles
- Open the app under a different hostname or port

## Security and Privacy

- The server listens on `127.0.0.1`, so it is accessible only from the same computer by default.
- Local video paths are sent only to the local Python server.
- The application does not upload local video files to an external storage service.
- Weather requests are sent to Open-Meteo.
- YouTube receives requests when YouTube videos or advertisements are loaded.
- Do not change `HOST` to `0.0.0.0` unless you understand the security implications of exposing the server to other devices on the network.

## Technical Overview

The application uses:

- `ThreadingHTTPServer` for the local web server
- HTTP range responses for seeking through local video files
- The YouTube IFrame Player API for the main YouTube video
- A YouTube embed for the post-credit advertisement
- Open-Meteo for current Bengaluru weather
- Browser `localStorage` for customized ad mappings
- Embedded HTML, CSS, and JavaScript served directly by the Python script

### Local routes

| Route | Purpose |
|---|---|
| `/` | Serves the application interface |
| `/config` | Returns the initial video source and default ad mappings |
| `/set-video?path=...` | Selects a local video file |
| `/video` | Streams the selected local video with range support |
| `/weather` | Retrieves and classifies current Bengaluru weather |

## Notes and Limitations

- This is a local development/demo application and does not include authentication.
- Only one local video path is active in the server at a time.
- Browser support determines which direct video formats and codecs can play.
- YouTube embedding depends on each video's settings and YouTube policies.
- Weather classification is based on current conditions, not the full-day forecast.
- Internet access is required at the moment the post-credit ad is selected.

## License

No license is included by default. Add a `LICENSE` file before distributing the project, and ensure you have permission to use and embed all videos and advertisements.
