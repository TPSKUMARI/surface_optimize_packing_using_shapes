# Surface Shape Packing Project

This project is a simple Python application for experimenting with different shapes and how they can be arranged efficiently on a surface.

It includes:
- shape drawing and layout testing
- optimization logic for packing shapes in rows and patterns
- support for several basic geometric shapes
- a camera-based mode for detecting real-world shapes from a webcam

## Project files

- `test_for_any_shape_.py` - main shape-packing and shape-layout demo
- `using_camera.py` - version that uses OpenCV and a camera feed to detect shapes

## Main idea

The project focuses on placing 2D shapes onto a surface with minimal wasted space. Different shapes have different packing behavior, so the code tries to arrange them in a way that looks more efficient and visually balanced.

Examples of supported shapes include:
- rectangle
- circle
- triangle
- hexagon
- diamond
- pentagon
- star

## Technologies used

- Python
- PySide6 for the graphical user interface
- OpenCV for camera-based shape detection
- NumPy for image processing

## How to run

1. Open the project folder in Python environment.
2. Install the required packages:

```bash
pip install PySide6 opencv-python numpy
```

3. Run the script you want:

```bash
python test_for_any_shape_.py
```

or

```bash
python using_camera.py
```

## Notes

- `test_for_any_shape_.py` is useful for testing shape packing without a camera.
- `using_camera.py` uses the webcam to detect a shape and show it in the GUI.
- This project is meant as a lightweight prototype/demo rather than a production-grade packing engine.

## Purpose

This project is a good starting point for learning:
- GUI programming with Python
- shape generation and drawing
- efficient layout optimization
- OpenCV-based detection and image processing
