#! /bin/bash
# Start the XSDL X server bridge (universal support service).
set -e
if [[ -z "${INITIAL_USERNAME}" ]]; then INITIAL_USERNAME="user"; fi
su "$INITIAL_USERNAME" -c /support/startXSDLServerStep2.sh
