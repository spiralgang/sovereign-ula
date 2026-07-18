#! /bin/bash
# Create the non-root user (universal — identical for every deployed distro).
set -e
if [[ -z "${INITIAL_USERNAME}" ]]; then INITIAL_USERNAME="user"; fi
if [[ -z "${INITIAL_PASSWORD}" ]]; then INITIAL_PASSWORD="userland"; fi
if [[ -z "${INITIAL_VNC_PASSWORD}" ]]; then INITIAL_VNC_PASSWORD="userland"; fi

if [ ! -d "/home/$INITIAL_USERNAME" ]; then
  useradd "$INITIAL_USERNAME" -s /bin/bash -m -u 2000
  echo "$INITIAL_USERNAME:$INITIAL_PASSWORD" | chpasswd
  chsh -s /bin/bash "$INITIAL_USERNAME"
  echo "$INITIAL_USERNAME ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/sovereign-user
  chmod 440 /etc/sudoers.d/sovereign-user
fi
