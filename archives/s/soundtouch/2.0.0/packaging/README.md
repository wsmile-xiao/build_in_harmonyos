# Packaging — soundtouch 2.0.0

打包说明：本包为纯 Conan 交付（conan create 产物），无独立打包产物。
制品经 CI release 流水线上传至 CNB 制品仓（conan.cnb.cool）。

- 库：lib/libSoundTouch.so.1.0.0（+ .so/.so.1 链接）
- CLI：bin/soundstretch（commands.json 已声明）
- 头文件：include/soundtouch/*.h
- pkg-config：lib/pkgconfig/soundtouch.pc
