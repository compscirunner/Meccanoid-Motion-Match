# Meccanoid Motion Match

![Meccanoid Motion Match Banner Placeholder](https://via.placeholder.com/800x200.png?text=Meccanoid+Motion+Match)
*(Replace the placeholder above with a cool banner image for your project!)*

**Meccanoid Motion Match is an interactive "Simon Says" game where players match poses performed by a Meccanoid robot, controlled by communicating with its native smart brain. Using computer vision to detect the player's stance, the game challenges you to mimic the robot's moves, with engaging sound and visual feedback displayed on a TV.**

---

## Project Overview
The goal is to create an interactive "Simon Says" game where a Meccanoid 2.0 robot performs poses, and a player, whose movements are tracked via webcam and pose estimation, attempts to mimic those poses. The game will feature audiovisual feedback on a TV. Control will be via the Meccanoid's native brain using Python.

---

## 🌟 Features

- Real-time human pose estimation via webcam.
- Bluetooth LE control of a Meccanoid 2.0 robot.
- "Simon Says" style gameplay.
- Audiovisual feedback.

---

## 🎮 Gameplay

1.  **Watch Simon (The Meccanoid!):** The Meccanoid robot will perform a specific pose (e.g., "arms up," "left arm out").
2.  **Sound Cue:** An accompanying sound will play, indicating it's time for your move.
3.  **Strike a Pose!:** The player stands in front of the webcam and tries to mimic the robot's pose within a given time.
4.  **Pose Detection:** The system analyzes the player's pose using computer vision.
5.  **Get Feedback:** The TV display will show if the pose was matched correctly, along with sounds for success or failure.
6.  **Level Up:** If successful, the game may continue, potentially increasing the complexity or sequence of poses. See if you can keep up with the Meccanoid!

---

## 🛠️ Technology Stack (High-Level)

- Python 3.x
- `bleak` (Bluetooth LE)
- `mediapipe` (Pose Estimation)
- `pygame` (Audiovisual)
- `opencv-python` (Webcam/Image Processing)

---

## ⚙️ Hardware Requirements

* **Meccanoid Robot:** \[Specify model, e.g., G15 KS, G15] - Project utilizes the stock Meccanoid with its original internal electronics, including the smart brain/main control board.
* **Computer:**
    * Development: Modern Linux Laptop (e.g., running Pop!\_OS 22.04)
    * Deployment Target: Older Linux Laptop or Raspberry Pi 4 (or newer)
* **Webcam:** Standard USB webcam compatible with your computer.
* **Display:** TV or Monitor with HDMI input (for game visuals and sound).
* **Bluetooth:** Built-in or USB Bluetooth adapter on the computer for communicating with the Meccanoid's brain.

---

## 💾 Software Requirements & Installation

*(This section will be more detailed as the project develops. Below is a general outline.)*

1.  **Clone the Repository:**

    ```bash
    git clone [URL_OF_YOUR_GIT_REPOSITORY]
    cd MeccanoidMotionMatch
    ```
2.  **Python Environment:**
    * Python 3.x recommended.
    * Consider using a virtual environment:

        ```bash
        python3 -m venv venv
        source venv/bin/activate
        ```
3.  **Install Dependencies:**
    * Create a `requirements.txt` file as you identify libraries.

        ```bash
        pip install -r requirements.txt
        ```
    * Potential key libraries (you'll fill this in):
        * `[Pose Estimation Library - e.g., mediapipe, tensorflow-lite-runtime]`
        * `[Bluetooth Library - e.g., bleak, pygatt, bluepy]` (for communication with the Meccanoid brain)
        * `[Audiovisual Library - e.g., pygame]`
        * `opencv-python` (often a dependency for pose estimation/webcam)
4.  **Bluetooth Setup (Linux):**
    * Ensure BlueZ is installed and running.
    * The user running the script may need to be part of the `bluetooth` group or have appropriate permissions.
    * Pair/connect to the Meccanoid if required by your chosen Bluetooth library and its method of communicating with the robot's brain.

---

## Setup
Instructions to be added for:
- Python environment setup (`venv`).
- Installing dependencies from `requirements.txt`.
- Bluetooth device configuration (if needed).

---

## ▶️ How to Run

*(This section will be updated with specific instructions.)*

1.  Ensure all hardware is connected (Meccanoid powered on with its brain active, webcam plugged in, TV connected).
2.  Navigate to the project directory.
3.  Activate your Python virtual environment (if used).
4.  Run the main game script:

    ```bash
    python main_game.py # Or your main script name
    ```

---

## Project Structure
```
Meccanoid-Motion-Match/
├── .venv/
├── .git/
├── .github/
│   └── copilot-instructions.md
├── src/
│   ├── __init__.py
│   ├── robot_control.py
│   ├── pose_estimation.py
│   ├── game_logic.py
│   └── main.py
├── assets/
│   ├── sounds/
│   └── images/
├── tests/
├── .gitignore
├── README.md
├── requirements.txt
└── ai-tasks.md
```

---

## 🚀 Future Ideas / To-Do

* \[ ] Add more complex poses for the Meccanoid.
* \[ ] Implement different difficulty levels.
* \[ ] Introduce sequences of poses instead of just one at a time.
* \[ ] Scoring system and high scores.
* \[ ] Calibration mode for human pose detection.
* \[ ] GUI for settings or game selection.
* \[ ] Explore reading sensor data or battery level from the Meccanoid brain if its protocol allows.

---

## 🤝 Contributing

*(Optional: Add guidelines if you plan for others to contribute.)*
Contributions are welcome! Please fork the repository and submit a pull request. For major changes, please open an issue first to discuss what you would like to change.

---

## 📜 License

*(Choose a license, e.g., MIT, GPL. If unsure, MIT is a common permissive one.)*
This project is licensed under the \[NAME OF LICENSE] - see the `LICENSE.md` file for details.

---

## Related Projects

* [Meccanoid-Imitate](https://github.com/lnmangione/Meccanoid-Imitate): A project exploring similar concepts of controlling a Meccanoid with external input.
