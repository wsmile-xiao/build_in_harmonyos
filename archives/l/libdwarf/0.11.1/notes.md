# libdwarf 0.11.1 适配笔记（bootstrap 阶段）

## 状态：bootstrap（版本级骨架已建立，未进入 adapt/编译）

## 官方来源核验

- 官方仓库: https://github.com/davea42/libdwarf-code
- 正式发布: https://github.com/davea42/libdwarf-code/releases/tag/v0.11.1 (2024-12-02T17:29:45Z)
- tag v0.11.1 -> commit `909af3e46b68335df6c4a901ddd256ffa0d193d2`
  （annotated tag object c7b6535ce28850db00877c069af137cfa6ff5bf7，type=commit，PGP 签名）
- 源码 tarball: https://github.com/davea42/libdwarf-code/archive/refs/tags/v0.11.1.tar.gz
- SHA-256: `dfd24db87c354b3ba6fa72d29a481014f81768fea15ddcde96a8a938b1557c17`
  （从官方 tarball 直接计算，3,212,893 字节）
- tarball 根目录: `libdwarf-code-0.11.1/`
- CMakeLists.txt: `project(libdwarf VERSION 0.11.1)`，与 tag 一致
- 构建系统：CMake（另有 configure.ac autotools、meson.build 可选）

## 基线既有适配（参考）

- 仓库基线 origin/main 已含 libdwarf 2.1.0 published 配方（archives/l/libdwarf/2.1.0/），
  采用 CMake + zlib/1.3.1 + zstd/1.5.6，静态包定义 LIBDWARF_STATIC=1。
- 0.11.1 为历史版本，独立归档目录，不覆盖 2.1.0。

## 适配规划（待 adapt 阶段）

- CMake 构建；确认 OHOS aarch64 下 clang 编译与端序支持
- 依赖核对：2.1.0 依赖 zlib/zstd；0.11.1 需在 adapt 阶段确认（Gentoo ebuild 亦声明 zstd/zlib）
- 系统同名库（libdwarf）按 R26 静态库方案；工具二进制（dwarfdump 等）按 R38 判断 commands.json

## 待办（下一阶段）

1. 运行 `ohc-run.py conan-verify libdwarf 0.11.1`（8 道门禁）
2. 编写 test_package 消费示例（真实调用 dwarf_* API，R34）
3. 按结果推进 finish / 提交
---

**编译结束**: 2026-08-31 22:59
**最终状态**: built
