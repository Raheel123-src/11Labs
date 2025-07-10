# ElevenLabs Automation API

This project provides an API for automating ElevenLabs TTS enhancement and audio generation using FastAPI.

## Features
- Enhance scripts using ElevenLabs TTS
- Generate and download audio
- API endpoints for automation

## Deployment: Render

### 1. Requirements
- Python 3.12 or higher
- `requirements.txt` (already provided)
- `Procfile` (see below)
- Your code pushed to GitHub

### 2. Procfile
Create a file named `Procfile` in your project root with this content:

```
web: uvicorn api:app --host 0.0.0.0 --port 10000
```

### 3. Environment Variables
Set the following secrets in the Render dashboard:
- ELEVENLABS_API_KEY
- ELEVENLABS_EMAIL
- ELEVENLABS_PASSWORD
- VOICE_ID
- BROWSER_USE_API_KEY

### 4. Deploy Steps
1. Push your code to GitHub.
2. Go to [Render](https://dashboard.render.com/), create a new Web Service, and connect your repo.
3. Set the build command to:
   ```
   pip install -r requirements.txt
   ```
4. Set the start command to:
   ```
   uvicorn api:app --host 0.0.0.0 --port 10000
   ```
5. Set environment variables in the Render dashboard.
6. Deploy!

### 5. Usage
- Your API will be live at `https://<your-app-name>.onrender.com`
- Visit `/docs` for the Swagger UI.

---

## Local Development

You can run locally with:
```sh
uvicorn api:app --reload
```

---

## No Modal Required
This project is now fully compatible with Render and does not require Modal. 