# rc_ptr 0.0.2 适配笔记

## 编译环境
- 构建系统: cmake（上游根 CMakeLists 为 INTERFACE 目标，header-only；测试面 `RC_PTR_BUILD_TESTS=ON`）
- 编译日期: 2026-09-29
- 编译器: clang/clang++ 15.0.4（aarch64-unknown-linux-ohos）
- Conan profile: `ci/conan/profiles/ohos-aarch64`（os=OHOS, arch=armv8, cppstd=17）
- 状态: built

## 编译步骤

rc_ptr 是 **header-only** C++17 单线程引用计数智能指针（`memory::rc_ptr` / `weak_rc_ptr` /
`enable_rc_from_this` / `make_rc`），上游根 CMakeLists 只定义 INTERFACE 目标，**无编译产物**，
Conan 配方按 header-only 形态交付头文件：

1. **源核验**：官方 tag `v0.0.2` 归档
   `https://github.com/Chylynsky/rc_ptr/archive/refs/tags/v0.0.2.tar.gz`，
   设备实测 sha256 = `4682e0235b6def843b52e9327c7f1f87c98998b58c1b39a27cbf13dae27f7977`
   （42131 字节），与 conan-center-index `recipes/rc_ptr/all/conandata.yml` 的 `0.0.2` 条目逐字一致；
   `git ls-remote --tags` 上游 2 个 tag（v0.0.1 / v0.0.2）全量命中，`v0.0.2` → `82234b415df9aaf31668fddf6713ca0967d3c14f`。
2. **配方**（`conan-init` 生成骨架后按 header-only 形态重写）：
   - `package_type="header-library"`、`no_copy_source=True`、`package_id()` 清空；
   - `source()` 下载主源 + 测试框架第二源（Catch2 v2.13.7 → `_deps/catch2-src`）；
   - `generate()` 注入 `RC_PTR_BUILD_TESTS=ON` 与 `FETCHCONTENT_SOURCE_DIR_CATCH2`（构建期零网络）；
   - `build()` 内**真实执行上游测试**（configure → 构建 `rc_ptr-test` → 运行 → 解析 Catch2 摘要并硬校验计数）；
   - `package()` 只 `copy` `include/**/*.hpp` → `include/`（保持 `rc_ptr/rc_ptr.hpp` 相对路径）与
     `LICENSE_1_0.txt` → `licenses/`；`package_info()` 清空 `bindirs/libdirs`，声明
     `cmake_file_name=rc_ptr` / `cmake_target_name=rc_ptr::rc_ptr`。
3. **验证**：`conan create`（ohos-aarch64 profile，含 test_package 消费者测试）
   与独立沙箱 HOME 下的上游测试复跑，读数见 `reports/`（工作区证据，不入库）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `task_init` 报 `archives/r/rc_ptr 在 upstream/main 不存在` | 全新包（conan-center-index 收录、本仓库尚未归档） | `task_init.sh --allow-unpublished` 放行并在终报注明 |
| 2 | 上游测试框架用 `FetchContent` git clone（`github.com/catchorg/Catch2.git` tag `v2.13.7`） | CI worker 的 git 协议不通 GitHub；构建期联网不可接受 | Catch2 官方 tag tarball 作为 `conandata.yml` 第二源（sha256 `3cdb4138a072e4c0290034fe22d9f0a80d3bcfb8d7a8a5c49ad75d3a5da24fae`，661014 字节），`source()` 预置到 `_deps/catch2-src` + `FETCHCONTENT_SOURCE_DIR_CATCH2` 指向本地，**上游测试文件零改动、构建期零网络** |
| 3 | 源码 112 个 `TEST_CASE`，运行只注册 110 个 | `test/allocator.cpp` 的 2 个 pmr 用例在上游源码内以 `#if (__has_include(<memory_resource>))` 条件编译，OHOS SDK libc++ 无 `<memory_resource>`（探针：`__has_include` = 0；直接 include 报 `fatal error: 'memory_resource' file not found`） | **不改上游测试**：申报 N=112（源码宏 / 框架注册两口径取最大值 112）、N′=110、`NOT_RUN=2` 并写明技术原因与探针证据；配方对 110/305 与 112/311 两种工具链形态都硬校验，其余计数一律失败（反静默） |
| 4 | header-only 包在 conan-verify 的 G4/L2/L4/L5 走「跳过」分支却并列打印 ✅ | 包内无 `bin/`、无 `lib/*`，自动门禁结构性跳过（设备事实 §二.17） | 不采信并列 ✅，人工补测四面读数写 `reports/conan-verify-supplement.md` |
| 5 | 上游 09-28 合入的 10.77 MiB 附件提交使新分支推送被 fork pre-receive 钩子拒绝（单文件 10 MiB 上限） | `archives/c/clownresampler/3.24/tests-ref/test1.b64` 落在 `upstream/main` 历史内 | 推送前按 0928 判据扫描 `origin/main..<基线>`，命中即 `git rebase --onto e78e9458a upstream/main` 换基（分支未推过、非 force），换基后走 T3/H11 完整链 |

