#!/bin/sh
# Generic profile drop-in: clear the selinux shim's LD_PRELOAD interference,
# export sane PATH + home. We only clear LD_LIBRARY_PATH if it is empty/our own
# shim residue, so we never break native binaries that legitimately need it.
unset LD_PRELOAD
case "${LD_LIBRARY_PATH:-}" in
  ""|*/support/*) unset LD_LIBRARY_PATH ;;
esac
export LIBGL_ALWAYS_SOFTWARE=1
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/usr/games:/usr/local/games
export SOVEREIGN_ULA=1
[ -r /support/sovereign-motd.sh ] && . /support/sovereign-motd.sh
