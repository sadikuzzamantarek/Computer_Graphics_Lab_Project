# 4-Stroke Engine Simulation with PyOpenGL

A real-time, interactive visualization of a 4-stroke internal combustion engine cycle (Intake → Compression → Power → Exhaust). Built with PyOpenGL, this simulation shows the crankshaft, connecting rod, piston, valves, spark plug, and combustion effects while clearly indicating the current stroke.

![Engine Simulation Screenshot](/images/screenshot.png)  

## Features

- **Full 4‑stroke cycle** – Intake, Compression, Power (with combustion flash), Exhaust.
- **Live physics** – Piston motion calculated from crank angle using slider‑crank kinematics.
- **Graphical components**:
  - Cylinder head, valves (open/close based on stroke), spark plug, combustion chamber gases.
  - Piston with rings, connecting rod, crankshaft, flywheel with timing mark.
  - Intake and exhaust pipes.
- **Stroke indicator panel** – Highlights the active stroke and provides a short description.
- **Interactive controls** – Pause/resume, speed adjustment, reset, quit.
- **Smooth animation** – Runs at ~60 FPS with OpenGL double buffering.

## Requirements

- Python 3.6 or higher
- PyOpenGL and PyOpenGL_accelerate
- A working installation of **GLUT** (freeglut / the system’s GLUT library)

## Installation

1. **Clone or download** this repository to your local machine.
2. **Install the Python dependencies** using pip:

   ```bash
   pip install PyOpenGL PyOpenGL_accelerate