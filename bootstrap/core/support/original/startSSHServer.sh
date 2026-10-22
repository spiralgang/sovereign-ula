#! /bin/bash
# ORIGINAL CypherpunkArmory/UserLAnd dropbear start (SOURCE OF TRUTH fallback).
# Kept verbatim from the known-working upstream build. Our evolved
# startSSHServer.sh wraps this and only falls back to the device-anchored SSH
# (ssh-anchor.sh) if THIS fails. Do not "improve" this file — it is the
# reference everything else is evolved past.
set -e
if [ ! -f /support/.ssh_setup_complete ]; then
    rm -rf /etc/dropbear
    mkdir /etc/dropbear
    dropbearkey -t dss -s 1024 -f /etc/dropbear/dropbear_dss_host_key
    dropbearkey -t rsa -s 2048 -f /etc/dropbear/dropbear_rsa_host_key
    dropbearkey -t ecdsa -s 521 -f /etc/dropbear/dropbear_ecdsa_host_key
    touch /support/.ssh_setup_complete
fi
dropbear -E -p 2022
