#!/support/busybox sh
# Extract the chosen distro's rootfs into the prepared chroot env.
# Called by tech.ula as /support/common/extractFilesystem.sh.
# The base chroot env (proot + universal support layer) is already present;
# this overlays the distro's rootfs on top of it.
set -e

if [ ! -f /support/rootfs.tar.gz ]; then
   cat /support/rootfs.tar.gz.part* > /support/rootfs.tar.gz
   rm -f /support/rootfs.tar.gz.part*
fi

/support/busybox tar -xzvf /support/rootfs.tar.gz -C /

if [ $? -eq 0 ]; then
    /support/addNonRootUser.sh
    # wire the glibc/termuxvoid translation layer (universal add-on)
    [ -x /support/termuxvoid-shim.sh ] && /support/termuxvoid-shim.sh install || true
    touch /support/.success_filesystem_extraction
    rm -f /support/rootfs.tar.gz
else
    touch /support/.failure_filesystem_extraction
fi
