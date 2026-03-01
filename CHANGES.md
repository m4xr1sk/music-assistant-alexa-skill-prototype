# CHANGES

Changelog and project evolution log.

## STEP 1 — Hardening & Dual-Port Architecture

Complete restructuring for security, isolation, and legacy dependency removal.

### Security & Infrastructure (Docker)
- **Dockerfile Hardening**: 
  - Removed `debugpy` installation (RCE risk).
  - Removed Node.js and ASK CLI dependencies (major reduction in image size).
  - Removed exposure of `DEBUG_PORT`.
  - Configured `appuser` (non-root) for container execution.
- **Production Readiness**: Replaced the Werkzeug development server with `gunicorn` for the public endpoint.
- **CI/CD**: Updated GitHub Actions workflow (`docker-ghcr.yml`) to automatically build and push the image to GHCR on pushes to the `master` branch.

### Dual-Port Architecture
- **Port 5150 (Public)**: Reserved exclusively for the Alexa skill endpoint (`POST /`). Full signature validation by Amazon is strictly required.
- **Port 5151 (Local/Admin)**: Access to the Status Dashboard, invocation logs, and Music Assistant API. 
  - Protected by **HTTP Basic Auth**.
  - Accessible only via internal network/LAN.

### Credential Management
- **Auto-generation**: On first run, the system automatically generates random `app_username.txt` and `app_password.txt` in the `secrets/` folder if missing.
- **Git Hygiene**: The `secrets/` folder has been added to `.gitignore` to prevent accidental credential leaks.

### Cleanup & Simplification
- **Component Removal**:
  - Completely removed the **Simulator** (and its `X-Simulator-Bypass` signature bypass).
  - Removed **Swagger UI** interface (`/docs`).
  - Removed over 15 scripts and utilities related to ASK CLI and automated skill creation.
- **User Interface**: Updated the status dashboard to remove references to deleted components.
- **Documentation**: Created [SKILL_SETUP.md](file:///c:/Users/canta/__DATA/_tail/music-assistant-alexa-skill-prototype/SKILL_SETUP.md) to guide users through the manual skill creation process via the Alexa Developer Console.
