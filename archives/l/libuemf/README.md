# libUEMF

libUEMF（libuemf）是 David Mathog 编写的可移植纯 C99 库，用于读取、生成与打印
EMF（Enhanced Metafile）、EMF+（PMF）与 WMF（Windows Metafile）元文件，
GPL-2.0-or-later 许可。上游地址：https://github.com/mathog/libUEMF 。

## OHOS 适配版本

- [0.2.8](./0.2.8/)：CMake 构建；共享库 libuemf + 10 个公共头文件 +
  8 个命令行工具（reademf、readwmf、cutemf、pmfdual2single 与 4 个 testbed）。
  适配要点：CMake 4 兼容（cmake_minimum_required 3.0→3.5）、打包前缀与
  BUILD_SHARED_LIBS 由 Conan 控制、上游 testit.sh 参考比对在配方 build() 内
  等价复现（16 项）。详见 0.2.8/notes.md。
