# libvdpau 1.5 packaging

Conan v3.0 流程：本目录不放置二进制 tarball（预编译制品由 Conan 制品仓
管理，见 conanfile.py），此处仅作目录占位与说明。

发布产物（conan create + release 流水线 conan upload）：
- `libvdpau/1.5` — lib/libvdpau.so{,.1,.1.0.0}（SONAME=libvdpau.so.1）、
  lib/vdpau/libvdpau_trace.so*（dlopen 追踪模块）、
  include/vdpau/{vdpau.h,vdpau_x11.h}、lib/pkgconfig/vdpau.pc、
  etc/vdpau_wrapper.cfg；全部 .so 已 binary-sign-tool 自签。
