# Meccanoid Motion Match Project Instructions

## Project Overview
The goal is to create an interactive "Simon Says" game where a Meccanoid 2.0 robot performs poses, and a player, whose movements are tracked via webcam and pose estimation, attempts to mimic those poses. The game will feature audiovisual feedback on a TV. Control will be via the Meccanoid's native brain using Python.

## Technical Preferences
- **Programming Language:** Python 3.x
- **Development Environment:** Use `venv` for virtual environments.
- **Target Platforms:**
    - Primary: Linux (Pop!_OS)
    - Deployment: Raspberry Pi 4 (consider performance implications)
- **Essential Tools:** Git for version control.
- **Key Python Libraries:**
    - Bluetooth LE: `bleak`
    - Pose Estimation: `mediapipe`
    - Audiovisual: `pygame`
    - Webcam/Image Processing: `opencv-python`

## General Guidelines
- Refer to `ai-tasks.md` for the detailed project plan and specific tasks.
- Prioritize clear, modular, and well-commented code.
- Ensure solutions are adaptable for both the development (Linux) and deployment (Raspberry Pi 4) environments.
