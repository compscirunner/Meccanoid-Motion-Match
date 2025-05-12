Project Development Plan: Meccanoid Motion Match

Goal: To create an interactive "Simon Says" game where a Meccanoid 2.0 robot performs poses, and a player, whose movements are tracked via webcam and pose estimation, attempts to mimic those poses. The game will feature audiovisual feedback on a TV. Control will be via the Meccanoid's native brain using Python.

Phase I: Project Setup and Foundations

Step 1: Environment & Initial Project Structure

Task for AI: "Help me set up a Python 3.x development environment using venv on Linux (Pop!_OS, with considerations for future Raspberry Pi 4 deployment). List essential tools (Git, etc.). Assist in creating a basic project directory structure, a README.md (using our previous draft as a base), and a standard Python .gitignore file."
Step 2: Core Library Installation & Management

Task for AI: "Guide me through installing the following Python libraries and help create/update a requirements.txt file:
A Bluetooth LE library (e.g., bleak).
A pose estimation library (e.g., mediapipe).
An audiovisual library (e.g., pygame).
opencv-python."
Phase II: Meccanoid Robot Control Module (via Native Brain)

Step 3: Establish Bluetooth LE Connection to Meccanoid 2.0

Task for AI: "Provide a Python script using the chosen BLE library (e.g., bleak) to scan for Bluetooth LE devices. Help me identify and connect to my Meccanoid 2.0 robot by its MAC address. Once connected, show how to list its available services and characteristics."
Step 4: Implement Meccanoid 2.0 Communication Protocol

Task for AI: "Based on available information for Meccanoid G15KS/2.0 smart module protocols (like packet structure, checksums, command bytes for servo movement and LED control from resources like pymecca or official Meccano open-source info), help me develop Python functions to:
Craft and send valid command packets to the Meccanoid brain via BLE.
Control a single Meccanoid 2.0 servo to a specific position.
Control the color of an LED within a Meccanoid 2.0 servo module."
Step 5: Define and Test Robot Poses

Task for AI: "Assist in creating a Python module (e.g., robot_control.py) that includes:
Functions to command individual servos (from Step 4).
Definitions for a set of 3-5 distinct, achievable poses for the Meccanoid 2.0 (e.g., pose_arms_up, pose_left_arm_out), where each pose is a dictionary or list of target positions for relevant servos.
A function execute_pose(pose_name) that makes the robot perform the named pose.
Help write a test script to cycle through and display these poses on the actual robot."
Phase III: Human Pose Estimation Module

Step 6: Webcam Input & Real-Time Pose Visualization

Task for AI: "Provide Python code using OpenCV to capture video from my webcam. Integrate the chosen pose estimation library (e.g., MediaPipe MoveNet) to process this feed and display the detected pose skeleton (keypoints and connections) in a real-time preview window."
Step 7: Extract and Normalize Key Pose Data

Task for AI: "Show me how to extract the 2D (or 3D if available) coordinates of specific body joints (e.g., shoulders, elbows, wrists, hips) from the pose estimation output. Advise on normalizing these coordinates (e.g., relative to torso height or a central point) to make them scale and position invariant."
Step 8: Develop Pose Representation & Matching Logic

Task for AI: "Advise on simple ways to represent a human pose for comparison (e.g., using angles between key limb segments, or relative positions of keypoints like 'wrists above shoulders'). Help me develop initial Python functions that take the normalized human pose data (from Step 7) and compare it against a target robot pose (from Step 5). This function should return True if a match is detected based on defined criteria and thresholds, False otherwise. Start with one example pose."
Phase IV: Core Game Logic ("Meccanoid Motion Match")

Step 9: Design Basic Game State Machine & Loop

Task for AI: "Help me outline a simple state machine for the game (e.g., ROBOT_TURN, PLAYER_TURN, EVALUATE, SHOW_RESULT). Then, help structure the main Python game loop that transitions through these states."
Step 10: Implement Core "Simon Says" Sequence

Task for AI: "Within the game loop, guide me to implement the following sequence:
Robot randomly selects one of its defined poses (from Step 5) and executes it.
A brief pause for the player.
Capture the player's pose via webcam for a few seconds (using Step 6 & 7).
Evaluate if the player's pose matches the robot's pose (using Step 8)."
Step 11: Implement Basic Scoring & Round Progression

Task for AI: "Assist in adding a simple scoring mechanism (e.g., points for a correct match) and a way to track rounds or player 'lives'. The game should loop for a few rounds or until 'lives' run out."
Phase V: Audiovisual Integration (TV Output using Pygame)

Step 12: Basic Pygame Window Setup for TV Display

Task for AI: "Show me how to initialize Pygame and create a display window (intended for a TV connected via HDMI). Help render basic text on this window (e.g., 'Robot's Turn', current score)."
Step 13: Integrate Visual Feedback for Gameplay

Task for AI: "Guide me to integrate the live webcam feed with the pose skeleton overlay (from Step 6) into the Pygame window. Add visual cues like:
Text indicating the current robot pose name.
"Correct!" or "Try Again!" messages based on pose evaluation."
Step 14: Add Basic Sound Effects

Task for AI: "Help me use Pygame's sound mixer to load and play simple .wav or .mp3 sound effects for events like: robot performing a pose, player success, player failure."
Phase VI: Game Refinements & Polish

Step 15: Develop Configuration Options

Task for AI: "Advise on creating a simple configuration file (e.g., config.json or config.py) for settings like robot MAC address, game timers (e.g., time for player to pose), and pose matching sensitivity thresholds. Show how to load these settings into the game."
Step 16: Iterative Pose Matching Improvement

Task for AI: "As I test, if pose matching is too strict or too lenient, help me debug and refine the matching logic (from Step 8) and the configuration thresholds (Step 15)."
Step 17: Add Simple UI Screens

Task for AI: "Help design and implement basic Pygame screens for:
A 'Start Game' screen with instructions.
A 'Game Over' screen displaying the final score."
Phase VII: Testing, Documentation & Deployment Considerations

Step 18: Testing on Target Platforms

Task for AI: "Provide a checklist for testing the full game flow, including robot interaction, pose accuracy, and AV performance, especially if I plan to run this on a Raspberry Pi 4."
Step 19: Finalize Documentation

Task for AI: "Help me review and expand the README.md with detailed setup instructions for all dependencies, clear steps on how to run the game, and a troubleshooting section for common issues (e.g., Bluetooth connection, webcam access)."
Step 20: (Optional) Performance Optimization for Raspberry Pi

Task for AI: "If performance is an issue on Raspberry Pi 4, suggest potential optimization strategies for the Python code, especially for pose estimation and image processing."
