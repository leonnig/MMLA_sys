# Multimodal Learning Monitoring and Analytics System (MMLA)

This project is a prototype system for real-time multimodal learning behavior monitoring. It integrates eye-tracking (via MediaPipe), speech recognition, keyboard and mouse activity tracking to provide a comprehensive dashboard for analyzing learner engagement and interactions.

## Features
Real-time eye gaze estimation using MediaPipe Face Mesh

Keyboard and mouse activity logging

Speech keyword detection and recognition

Flask-based web dashboard displaying live, aggregated data

Modular design facilitates multi-device and multi-user scalability

## Installation
- Clone the repository
- Set up a Python virtual environment

```shell
py -3.11 -m venv my_venv
```

- Install required packages via

```shell
pip install -r requirements.txt
```

Connect your webcam for eye tracking

Run the main detection scripts and launch the Flask dashboard

## Usage

Run media_eye_tracking.py to start multimodal data collection

```python
python media_eye_tracking.py
```

Launch the Flask web server using python app.py

Access the dashboard at http://localhost:5000

Use the dashboard to monitor live learner behavior and data

## Contributing
Contributions and integrations of additional modalities are welcome. Please open issues or pull requests for improvements or bug fixes.

## License
## MIT License
