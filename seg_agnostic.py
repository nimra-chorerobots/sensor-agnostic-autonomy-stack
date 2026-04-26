# =========================================================
# SENSOR-AGNOSTIC AUTONOMY STACK (FINAL)
# =========================================================

import os
import json
import cv2
import torch
import numpy as np
from dataclasses import dataclass
from abc import ABC, abstractmethod
import time

from transformers import SegformerImageProcessor, SegformerForSemanticSegmentation

# =========================================================
# SENSOR FORMAT
# =========================================================

@dataclass
class SensorFrame:
    timestamp: float
    frame_id: str
    sensor_type: str
    image_bgr: np.ndarray


# =========================================================
# SENSOR LAYER
# =========================================================

class BaseSensor(ABC):
    @abstractmethod
    def get_frame(self):
        pass


class ImageFolderSensor(BaseSensor):
    def __init__(self, folder):
        self.files = sorted([
            os.path.join(folder, f)
            for f in os.listdir(folder)
            if f.lower().endswith((".png", ".jpg", ".jpeg"))
        ])
        self.index = 0

    def get_frame(self):
        if self.index >= len(self.files):
            return None

        path = self.files[self.index]
        self.index += 1

        image = cv2.imread(path)

        return SensorFrame(
            timestamp=time.time(),
            frame_id="front_camera",
            sensor_type="rgb_camera",
            image_bgr=image
        )


# =========================================================
# CONFIG
# =========================================================

IMAGE_DIR = r"D:\Chore\codes\data_scene_flow\training\image_2"
OUTPUT_DIR = r"D:\Chore\codes\outputs_autonomy_stack_final"

os.makedirs(OUTPUT_DIR, exist_ok=True)

device = torch.device("cpu")

DISPLAY_WIDTH = 640
DISPLAY_HEIGHT = 360

STOP_DEPTH_THRESHOLD = 0.35
SLOW_DEPTH_THRESHOLD = 0.55

# =========================================================
# LOAD MODELS
# =========================================================

print("Loading models...")

processor = SegformerImageProcessor.from_pretrained(
    "nvidia/segformer-b0-finetuned-ade-512-512"
)

seg_model = SegformerForSemanticSegmentation.from_pretrained(
    "nvidia/segformer-b0-finetuned-ade-512-512"
)

seg_model.to(device).eval()

midas = torch.hub.load("intel-isl/MiDaS", "MiDaS_small")
midas.to(device).eval()

midas_transform = torch.hub.load("intel-isl/MiDaS", "transforms").small_transform

# =========================================================
# CLASS MAP
# =========================================================

ROAD_CLASSES = [6, 11]
OBSTACLE_CLASSES = [12, 13, 14, 15, 16, 17, 18]

# =========================================================
# VISUALIZATION FUNCTION
# =========================================================

