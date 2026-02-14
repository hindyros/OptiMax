#!/usr/bin/env bash
# Run this script ON the Google Cloud GPU VM (Ubuntu 22.04) to install
# SGLang and launch the OptiMind server.
# Usage: chmod +x setup-optimind-gcp.sh && ./setup-optimind-gcp.sh

set -e

echo "[setup] Checking NVIDIA driver..."
if ! command -v nvidia-smi &>/dev/null; then
  echo "[setup] nvidia-smi not found. Installing NVIDIA driver..."
  # GCP one-line driver install (Ubuntu 22.04)
  curl -sS -O https://raw.githubusercontent.com/GoogleCloudPlatform/compute-gpu-installation/main/linux/install_gpu_driver.py
  sudo python3 install_gpu_driver.py
  rm -f install_gpu_driver.py
  echo "[setup] Driver installed. Reboot may be required. Run: sudo reboot"
  exit 0
fi
nvidia-smi

echo "[setup] Installing Python 3.12 and venv..."
sudo apt-get update -y
sudo apt-get install -y python3.12 python3.12-venv python3-pip 2>/dev/null || true

echo "[setup] Creating venv and installing SGLang..."
PYTHON=python3.12
if ! command -v $PYTHON &>/dev/null; then
  PYTHON=python3
fi
$PYTHON -m venv ~/venv
source ~/venv/bin/activate
pip install --upgrade pip
pip install "sglang[all]>=0.4.5" --find-links https://flashinfer.ai/whl/cu124/torch2.5/flashinfer-python
pip install gurobipy

echo "[setup] Launching OptiMind SGLang server (first run downloads ~28 GB)..."
exec python -m sglang.launch_server \
  --model-path microsoft/OptiMind-SFT \
  --host 0.0.0.0 \
  --port 30000 \
  --tensor-parallel-size 1 \
  --trust-remote-code \
  --mem-fraction-static 0.85
