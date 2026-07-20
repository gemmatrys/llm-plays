#!/usr/bin/env bash
# One-time root setup for the llm-plays inference server (Arc Pro B70).
# Installs GPU userspace sanity tools, Docker, and pulls Intel's vLLM image.
set -euxo pipefail

apt-get update
apt-get install -y intel-opencl-icd clinfo docker.io curl

# GPU + container access for the daily-driver user
usermod -aG docker,render chuxiong

systemctl enable --now docker

# model storage
mkdir -p /opt/models
chown chuxiong:chuxiong /opt/models

# Intel's Arc Pro B-series vLLM container (see github.com/intel/llm-scaler)
docker pull intel/llm-scaler-vllm:latest || \
  echo "WARN: pull failed - check current tag at github.com/intel/llm-scaler"

# sanity: the B70 should appear as an OpenCL device
clinfo | grep -E "Platform Name|Device Name" | sort -u || true

echo "SETUP DONE - log out and back in for docker/render group membership"
