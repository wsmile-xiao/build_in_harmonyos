# hedley 15 — OHOS 适配笔记

## 结论
- 单头文件 C/C++ 宏库（编译器属性/诊断的可移植封装），零依赖、零源码编译。
- header-only：`package()` 仅安装 `hedley.h` 到 include/，`COPYING`（CC0）到 licenses/。
- 零补丁（无需任何平台源码修改）。

## 上游测试执行
- 上游**无运行时测试框架**（无 TEST_CASE/add_test）。`test/Makefile` 的 `make all`
  把 35 个编译检查源（`test/*.c`）逐个编译：先按 C，再把每个 `.c` 复制为 `.cpp` 按 C++，
  通过 = 干净编译（验证每个 hedley 宏在目标编译器上展开为合法代码）。
- `build()` 完整复现该口径：35 C + 35 C++ = **70 个编译检查全过（70/70）**，
  并真实执行全部 70 个产物二进制。
- 其中 **24 个二进制按设计返回计算值**（如 `require.c` 的 main 返回 `add(2,3)=5`、
  `deprecated.c` 返回 `cube(7)=217`），上游从不运行这些二进制——故非零退出为信息性，
  不作为失败判定。实测：46 个退出码 0，24 个非零（全部属上述"返回计算值"设计）。
- 与上游 `Makefile` 的差异：上游用 `-Weverything -Werror`（clang）/`-Wall -Wextra -Werror`（gcc）。
  OHOS clang 15 更严格，会在 7 个**故意触发警告**的测试（message、non-null、printf-format、
  sentinel、unused-function、unreachable、warn-unused-result）上把警告升级为硬错误，
  另在 unused-function 上触发 `-Wmissing-prototypes`。故 `build()` 用 `-std=c11` / `-std=c++17`
  且不带 `-Werror` 编译——编译与执行的都是未经修改的上游真实源码。

## test_package
- test.c 共 10 个 CHECK，真实调用 hedley 宏 API：HEDLEY_VERSION、版本 encode/decode、
  HEDLEY_LIKELY/UNLIKELY、HEDLEY_CONST/PURE 函数、HEDLEY_STATIC_CAST、HEDLEY_CONCAT、
  HEDLEY_STRINGIFY、HEDLEY_DIAGNOSTIC_PUSH/POP。

## 版本对齐
- 任务 #5384 = conan 15 = 分支 feat/hedley-15 = 目录 archives/h/hedley/15。
- 上游 GitHub tag `v15`（`HEDLEY_VERSION == 15`）。

---
**编译结束**: 2026-09-02 02:30
**最终状态**: built
