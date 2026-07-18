#! /bin/bash
# VNC step 2 — launch tightvncserver as the non-root user.
set -e
tightvncserver :1 -geometry 1024x768 -depth 24
