# bitmagic

> BitMagic — C++ library for compact bit vectors, sparse vectors, and integer sets

## 基本信息

| 项 | 值 |
|---|---|
| 软件名 | bitmagic |
| 上游 | https://github.com/tlk00/BitMagic |
| 主页 | https://github.com/tlk00/BitMagic |
| 许可证 | Apache-2.0 OR MIT |
| 类型 | C++ header-only library |
| 构建系统 | CMake (INTERFACE library) |

## 已适配版本

| 版本 | 状态 | 适配日期 | 说明 |
|------|------|---------|------|
| 9.3.2 | built | 2026-09-30 | 首次适配，header-only 配方 |

## 依赖

- pthread（可选，启用 `with_threads=True` 时链接）
- C++17 编译器（clang/gcc）

## 已知限制

- 上游 CMakeLists.txt 没写 `install()` 规则，依赖手工 copy 头文件
- x86 优化宏（`BMSSE42OPT` / `BMAVX2OPT`）需下游自己定义，本配方默认不开启

## 相关文档

- [notes.md](9.3.2/notes.md) — 适配笔记
- [conanfile.py](9.3.2/conanfile.py)
- [test_package/](9.3.2/test_package/)