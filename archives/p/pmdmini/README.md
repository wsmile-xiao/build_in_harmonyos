# pmdmini - PMD/MDX 音乐播放库

## 简介
pmdmini 是播放 PMD/MDX（NEC PC-98 时代 FM 音源）格式音乐的 C 库，
内嵌 fmgen（FM 音源模拟）、pmdwin（PMD 驱动）、ppz8（PCM 驱动）源码，
对外提供 `pmdmini.h` 中的 C API（`pmd_init` / `pmd_setrate` / `pmd_is_pmd` / `pmd_stop` 等）。

## OHOS 适配
- 构建系统：原生 Makefile（无 configure/CMake），使用 `Makefile.lib` 只编译核心静态库
- 无外部依赖：fmgen / pmdwin / ppz8 均为内嵌 (vendored) 源码；示例播放器 `pmdplay` 需要
  SDL2（`sdl2-config`），配方**不打包播放器**，故不声明依赖
- 上游为 C++03 时代代码：clang 默认 C++17 下 `src/fmgen/psg.cpp:121` 的 `-1` 窄化到
  `uint8` 触发 `-Wc++11-narrowing`，C++ 对象需用 `-std=c++03` 编译
- 交付产物：`lib/libpmdmini.a`（OHOS aarch64 静态库）+ `include/pmdmini.h`
- 上游无自动化测试套件（Makefile 仅 `all`/`clean`，无 `check`/`test` 目标），
  `test_package/test.cpp` 自建消费者 API 冒烟测试（1 个可执行文件，3 项断言）

## 功能
- 播放 PMD/MDX 格式音乐（PC-98 FM 音源）
- 内嵌 FM 音源模拟（fmgen）、PMD 驱动（pmdwin）、PCM 驱动（ppz8）
- 提供渲染到 PCM 缓冲区的 C API，便于集成到其他音频后端

## 依赖关系
```
pmdmini/2.0.0 (makefile, C/C++03)
└─ 无外部依赖（fmgen/pmdwin/ppz8 内嵌；播放器 pmdplay 的 SDL2 不在打包范围内）
```

## 参考资料
- 上游仓库：https://github.com/mistydemeo/pmdmini
- 源码包：https://github.com/mistydemeo/pmdmini/archive/refs/tags/v2.0.0.tar.gz
- 适配记录：`2.0.0/notes.md`

## 许可证
GPL-2.0-or-later
