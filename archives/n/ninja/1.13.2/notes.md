# ninja 1.13.2 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-22
- 编译器: clang/clang++ 15.0.4（/data/service/hnp/bin，OHOS PC aarch64）
- 状态: built（conan create 通过；测试门禁见下）
- Conan profile: ci/conan/profiles/ohos-aarch64（os=OHOS, armv8, clang15, cppstd17）

## 编译步骤

```bash
# 1. 源码（官方 tag v1.13.2）
#    https://github.com/ninja-build/ninja/archive/refs/tags/v1.13.2.tar.gz
#    sha256 = 974d6b2f4eeefa25625d34da3cb36bdcebe7fbce40f4c16ac0835fd1c0cbae17
#    （与官方重新下载比对一致）

# 2. 本地 CMake 构建（测试运行用；GTest 来自 conan 本地 OHOS 包）
cmake -S . -B build \
  -DCMAKE_BUILD_TYPE=Release \
  -DBUILD_TESTING=ON \
  -DNINJA_FORCE_PSELECT=ON \
  -DGTest_DIR=<conan gtest/1.17.0 OHOS 包>/lib/cmake/GTest \
  -DCMAKE_CXX_COMPILER=/data/service/hnp/bin/clang++
cmake --build build --target ninja_test -j2
./build/ninja_test

# 3. Conan 配方验证（含 test_package 消费者）
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游测试运行循环刷 "ninja: ppoll: Out of memory" | OHOS 内核 ppoll() 运行时返回 ENOMEM（toybox/bionic poll 限制） | CMake 加 `-DNINJA_FORCE_PSELECT=ON` 强制 pselect() 路径（上游提供该开关） |
| 2 | status_test.cc 无法编译（BuildConfig incomplete type / StatusPrinter unknown） | 上游遗漏：该测试文件未被任何构建目标接入，且缺 `status_printer.h`/`build.h` include | 最小补丁 0001：纳入 ninja_test 目标 + 补 include（源码测试入口恢复规则） |
| 3 | 上游测试依赖 GTest（FetchContent 从 GitHub 下载 googletest） | GitHub 不可达 | 配方 `test_requires gtest/1.17.0`（ohpcd 制品仓有 OHOS 包），`generate()` 里 `GTest_DIR` 指向 conan 包内 GTestConfig.cmake |
| 4 | Jobserver.PosixFifoClient 失败（mknod EPERM） | OHOS HMDFS 不支持 FIFO inode；/dev/shm 等 tmpfs 亦 EACCES | 真实平台阻塞，见 reports/upstream-test-ledger.md 3.1，恢复条件：提供支持 mknod/FIFO 的挂载点 |
| 5 | SubprocessTest.InterruptChildWithSigHup 失败（130 vs 129） | OHOS /bin/sh 对 SIGHUP 以 WIFEXITED(128+1)=129 退出，而非被信号杀死 | 真实平台 shell 语义差异，见台账 3.2 |
| 6 | SubprocessTest.SetWithSingle/Multi 失败（`ls /` exit 1） | 设备根目录 drwx--x--x root，非 root 用户无读权限；`id` 不在 PATH | 真实平台权限条件，见台账 3.3/3.4 |

## 源码修改

- 补丁：`patches/0001-include-status-test-in-target.patch`
  - CMakeLists.txt：ninja_test 目标追加 `src/status_test.cc`
  - src/status_test.cc：追加 `#include "status_printer.h"` / `#include "build.h"`

## 依赖版本

- gtest/1.17.0（ohpcd 制品仓，OHOS armv8 clang15 包，conan 本地缓存）
- 无第三方运行依赖

## 验证结果

```bash
# C++ 上游测试（GTest）：411 注册 / 407 通过 / 4 平台阻塞
#   - 通过率：407/433 全量口径 94.0%；407/411 当前配置可执行口径 99.0%
#   - 4 个失败全部为真实平台/权限/工具条件（台账逐项证据）
# Python 测试：49 运行 / 27 通过（output/jobserver 组受 script/FIFO 平台限制）
# 双口径台账：reports/upstream-test-ledger.md

# 鸿蒙专项测试（test_package/hello_ohos.c）：
#   ninja 驱动 OHOS clang 编译 C 程序并运行产物，输出 ohos-ninja-consumer-ok:3（退出码 0）

# conan create：通过（含 test_package 消费者验证）
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | CMake 配方（application，pselect 强制 + GTest 本地化） |
| conandata.yml | 官方源 + sha256 + 补丁声明 |
| test_package/ | 消费者测试（MANIFEST.yml + conanfile.py + hello_ohos.c） |
| patches/0001-*.patch | status_test 纳入补丁 |
| reports/upstream-test-ledger.md | 双口径测试台账 |
| reports/ohos-spec-test.md | 鸿蒙专项测试证据 |

## 注意事项

- 高难度挑战上游测试硬门禁未满足（407/433，4 个真实平台阻塞）：按任务规则禁止 commit/push/PR，最终回报真实阻塞事实与恢复条件（详见台账第五节约束）
---

**编译结束**: 2026-09-22 18:59
**最终状态**: built
