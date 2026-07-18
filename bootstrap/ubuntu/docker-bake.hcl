# docker-bake.hcl — build all arches of the Noble rootfs at once.
variable "ARCH" { default = "arm64" }

target "rootfs" {
  context = "."
  dockerfile = "Dockerfile"
  platforms = ["linux/arm64", "linux/arm/v7", "linux/amd64", "linux/386"]
  args = {
    IMAGE_ARCH = "arm64v8"
    IMAGE_DISTRO = "ubuntu"
    IMAGE_VERSION = "noble"
    IMAGE_PLATFORM = "linux/arm64"
    QEMU_FILE = "qemu-aarch64-static"
  }
  output = ["type=local,dest=./output"]
}
