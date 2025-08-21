# VuGru Music MVP

## Overview

VuGru Music MVP is a full-stack web application that generates custom background music for real estate videos using the ElevenLabs Music API. The application allows users to specify property types, musical vibes, and audio settings to create tailored background tracks. It features a clean, mobile-friendly interface with real-time audio preview, download capabilities, and a history of recently generated tracks.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Frontend Architecture
- **Technology**: Vanilla HTML/CSS/JavaScript with no build step required
- **Design Pattern**: Single-page application (SPA) with client-side state management
- **Responsive Design**: Mobile-first approach using CSS Grid and Flexbox
- **Audio Handling**: Web Audio API for blob-based MP3/WAV playback and download
- **State Management**: Local storage for user preferences and recent tracks history
- **Error Handling**: Graceful degradation with user-friendly error messages

### Backend Architecture
- **Framework**: FastAPI (Python 3.11) for high-performance async API endpoints
- **Static File Serving**: FastAPI's StaticFiles for frontend asset delivery
- **Request Management**: In-memory storage for active requests and caching
- **Rate Limiting**: IP-based request throttling to prevent abuse
- **Service Layer**: Dedicated ElevenLabsMusicService class for API abstraction
- **Error Handling**: Comprehensive HTTP status codes with JSON error responses

### API Design
- **RESTful Endpoints**: `/api/generate_music` for music generation
- **Request Validation**: Pydantic models for type safety and data validation
- **Streaming Responses**: Efficient audio file delivery with proper MIME types
- **Async Processing**: Non-blocking request handling with timeout management
- **CORS Support**: Cross-origin resource sharing for frontend-backend communication

### Data Storage
- **In-Memory Storage**: Active requests tracking and basic caching
- **Client-Side Storage**: localStorage for user preferences and recent tracks
- **No Database**: Simplified architecture without persistent data requirements
- **Cache Management**: Automatic cleanup of expired cache entries

### Authentication & Security
- **API Key Management**: Environment variable-based ElevenLabs API key storage
- **Rate Limiting**: Request throttling based on client IP addresses
- **Input Validation**: Server-side validation for all user inputs
- **Request Cancellation**: Abort controller pattern for graceful request termination

## External Dependencies

### Primary API Integration
- **ElevenLabs Music API**: Core music generation service
  - Authentication via Bearer token
  - RESTful API with JSON payloads
  - Binary audio response handling
  - Configurable generation parameters (duration, vocals, mode)

### Python Dependencies
- **FastAPI**: Web framework for API development
- **Uvicorn**: ASGI server for FastAPI applications
- **HTTPX**: Async HTTP client for ElevenLabs API communication
- **Pydantic**: Data validation and settings management
- **python-dotenv**: Environment variable management

### Frontend Dependencies
- **Web Audio API**: Browser-native audio processing and playback
- **Fetch API**: HTTP requests with abort controller support
- **localStorage**: Client-side data persistence
- **CSS Grid/Flexbox**: Modern layout systems for responsive design

### Development Tools
- **Environment Variables**: `.env` file configuration
- **Logging**: Python's built-in logging module for debugging
- **Type Hints**: Python type annotations for code clarity
- **Error Tracking**: Comprehensive exception handling and logging