<div align="center">
  <img src="torquewizard.png" alt="TorqueWizard Logo" width="128" height="128">

  <h1>TorqueWizard ✈️</h1>

  <p>
    <strong>A Serial Dashboard Designed for Propeller Traction Telemetry</strong>
  </p>

  <p>
    <a href="https://nicegui.io/">
      <img src="https://img.shields.io/badge/GUI-NiceGUI-orange?style=flat-square" alt="NiceGUI">
    </a>
    <a href="https://pyserial.readthedocs.io/">
      <img src="https://img.shields.io/badge/Serial-PySerial-blue?style=flat-square" alt="PySerial">
    </a>
    <a href="https://plotly.com/python/">
      <img src="https://img.shields.io/badge/Graphs-Plotly-green?style=flat-square" alt="Plotly">
    </a>
  </p>
</div>

<br>

## 📖 About

This application was built to solve a specific problem: visualizing the raw data coming from a load cell during propeller thrust tests. Instead of reading raw text from a serial monitor, TorqueWizard instantly plots the data, allowing engineers to see thrust curves in real-time.



The GUI is built entirely in Python using **NiceGUI**, making it lightweight and responsive while running locally as a native desktop application.




## ✨ Key Features

### 🖥️ Modern GUI (Powered by NiceGUI)
Unlike traditional Tkinter or Qt apps, TorqueWizard uses a web-based architecture running natively on your desktop. This ensures a clean, modern look with responsive controls.

### 🔌 Complete Serial Monitor (Powered by PySerial)
A fully functional serial debugger is built-in.
* **Plug & Play:** Automatically detects available COM ports.
* **Configurable:** Supports all standard Baud rates (from 1200 to 115200+).
* **Bi-directional:** Send and receive commands to your MCU simultaneously.

### 📊 Advanced Visualization (Powered by Plotly)
* **Real-time Plotting:** Live graph updates at 80Hz.
* **Automatic Scaling:** Graphs adjust automatically to fit the data.
* **Interactive Tools:** Zoom, pan, export png and hover over specific data points to see exact values.

### 💾 Data Management (CSV)
* **Export:** Record your sessions and save them instantly as `.csv` files.
* **Import & Replay:** Drag and drop previous `.csv` files to "replay" the test and view the full high-resolution graph.

---

##  How to Run

### 🐧 Option 1: Linux Standalone App (.AppImage )
### 🪟 Option 2: Windows Standalone App (.exe  )
### 🖥️ Option 3: Just execute nice.py   
