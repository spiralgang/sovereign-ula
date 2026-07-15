#!/bin/sh
# Generic profile drop-in: unset selinux shim interference, export sane PATH + home.
unset LD_PRELOAD
unset LD_LIBRARY_PATH
export LIBGL_ALWAYS_SOFTWARE=1
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/usr/games:/usr/local/games
export SOVEREIGN_ULA=1
[ -r /support/sovereign-motd.sh ] && . /support/sovereign-motd.sh