def create_dashboard(image_bgr, seg_map, closeness, road_mask, obstacle_mask, status):

    h, w = image_bgr.shape[:2]

    # Segmentation
    seg_color = cv2.applyColorMap((seg_map * 10).astype(np.uint8), cv2.COLORMAP_JET)
    seg_overlay = cv2.addWeighted(image_bgr, 0.6, seg_color, 0.4, 0)

    # Depth
    depth_vis = (closeness * 255).astype(np.uint8)
    depth_color = cv2.applyColorMap(depth_vis, cv2.COLORMAP_INFERNO)

    # Risk overlay
    risk_vis = np.zeros_like(image_bgr)
    risk_vis[road_mask > 0] = (0, 255, 0)
    risk_vis[obstacle_mask > 0] = (0, 0, 255)

    autonomy_overlay = cv2.addWeighted(image_bgr, 0.6, risk_vis, 0.4, 0)

    # Resize panels
    original_disp = cv2.resize(image_bgr, (DISPLAY_WIDTH, DISPLAY_HEIGHT))
    seg_disp = cv2.resize(seg_overlay, (DISPLAY_WIDTH, DISPLAY_HEIGHT))
    depth_disp = cv2.resize(depth_color, (DISPLAY_WIDTH, DISPLAY_HEIGHT))
    risk_disp = cv2.resize(autonomy_overlay, (DISPLAY_WIDTH, DISPLAY_HEIGHT))

    # Labels
    cv2.putText(original_disp, "Original", (20, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255,255,255), 2)

    cv2.putText(seg_disp, "Segmentation", (20, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255,255,255), 2)

    cv2.putText(depth_disp, "Depth", (20, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255,255,255), 2)

    color = (0,255,0) if status=="GO" else (0,165,255) if status=="SLOW" else (0,0,255)

    cv2.putText(risk_disp, f"Autonomy | {status}", (20, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)

    combined = np.hstack((original_disp, seg_disp, depth_disp, risk_disp))

    return combined


# =========================================================
# PIPELINE
# =========================================================

sensor = ImageFolderSensor(IMAGE_DIR)

cv2.namedWindow("Autonomy Stack", cv2.WINDOW_NORMAL)
cv2.resizeWindow("Autonomy Stack", DISPLAY_WIDTH*4, DISPLAY_HEIGHT)

frame_count = 0

while True:

    frame = sensor.get_frame()
    if frame is None:
        break

    image_bgr = frame.image_bgr
    image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)

    h, w = image_rgb.shape[:2]

    # ---------------- SEGMENTATION ----------------
    inputs = processor(images=image_rgb, return_tensors="pt").to(device)

    with torch.no_grad():
        outputs = seg_model(**inputs)

    logits = torch.nn.functional.interpolate(
        outputs.logits,
        size=(h, w),
        mode="bilinear",
        align_corners=False
    )

    seg_map = logits.argmax(dim=1)[0].cpu().numpy().astype(np.uint8)

    road_mask = np.isin(seg_map, ROAD_CLASSES).astype(np.uint8) * 255
    obstacle_mask = np.isin(seg_map, OBSTACLE_CLASSES).astype(np.uint8) * 255

    # ---------------- DEPTH ----------------
    input_batch = midas_transform(image_rgb).to(device)

    with torch.no_grad():
        depth_pred = midas(input_batch)

    depth_pred = torch.nn.functional.interpolate(
        depth_pred.unsqueeze(1),
        size=(h, w),
        mode="bicubic",
        align_corners=False
    ).squeeze()

    depth_map = depth_pred.cpu().numpy()
    depth_norm = (depth_map - depth_map.min()) / (depth_map.max() - depth_map.min() + 1e-6)

    closeness = depth_norm

    # ---------------- RISK ----------------
    obstacle_area = obstacle_mask == 255

    red_zone = obstacle_area & (closeness > SLOW_DEPTH_THRESHOLD)
    yellow_zone = obstacle_area & (closeness > STOP_DEPTH_THRESHOLD)

    red_ratio = np.sum(red_zone) / (h * w)
    yellow_ratio = np.sum(yellow_zone) / (h * w)

    # FIXED THRESHOLDS
    if red_ratio > 0.01:
        status = "STOP"
    elif yellow_ratio > 0.02:
        status = "SLOW"
    else:
        status = "GO"

    # ---------------- DASHBOARD ----------------
    dashboard = create_dashboard(
        image_bgr,
        seg_map,
        closeness,
        road_mask,
        obstacle_mask,
        status
    )

    cv2.imshow("Autonomy Stack", dashboard)

    # ---------------- JSON OUTPUT ----------------
    output = {
        "timestamp": frame.timestamp,
        "frame_id": frame.frame_id,
        "sensor_type": frame.sensor_type,
        "coordinate_system": "REP-103 (x forward, y left, z up)",

        "perception": {
            "road_ratio": float(np.sum(road_mask > 0) / (h*w)),
            "obstacle_ratio": float(np.sum(obstacle_mask > 0) / (h*w)),
        },

        "risk": {
            "red_ratio": float(red_ratio),
            "yellow_ratio": float(yellow_ratio),
        },

        "motion_command": {
            "action": status
        }
    }

    with open(os.path.join(OUTPUT_DIR, f"{frame_count:06d}.json"), "w") as f:
        json.dump(output, f, indent=4)

    print(output)

    frame_count += 1

    if cv2.waitKey(1) == ord("q"):
        break

cv2.destroyAllWindows()

print("✅ DONE — Full sensor-agnostic autonomy stack running")