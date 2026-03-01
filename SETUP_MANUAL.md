# Music Assistant Alexa Skill - Comprehensive Manual Setup Guide

This guide provides complete instructions to manually configure the Music Assistant Alexa skill and the Docker container, including security hardening and playback synchronization.

## 1. Prerequisites (Endpoints)

To communicate with Amazon Alexa, you need two publicly accessible HTTPS endpoints (e.g., via Cloudflare Tunnels):

*   **Skill Endpoint**: Points to the Skill container's port **5150**. (Example: `https://alexa-skill.your-domain.com`)
*   **Streaming Endpoint**: Points to the Music Assistant stream port **8097**. (Example: `https://ma-stream.your-domain.com`)
    *   *Note: This is required for Alexa to download and play the audio files.*

## 2. Docker & Secrets Configuration

### Step A: Setup Secrets
For security, credentials are managed via Docker secrets.
1.  Create a `secrets` directory next to your `docker-compose.yml`.
2.  Create `secrets/app_username.txt` and write your desired username inside.
3.  Create `secrets/app_password.txt` and write your desired password inside.

### Step B: docker-compose.yml
Use the following template, replacing the example hostnames and local IPs with your own.

```yaml
services:
  music-assistant-skill:
    image: ghcr.io/alams154/music-assistant-skill:latest
    environment:
      - SKILL_HOSTNAME=alexa-skill.your-domain.com
      - STREAM_HOSTNAME=ma-stream.your-domain.com
      - MA_SERVER_URL=http://192.168.x.x:8095      # Local IP of your Music Assistant server
      - APP_USERNAME=/run/secrets/APP_USERNAME
      - APP_PASSWORD=/run/secrets/APP_PASSWORD
      - PORT=5150
      - TZ=Europe/Rome
      - LOCALE=it-IT                                # Language for Alexa (e.g., en-US, it-IT)
    secrets:
      - APP_USERNAME
      - APP_PASSWORD
    ports:
      - 5150:5150
    volumes:
      - ./ask_data:/root/.ask                       # Persists Alexa credentials
    restart: unless-stopped

secrets:
  APP_USERNAME:
    file: ./secrets/app_username.txt
  APP_PASSWORD:
    file: ./secrets/app_password.txt
```

### Step C: Start the Service
Run the following command in the directory containing your `docker-compose.yml`:

```sh
docker compose up -d
```

## 3. Alexa Developer Console Setup

Follow these steps in the [Alexa Developer Console](https://developer.amazon.com/alexa/console/ask):

1.  **Create Skill**: Click **Create Skill**.
    *   **Name**: "Music Assistant"
    *   **Experience**: "Music & Audio"
    *   **Model**: "Custom"
    *   **Hosting**: "Provision your own"
    *   ![Step 1 - Create Skill](assets/screenshots/step7-1.png)
    *   ![Step 2 - Model selection](assets/screenshots/step7-2-1.png)
    *   ![Step 3 - Hosting selection](assets/screenshots/step7-2-2.png)
2.  **Template**: Choose **Start from Scratch**.
    *   ![Step 4 - Template selection](assets/screenshots/step7-3.png)
3.  **Invocation**: Set the invocation name to "music assistant".
    *   ![Step 5 - Invocation](assets/screenshots/step7-4.png)
4.  **Endpoint**:
    *   Select **HTTPS**.
    *   **Default Region**: Enter your Skill Endpoint (e.g., `https://alexa-skill.your-domain.com`).
    *   **Certificate**: Select *"My endpoint is a sub-domain of a domain that has a wildcard certificate..."*.
    *   ![Step 6 - Endpoint](assets/screenshots/step7-5.png)
5.  **Intents**: Add a custom intent `PlayAudio` with utterances like "play", "play music", "start".
    *   ![Step 7 - Intents](assets/screenshots/step7-6.png)
6.  **Interfaces**: 
    *   Enable **Audio Player**.
    *   Enable **Alexa Presentation Language**.
    *   ![Step 8 - Interfaces](assets/screenshots/step7-7.png)
7.  **Build**: Click **Build Skill**.
    *   ![Step 9 - Build](assets/screenshots/step7-8.png)
8.  **Activation**: Go to the **Test** tab and change "Off" to **Development**.
    *   ![Step 10 - Activation](assets/screenshots/step7-9.png)

## 4. Final Authorization & Monitoring

### Authentication (ASK Setup)
Your server must be authorized to communicate with Amazon.
1.  Navigate to `https://alexa-skill.your-domain.com/setup`
2.  Follow the on-screen instructions to bridge your backend with the Amazon ASK CLI.

### Status Page
Monitor your skill health and latest pushed metadata at:
`https://alexa-skill.your-domain.com/status`

---

## Technical Features

### Playback Control (Next/Prev/Play/Pause)
*   **Skill to MA**: Alexa relays media commands to your local MA server via `MA_SERVER_URL`.
*   **MA to Skill (Stop Sync)**: If you stop music in MA, Alexa will stop as well during the next metadata refresh.
*   **Configuration**: Include your player ID in the MA automation:
    ```json
    { "streamUrl": "...", "title": "...", "playerId": "your_id" }
    ```

### Networking & Security
*   **Internal Routing**: metadata can be pushed locally: `http://192.168.x.x:5150/ma/push-url`.
*   **Minimal Exposure**: Only ports 5150 and 8097 need public tunnels.

### LXC (Proxmox) Notes
*   Enable **Nesting** and **Keyctl** in LXC Features.
*   Ensure a valid UTF-8 locale is generated on the host.

---

## Further Reading
*   [COMPATIBILITY.md](COMPATIBILITY.md) - Supported hardware and regions.
*   [LIMITATIONS.md](LIMITATIONS.md) - Known limitations and troubleshooting.
*   [TODO.md](TODO.md) - Future feature roadmap.
