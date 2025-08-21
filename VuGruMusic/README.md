# VuGru Music MVP 🎵

A full-stack web application that generates custom background music for real estate videos using the ElevenLabs Music API.

## Features

- **Property-Specific Music Generation**: Create background tracks tailored to different property types (single-family, condo, luxury, etc.)
- **Customizable Musical Vibes**: Choose from various styles like calm elegant, upbeat modern, luxury cinematic, and more
- **Flexible Audio Settings**: Control duration (20-60 seconds), vocals, and intensity curves
- **Real-Time Preview**: Play generated tracks directly in the browser
- **Easy Downloads**: One-click download of generated MP3 files
- **Recent Tracks History**: Quick access to your last 5 generated tracks
- **Mobile-Friendly Interface**: Responsive design that works on all devices
- **Request Management**: Cancel generation requests and handle errors gracefully

## Tech Stack

- **Backend**: FastAPI (Python 3.11)
- **Frontend**: Vanilla HTML/CSS/JavaScript (no build step required)
- **API Integration**: ElevenLabs Music API
- **Audio Handling**: Web Audio API with MP3/WAV blob support
- **Environment Management**: python-dotenv

## Setup Instructions

### Prerequisites

- Python 3.11 or higher
- ElevenLabs API account and API key
- Modern web browser with audio support

### Installation

1. **Install Dependencies**
   ```bash
   pip install fastapi uvicorn python-dotenv httpx
   ```

2. **Configure Environment Variables**
   
   Create a `.env` file in the root directory:
   ```env
   ELEVENLABS_API_KEY=your_elevenlabs_api_key_here
   