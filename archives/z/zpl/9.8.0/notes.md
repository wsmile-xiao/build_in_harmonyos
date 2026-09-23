# zpl 9.8.0 — 源码审计 notes

## 官方来源
- 上游仓库: https://github.com/zpl-c/zpl
- 官方 tag: `v9.8.0`（轻量 tag，直接指向 commit `2fccef82b87d32f87bc9afea0354baa36fb21dca`，经 GitHub refs API 核验）
- 源码包: `https://github.com/zpl-c/zpl/archive/refs/tags/v9.8.0.tar.gz`
- SHA-256: `1ede9c7a13079470dad09c6ed9376365c6389b4a6c82de24bd5389d5aa5fa7de`
  （canonical codeload 通道实测两次一致；api.github.com tarball 端点 gzip 字节不同但解包内容逐文件一致）

## 库形态
- 单头文件库（stb 式）：消费方在唯一源文件中先 `#define ZPL_IMPLEMENTATION` 再 `#include "zpl.h"`。
- 官方 tag 自带聚合后的 `code/zpl.h`（约 18K 行），无需运行 `code/zpl/build.py` 重新生成。
- 可选模块头：`code/zpl_math.h`（要求先包含 zpl.h）、`code/zpl_image.h`。
- `ZPL_OPENGL` 相关代码依赖 vendored `stb_image.h`/`stb_rect_pack.h`/`stb_truetype.h` 与生成头 `zpl_glgen.h`，默认不启用。
- 许可证：双许可 Unlicense OR Apache-2.0（LICENSE 文件）。

## 构建形态判断
- header-only，无编译产物 → Conan `package_type = "header-library"`，`package_id` 清空。
- 打包 `code/zpl.h` + 可选模块头到 `include/`，LICENSE 到 `licenses/`。

## 上游测试入口（test/ 目录）
- `test/` 下为独立可执行测试程序（各自 `#define ZPL_IMPLEMENTATION` + 自含 `main`），
  覆盖 base64、json、hashtable、regex、ring、stack、coroutines、event、jobs、timers、when、
  dirlist、env、opts、radix、list 等模块；另有 `build-test.c`（C 编译冒烟）与
  `build-test.cpp`、`strdup.cc`（C++ 冒烟）、`imgui.cc`（依赖 OpenGL，预期不可在无 GPU 环境运行）。
- 详细枚举与运行结果见 Adaptation 阶段双口径台账（test/ 全量清点）。

## 依赖
- 无外部依赖（纯标准 C 库；仅在 Windows 分支使用 windows.h，OHOS/Linux 分支为 POSIX）。
---

**编译结束**: 2026-09-18 01:08
**最终状态**: built