## 源码修改

无（header-only 库零补丁，`patches: []`、`patches_applied: []`；`test/` 与 `include/` 零改动）。

## 依赖版本

- 配方 `requires()` / `tool_requires()` = **0 个**（软件本体 0 依赖，仅依赖 C++17 标准库）。
- 测试面预置源：**Catch2 v2.13.7**（上游 FetchContent 固定 tag），只进 `conandata.yml` 的 `catch2:` 键，
  **不进依赖链**，对下游仍是 0 依赖。

## 验证结果

```bash
# W0 版本可得性 / sha 三路
git ls-remote --tags https://github.com/Chylynsky/rc_ptr.git        # 2 个 tag 全量命中
sha256sum rc_ptr-v0.0.2.tar.gz                                       # 4682e023…f7977（= CCI conandata = 任务卡）

# 上游测试（沙箱 HOME，上游 CI test-master.yml 同形态；2026-09-29 实测）
HOME="$TASK_DIR/test-home" cmake -S <src> -B <build> -DCMAKE_BUILD_TYPE=Debug \
  -DRC_PTR_BUILD_TESTS=ON -DFETCHCONTENT_SOURCE_DIR_CATCH2=<catch2-src>   # CONFIGURE_RC=0
HOME="$TASK_DIR/test-home" cmake --build <build> --target rc_ptr-test -j4  # BUILD_RC=0
HOME="$TASK_DIR/test-home" <build>/rc_ptr-test/rc_ptr-test                 # RUN_RC=0
#   → All tests passed (305 assertions in 110 test cases)
HOME="$TASK_DIR/test-home" <build>/rc_ptr-test/rc_ptr-test --list-tests    # 110 test cases
HOME="$TASK_DIR/test-home" ctest --test-dir <build>                        # 100% tests passed (1/1)

# 消费者测试（交付头 + memory:: 公共 API，18 条运行期断言）
clang++ -std=c++17 -I<include> test_package/test_rc_ptr.cpp && ./consumer-probe
#   → [consumer] TOTAL=18 FAIL=0（rc=0）

# Conan 完整验证（采信轮）
sh tools/conan_verify_round.sh rc_ptr 0.0.2 --repo "$TARGET_REPO" --task-dir "$TASK_DIR"
```

## 交付物

| 文件 | 说明 |
|------|------|
| `conanfile.py` | header-only Conan 配方（含 `build()` 内上游测试硬校验） |
| `conandata.yml` | 官方源 URL + SHA-256 + Catch2 测试面第二源 |
| `manifest.yaml` | 版本 manifest（四口径测试统计、状态 built） |
| `notes.md` | 本适配笔记 |
| `test_package/test_rc_ptr.cpp` | 消费者测试：18 条运行期断言 + 3 条 static_assert |
| `test_package/MANIFEST.yml` | 上游测试声明（N=112 / N′=110 / NOT_RUN=2 与四口径归因） |

## 注意事项

- **N 口径**：源码宏 112 ／ 框架注册 110 ／ 断言宏 307 ／ 断言执行 305 —— 四口径并列不混用，
  申报 N 取 case 级候选最大值 **112**，差额 2 已按条件编译逐项归因（NOT_RUN=2）。
- 上游 CI 还有一段 Valgrind 步骤：本设备 valgrind 触发 SIGSEGV 不投递（设备事实 §一.38），
  该步在设备侧不可执行，属环境限制，不写成 PASS。
- 包内无 `bin/`、无 `lib/`，conan-verify 的 L2/L4/L5 与 W3 的 L2/L5 属**预期跳过/warn**，
  已人工补测，读数在 `reports/` 下（工作区 ignored 证据）。
- 状态保持 `built`（未合并、未 release upload 前不得标 `published`，AGENTS O5）。
