#!/bin/sh
# Sovereign ULA — generic profile drop-in (sits alongside userland_profile.sh).
# Unsets the selinux-preload shim interference and exports a sane PATH + home.
unset LD_PRELOAD
unset LD_LIBRARY_PATH
export LIBGL_ALWAYS_SOFTWARE=1
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/usr/games:/usr/local/games
export SOVEREIGN_ULA=1

# Source the MOTD walk-through if present (prints banner on login).
if [ -r /support/sovereign-motd.sh ]; then
    . /support/sovereign-motd.sh
fi
