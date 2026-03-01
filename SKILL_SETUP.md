# Skill Setup — Alexa Developer Console

This guide explains how to manually create and configure the Alexa skill in the [Amazon Developer Console](https://developer.amazon.com/alexa/console/ask).

## Prerequisites

- An Amazon Developer account
- The skill server running and accessible via HTTPS (e.g. via Cloudflare Tunnel, ngrok, or similar)
- Your `SKILL_HOSTNAME` (the public HTTPS hostname pointing to port 5150 of the container)

## Step 1 — Create a New Skill

1. Go to the [Alexa Developer Console](https://developer.amazon.com/alexa/console/ask)
2. Click **Create Skill**
3. Enter a skill name, e.g. `Music Assistant`
4. Select your preferred language/locale (e.g. `Italian (IT)`)
5. Choose **Custom** model
6. Choose **Provision your own** for the backend
7. Click **Create Skill**, then select **Start from scratch**

## Step 2 — Set the Endpoint

1. In the left sidebar, click **Endpoint**
2. Select **HTTPS**
3. In the **Default Region** field, enter: `https://<YOUR_SKILL_HOSTNAME>/`
4. For the SSL certificate type, select:
   - *My development endpoint has a certificate from a trusted certificate authority* (if using Cloudflare Tunnel or a real cert)
   - *My development endpoint is a sub-domain of a domain that has a wildcard certificate...* (if applicable)
5. Click **Save Endpoints**

## Step 3 — Import the Interaction Model

1. In the left sidebar, click **Interaction Model** → **JSON Editor**
2. Open the file `app/models/<your-locale>.json` from this repository (e.g. `app/models/it-IT.json`)
3. Paste the JSON content into the editor
4. Click **Save Model**
5. Click **Build Model** and wait for it to complete

## Step 4 — Enable Testing

1. Go to the **Test** tab at the top
2. Set **Skill testing is enabled in:** to **Development**
3. You can now test the skill via the Alexa simulator or your Echo device

## Step 5 — Configure Audio Player

1. In the left sidebar, click **Interfaces**
2. Enable **Audio Player**
3. Click **Save Interfaces**
4. Rebuild the model if prompted

## Troubleshooting

- **Skill not responding**: Check that the container is running and the tunnel is active. Visit `https://<SKILL_HOSTNAME>/` in a browser — you should get an error (POST only), which confirms the endpoint is reachable.
- **Check status**: Navigate to `http://<server-ip>:5151/status` (admin port) to see the system status dashboard.
- **Check invocations**: Navigate to `http://<server-ip>:5151/invocations` to see incoming Alexa requests and responses.
