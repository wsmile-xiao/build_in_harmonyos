# tigr 3.1.0 适配笔记

## 编译环境
- 构建系统: makefile（单文件库，直接编译 amalgamated tigr.c）
- 编译日期: 2026-09-16
- 编译器: clang 15.0.4（OHOS aarch64，-DTIGR_HEADLESS）
- 状态: built

## 编译步骤

1. `init-build tigr 3.1.0 --url=https://codeload.github.com/erkkah/tigr/tar.gz/refs/tags/v3.1.0`（官方 tag archive）
2. ⚠️ init-build 嵌套源码检测误判：把含 Makefile 的 `ci/` 子目录提升为源码根（同 libbpf 案例）。手动重建 `tigr-3.1.0.orig` / `tigr-3.1.0.work` 为真实源码根（tigr.c/tigr.h/src/examples/ci），核对 `.tarball-sha256` = eef1a174214429bb22ce151c147614b83aca7a1043b56c8bb4584b83f985ca8e。
3. `conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64`：配方 `build()` 直接 `clang -DTIGR_HEADLESS -fPIC -O2 -c tigr.c` + `llvm-ar rcs libtigr.a`，test_package 消费者测试全绿（ALL 8 CHECKS PASSED）。
4. `ohc-run.py conan-verify tigr 3.1.0`：G1-G5 全 PASS。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | tigr.c 编译报 X11/X.h 找不到 | OHOS 无 X11/GLX 窗口后端；tigr 默认窗口后端按平台编译（linux→X11+GL） | 以官方 `TIGR_HEADLESS` 模式编译：剔除窗口/输入/GL 后端，保留纯 framebuffer 核心（绘图/文字/PNG/解压），全部实质实现，无 stub |
| 2 | conan create 报 BadZipFile | codeload 响应 Content-Type 为 application/zip，被 Conan get() 误判为 zip | source() 显式 `src["filename"]="tigr-3.1.0.tar.gz"` 强制按 tar.gz 解压 |
| 3 | `tools.build:compiler_executables:c` 读取失败 | 该 conf 为 dict，不是列表项 | `comp.get("c","clang")` 从 dict 取编译器（同 aa3d 等既有配方） |
| 4 | init-build 嵌套源码误判 | 根目录无构建标记、`ci/` 子目录含 Makefile（同 libbpf Sphinx 案例） | 手动重建 .orig/.work 为真实源码根，核对 tarball SHA-256 |

## 源码修改

无补丁。OHOS 适配完全通过编译期宏 `TIGR_HEADLESS` 完成（官方支持的模式，非自编 stub）。patch 文件为空，未做任何源码改动。

## 依赖版本

无外部依赖（单文件库，仅 libc/libm）。

## 验证结果

```bash
# 消费者测试（test_package，TIGR_HEADLESS）
./test_tigr    # ALL 8 CHECKS PASSED —— 位图/绘制/文字/PNG 读写全流程
# 上游 headless 冒烟样例（可运行入口）
./headless     # exit 0，产出 headless.png (320x240 RGBA)
# 上游 ci 测试程序（R03 已纳入 headless 运行，见下）
cd ci && ../ci_headless   # *** All tests pass OK (Create offscreen/Drawing API/Unicode)
```

## 上游测试枚举台账（双口径，R51+任务要求，R03 更新）

tigr 无独立测试框架（无 ctest/GTest/check），上游"测试"入口共两类：

### 源码声明口径（source_declared）

| 入口 | 类型 | 是否独立用例 | 构建/运行结果 | 原因 |
|------|------|------|------|------|
| ci/ci.c | 上游 massage 测试程序（399 行，30+ assert 子检查，遍历主要 API） | ✅ 独立上游用例（唯一用户测试源） | **R03：可运行且已运行 ✅** | R03 以最小补丁 `patches/0001-ci-headless-guard.patch`（#ifndef TIGR_HEADLESS 剔除窗口/GL/输入路径，保留 framebuffer 断言）经 conan create 实测：`Create offscreen...OK / Drawing API...OK / Unicode...OK / *** All tests pass OK`，exit 0 |
| src/Makefile | 源码打包脚本（bundle.pl 生成 amalgamated tigr.c） | ❌ 构建目标，非测试 | — | — |

