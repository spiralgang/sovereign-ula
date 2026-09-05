#!/support/busybox sh
# Compress the running filesystem back into a rootfs tarball (backup/export).
# Called by tech.ula as /support/common/compressFilesystem.sh.
set -e
TAR_PATH="${TAR_PATH:-/sdcard/sovereign-backup.tar.gz}"
/support/busybox tar -czvf "$TAR_PATH" \
    --exclude sys --exclude dev --exclude proc \
    --exclude mnt --exclude support/rootfs.tar.gz \
    /
touch /support/.success_filesystem_compression
