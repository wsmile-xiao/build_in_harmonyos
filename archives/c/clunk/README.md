# clunk

## 简介

clunk 是实时 3D（双耳）声音生成 C++ 库，基于 SDL 输出，支持任意数量混音通道。
上游：https://sourceforge.net/projects/clunk/

## OHOS 适配

- CMake 构建，SDL 1.2 API 由 `sdl12-compat/1.2.68` 提供。
- C++11 标准（源码含 C++17 已移除的 `throw()` 声明与 `std::auto_ptr`）。
- 上游无 CTest 套件；`test.cpp` 的 `f`/`t` DSP 自检模式在 `build()` 中真实运行。

## 依赖

- sdl12-compat 1.2.68

## 功能验证

```bash
conan create archives/c/clunk/1.3.261 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing
```

## 参考

- 源码：https://downloads.sourceforge.net/project/clunk/clunk-1.3.261.tar.bz2
