#!/usr/bin/env bash
# env-toolchain.sh — wire the rootless Android/Java toolchain into PATH.
# Source me:  source /home/spiralgang/toolchain/env-toolchain.sh
ROOTFS=/home/spiralgang/toolchain/rootfs
JH="$ROOTFS/usr/lib/jvm/java-17-openjdk-arm64"
export JAVA_HOME="$JH"
export PATH="$JH/bin:$ROOTFS/usr/bin:$ROOTFS/usr/lib/android-sdk/build-tools/debian:$PATH"
export APKTOOL_JAR=/home/spiralgang/toolchain/apktool.jar
export ANDROID_SDK_ROOT="$ROOTFS/usr/lib/android-sdk"
# aapt + its shared lib live under the multiarch dir
export LD_LIBRARY_PATH="$ROOTFS/usr/lib/aarch64-linux-gnu/android:$ROOTFS/usr/lib/aarch64-linux-gnu:$LD_LIBRARY_PATH"
# relocated JAVA_HOME needs the security file pointed at explicitly
export JAVA_TOOL_OPTIONS="-Djava.security.properties=$JH/conf/security/java.security"
echo "toolchain env loaded:"
echo "  JAVA_HOME=$JAVA_HOME"
echo "  apktool=$APKTOOL_JAR"
command -v java >/dev/null && echo "  java: $(java -version 2>&1 | head -1)"
command -v aapt >/dev/null && echo "  aapt: $(aapt version 2>&1 | head -1 | cut -c1-50)"
command -v keytool >/dev/null && echo "  keytool: present"
command -v jarsigner >/dev/null && echo "  jarsigner: present"
command -v apksigner >/dev/null && echo "  apksigner(wrapper): present"
