# confu_json 1.2.4 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-22
- 编译器: clang/clang++ (LLVM 15.0.4, aarch64 OHOS)
- 状态: built
- 官方源: https://github.com/werto87/confu_json v1.2.4 (tar.gz SHA-256 adb87ecd8181f4ac4bb1eac0fbd9d803ce2f4c5bb7982b84b8a1aa95814228c5)

## 编译步骤
1. `ohc-run.py init-build confu_json 1.2.4 --url=https://github.com/werto87/confu_json/archive/refs/tags/v1.2.4.tar.gz`（OHC_PROJECT_DIR 指向本 worktree，归档落在 archives/c/confu_json/1.2.4）
2. 手工核验：manifest.yaml 修正 software/build_system=cmake/sha256；构建系统确认为 CMake（C++20 头文件 INTERFACE 库，confu_json/ 子目录 5 个头文件，无编译产物）
3. 库本体验证：`cmake -S . -B build -DBUILD_TESTS=OFF -DCMAKE_CXX_COMPILER=clang++ -DCMAKE_C_COMPILER=clang` → configure OK；`cmake --build build -j1` → OK（-j1 规避 HMDFS 不支持 make jobserver fifo）；`cmake --install build --prefix <TEST_PREFIX>` → 5 个头文件安装到 include/confu_json/
4. 依赖核对（W0/R35 conan download --only-recipe -r=ohpcd）：magic_enum/0.9.7 ✅、boost/1.90.0 ✅ 已发布；catch2/3.9.0 ❌（制品仓有 2.13.10/3.8.1/3.16.0，测试用）；durak/2.1.1@modern-durak ❌ 未发布（仅测试用）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 归档写入 SKILL_ROOT（全局安装）而非 worktree | find_project_dir() 默认向上找到 SKILL 安装目录 | 设 `OHC_PROJECT_DIR=<worktree>` 重跑；清理误写产物 |
| 2 | `make` 报 `jobserver mkfifo: Operation not permitted` | HMDFS 不支持 mkfifo，make 并行 jobserver 需 fifo | 构建统一用 `-j1` |
| 3 | `copy_compile_commands_json` 自定义目标使 `make` 失败 | 头文件库无编译规则，${CMAKE_BINARY_DIR}/compile_commands.json 不存在，无条件复制必然失败 | 改 CMakeLists.txt：`if (EXISTS ${CMAKE_BINARY_DIR}/compile_commands.json)` 守卫该目标；有真实编译规则时行为不变 |
| 4 | 上游 conanfile.py requires catch2/3.9.0 + durak/2.1.1@modern-durak | 制品仓无 3.9.0 与 durak（仅测试依赖） | 测试构建改用制品仓可用 catch2（3.8.1 或 3.16.0）；durak 依赖的用例按依赖缺口登记，最终回报前复查 |

## 源码修改
- CMakeLists.txt：compile_commands.json 复制目标加存在性守卫（见问题 3），其余上游源码未改

## 对话记录

### 对话 #1
- 2026-09-22 R02：init-build 建档（OHC_PROJECT_DIR 指向本 worktree）→ 库本体
  cmake 验证 → conan-init 生成配方并修正（头文件库、去除 catch2 包依赖）→
  conan-verify 全门禁通过 → 上游测试枚举/运行（47/49 通过，台账见
  reports/upstream-tests-ledger.md）→ OHOS 专项测试（ohos_test/，4 项检查通过）→
  refresh-patch 生成 6 补丁并注册 → finish（W2/W3 通过，最终态 built）
---

**编译结束**: 2026-09-22 14:17
**最终状态**: built
