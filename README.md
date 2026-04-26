# 🚀 Sensor-Agnostic Autonomy Stack

⚡ Designed for scalable robotics systems with plug-and-play sensor integration.

A real-time perception-to-autonomy pipeline combining:

- 🧠 **SegFormer** → Semantic Segmentation  
- 📏 **MiDaS** → Depth Estimation  
- ⚠️ **Risk Engine** → Traversability Analysis  
- 🤖 **Autonomy Layer** → Motion Decision (GO / SLOW / STOP)  

---

## 📸 Demo

<img width="2048" height="580" alt="image" src="https://github.com/user-attachments/assets/05cd19d1-d8f0-4ab9-ab2f-7716d3221088" />


---

## 🧠 System Overview

This project implements a **sensor-agnostic perception pipeline** where any input source (camera, dataset, or future sensors) can be plugged into a unified interface.


---

## 🔥 Key Features

- ✅ Sensor-agnostic architecture (plug & play)
- ✅ Real-time 4-panel visualization dashboard
- ✅ Depth + segmentation fusion
- ✅ Traversability + risk estimation
- ✅ Standardized outputs for localization & motion teams
- ✅ Clean modular design for scalability

---

## 📁 Project Structure

<img width="509" height="824" alt="image" src="https://github.com/user-attachments/assets/94ef61a5-1f9f-45dc-b3db-7ca9b566d42b" />


---

## ⚙️ Installation

```bash
git clone https://github.com/your-username/sensor-agnostic-autonomy-stack.git
cd sensor-agnostic-autonomy-stack

pip install -r requirements.txt

---
## 📊 Output
JSON (for localization + motion)
{
  "timestamp": 1777142827.42,
  "frame_id": "front_camera",
  "sensor_type": "rgb_camera",
  "coordinate_system": "REP-103 (x forward, y left, z up)",
  "motion_command": {
    "action": "STOP"
  }
}


