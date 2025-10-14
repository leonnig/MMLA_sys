# Multimodal Learning Monitoring and Analytics System (MMLA)

This project is a prototype system for real-time multimodal learning behavior monitoring. It integrates eye-tracking (via MediaPipe), image detection, speech recognition, keyboard and mouse activity tracking to provide a comprehensive dashboard for analyzing learner engagement and interactions.

## Features
Real-time eye gaze estimation using MediaPipe Face Mesh

Object detection using yolo11 do image recognition

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

- Activate virtual environment

```shell
.\mmla\Scripts\activate
```

- Install required packages via

```shell
pip install -r requirements.txt
```

- Install torch

```shell
pip3 install torch torchvision
```

- Install yolo
  
```shell
pip install ultralytics  
```

Connect your webcam(you need two) for eye tracking and image detecting

Run the main detection scripts and launch the Flask dashboard

## Usage

Run mmla.py to start multimodal data collection

```python
python mmla.py
```

Launch the Flask web server using python app.py

Access the dashboard at http://localhost:5000

Use the dashboard to monitor live learner behavior and data

## Contributing
Contributions and integrations of additional modalities are welcome. Please open issues or pull requests for improvements or bug fixes.

## License
## MIT License