**source_declared_total = 1**（ci/ci.c 独立上游用例，R03 不改写）；**configured_executable_total = 1**（R03 补丁后 ci.c headless 版在 OHOS 配置可实例化）；executed_passed_total = 1；全量通过率 **1/1 (100%)**。

### 样例/基准/框架文件（不误算独立用例，如实列出）

| 入口 | 类型 | 运行结果 | 原因 |
|------|------|----------|------|
| examples/headless/headless.c | 官方 headless 冒烟样例（TIGR_HEADLESS） | ✅ 实际运行 exit 0，产出 headless.png 320x240 RGBA 校验通过 | 无窗口依赖，OHOS 可运行 |
| examples/hello/hello.c | 样例（窗口型） | ❌ 不可编译 | X11/X.h not found（样例不计独立用例） |
| examples/clip/clip.c | 样例（窗口型） | ❌ 不可编译 | X11/X.h not found（样例不计独立用例） |
| examples/flags/flags.c | 样例（窗口型） | ❌ 不可编译 | X11/X.h not found（样例不计独立用例） |
| examples/opengl/opengl.c | 样例（GL 窗口型） | ❌ 不可编译 | X11/X.h not found（样例不计独立用例） |
| examples/shader/shader.c | 样例（GL 窗口型） | ❌ 不可编译 | X11/X.h not found（样例不计独立用例） |
| examples/demo/demo.cpp | 样例（C++ 窗口型，附 greeting.txt/squinkle.png 素材） | ❌ 不可编译 | 源码为 demo.cpp 非 demo.c + X11/GL 依赖 |
| tigr.h / tigr.c / src/*.c | 库框架源码（非测试） | — | — |
| ci/5x7.png ch.png reference.png | 测试参考图片素材 | — | 仅素材 |

### 双口径汇总（R03 更新后）

- 源码声明总数 `source_declared_total`：**1**（ci/ci.c，官方 tag 源码唯一独立上游用例）
- 当前配置可执行数 `configured_executable_total`：**1**（R03 补丁后 ci.c headless 版）
- 实际执行并通过 `executed_passed_total`：**1**
- 未运行/未实例化：**0**
- 全量通过率：**1/1 (100%)**
- 当前配置可执行集合通过率：**1/1 (100%)**
- 另计（不计独立用例）：headless 冒烟样例 1/1、消费者 test_tigr 15/15、鸿蒙专项 test_tigr_ohos 13/13

说明：R03 前 ci/ci.c 因 X11/GLX 窗口后端平台阻塞（`X11/X.h not found`）不可实例化；
R03 按用户选定路径 B 以最小补丁将窗口/GL/输入路径 guard 在 `#ifndef TIGR_HEADLESS`
内（补丁前后 SHA-256：900514f45b0a3effb263d57b58dd458048dacaa9151fffe1d144b24ebc7437c9 →
f32b8b3dbacbbf1fbac1d199fb5bb08245156e2beacaa1c4304fdb0b2fd5e8df），保留断言语义，
纳入配方 build() 测试目标并经 conan create 实测通过；双口径分母与分子均按真实结果如实更新。

## 交付物

| 文件 | 说明 |
|------|------|
| archives/t/tigr/3.1.0/conanfile.py | Conan 配方（TIGR_HEADLESS 静态库） |
| archives/t/tigr/3.1.0/conandata.yml | 官方源 + SHA-256 |
| archives/t/tigr/3.1.0/manifest.yaml | 版本清单 |
| archives/t/tigr/3.1.0/test_package/ | 消费者测试（8 项断言全 PASS） |

## 注意事项

- 窗口/输入/GL 后端 API（tigrWindow/tigrUpdate/tigrEvents 等）在 TIGR_HEADLESS 下不可用，属上游官方设计；消费者按 headless 模式使用离屏位图。
- conan-verify 的 E017 镜像注入会临时改写 conandata.yml 并已自动恢复；提交前检查无 `.ghfast-bak`/`.orig` 残留。
---

**编译结束**: 2026-09-17 09:37
**最终状态**: built
