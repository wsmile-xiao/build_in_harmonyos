# pmdmini 2.0.0 适配笔记

## 编译环境
- 构建系统: makefile（纯 Makefile，无 configure/CMake）
- 编译日期: 2026-09-04
- 编译器: clang/clang++ (OHOS aarch64, clang 15.0.4)
- 状态: built

## 编译步骤

核心库（仅打包静态库，不打包播放器）：

```bash
make -f Makefile.lib CC=clang CXX="clang++ -std=c++03" \
    AR=llvm-ar RANLIB=llvm-ranlib CFLAGS="-fPIC -O2" -j1
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `src/fmgen/psg.cpp:121` 报 `-Wc++11-narrowing` 错误：`-1` 无法窄化到 `uint8` | 源码为 C++03 时代代码，clang 默认 C++17 下 list-initialization 窄化为编译错误 | C++ 文件用 `-std=c++03` 编译（对齐 Homebrew 配方的 `CXX="... -std=c++03"`） |
| 2 | conan `self.conf.get("tools.build:compiler_executables:c")` 报 conf 不存在 | conan 2.29.1 不支持 `:c` 子键访问，需整体取 dict | 改为 `self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)` 后 `.get("c")` |
| 3 | `make -f Makefile.lib` 报 `No such file or directory` | `basic_layout` 下 build() 运行在 build 目录，源码在 source 目录 | `self.run(..., cwd=self.source_folder)` |

## 源码修改

无补丁。上游代码无需修改即可在 OHOS aarch64 编译（仅需 `-std=c++03` 编译标志）。

## 依赖版本

核心库 `libpmdmini.a` 无外部依赖。fmgen / pmdwin / ppz8 均为内嵌 (vendored) 源码。
播放器 `pmdplay` 需要 SDL2（sdl2-config），但配方不打包播放器，故不声明依赖。

## 验证结果

```bash
python3 scripts/ohc-run.py conan-verify pmdmini 2.0.0
# 结果: PASS (G1/G2/G3/G4 通过)
# test_package: "pmdmini API smoke test: OK"
```

## 交付物

| 文件 | 说明 |
|------|------|
| libpmdmini.a | 静态库（aarch64） |
| pmdmini.h | 公共 C API 头文件 |

## 注意事项

- 上游无自动化测试套件（Makefile 仅 all/clean，无 check/test 目标）。
  唯一"测试入口"为示例播放器 pmdplay，依赖 SDL2 音频与 PMD 音乐文件，无法无头自动化。
- `src/pmdwin/util.cpp` 含 Shift-JIS 字体表字符串字面量（`-Winvalid-source-encoding` 警告，无害）。
- 版本号策略：首次适配用上游版本 2.0.0。
---

**编译结束**: 2026-09-04 15:05
**最终状态**: built
