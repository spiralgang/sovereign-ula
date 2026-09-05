#! /bin/bash
# Start the VNC server (universal support service).
set -e
if [[ -z "${INITIAL_USERNAME}" ]]; then INITIAL_USERNAME="user"; fi
if [ ! -f /support/.reconfigure_xfonts ]; then
   dpkg-reconfigure xfonts-base || true
   touch /support/.reconfigure_xfonts
fi
su "$INITIAL_USERNAME" -c /support/startVNCServerStep2.sh
