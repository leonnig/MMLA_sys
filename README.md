# Multimodal Learning Monitoring and Analytics System (MMLA)

This project is a prototype system for real-time multimodal learning behavior analysis and timely intervention, designed specifically for K-12 STEM and Arduino programming education.

Grounded in the **ICAP framework** (Interactive, Constructive, Active, Passive), the system integrates computer vision, speech recognition, and OS-level activity tracking to diagnose student engagement. When a learner is detected as "stuck" or asks for help, a Generative AI virtual assistant provides context-aware, Socratic feedback to guide them without causing cognitive overload.

## Features
- Gaze Tracking: Real-time eye tracking via MediaPipe Face Mesh.

- Object & Hand Detection: Custom YOLOv11 model detecting interactions between hands, Arduino, breadboards, and laptops.

- Speech Intent Recognition: Detects keywords to classify "Help Seeking" or "Peer Discussion" intents.

- Peripheral Tracking: Keyboard and mouse activity logging.

- IDE Code Monitoring: Watchdog integration to track .ino file saves dynamically.

**ICAP Behavior Analysis:** Accurately classifies learning states (e.g., Constructive: Testing & Debugging, Passive: Viewing Code) with State Smoothing (Anti-Jitter) mechanisms to ensure robust data collection.

**GenAI Virtual Teaching Assistant:** Powered by OpenAI (gpt-5.4). It features Context Memory Tracking to avoid repetitive advice and provides targeted, empathetic hints based on the student's exact code state and multimodal context.

**Cloud Integration:** Automatically packages and uploads behavior logs (CSV) to Google Cloud Storage (GCS) upon secure system exit.

## Installation
- Clone the repository

```shell
git clone https://github.com/yourusername/MMLA_sys.git
cd MMLA_sys
```
- Set up a Python virtual environment

```shell
py -3.11 -m venv mmla
```

- Activate virtual environment

```shell
.\mmla\Scripts\activate
```

- Install required packages via

```shell
pip install -r requirement.txt
```

- Install torch

```shell
pip3 install torch torchvision
```

- Install yolo
  
```shell
pip install ultralytics  
```

- Install google-cloud-storage to save behavior logs

```shell
pip install google-cloud-storage
```

- Install plyer

```shell
pip install plyer
```

- Install openai and watchdog package

```shell
pip install openai watchdog
```

## Hardware Requirements:

- Two webcams (one for facial/gaze tracking, one for desk/hand/Arduino tracking).

- Microphone for speech recognition.

## API Key Configuration:

For security reasons, never hardcode your API keys. Create a .env file in the root directory and add your OpenAI API key:

```shell
OPENAI_API_KEY=sk-proj-your-actual-api-key-here
```
(Ensure .env is added to your .gitignore file to prevent accidental pushes to GitHub).

## Google Cloud Storage Credentials:
Place your GCS service account key (gcp-credentials.json) in the root directory to enable cloud logging.

## Usage

1. Run mmla.py to start multimodal data collection

```python
python mmla.py
```

2. Using the Dashboard:
- *Student ID & Path:* Enter the Student ID and browse for the target Arduino .ino project folder.

- *Start/Pause/Resume:* Use the UI buttons to control the monitoring state. The system features a dynamic watchdog that tracks the folder seamlessly even after pausing and switching paths.

- *Toggle Video:* Check the "Show Camera Feeds" box to open OpenCV windows for debugging (Note: unchecking this hides the windows but keeps the AI running in the background to save CPU/GPU resources).

- *Safe Exit:* Click "End System" or close the window to safely stop all daemon threads and trigger the automatic GCS log upload.


## Contributing
Contributions and integrations of additional modalities are welcome. Please open issues or pull requests for improvements or bug fixes.

## License
## MIT License
