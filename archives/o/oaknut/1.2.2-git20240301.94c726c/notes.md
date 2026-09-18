# oaknut 1.2.2-git20240301.94c726c 适配笔记

## 基本信息
- **上游**: https://github.com/merryhime/oaknut（commit 94c726ce0338b054eb8cb5ea91de8fe6c19f4392，2024-03-01，message "oaknut: Add PAUTH instructions"）
- **版本**: 1.2.2-git20240301.94c726c（对应 Debian `1.2.2+git20240301.94c726c-2` 快照）
- **许可证**: MIT（Copyright (c) 2022 merryhime）
- **类型**: header-only C++20 库（CMake INTERFACE library）
- **定位**: AArch64 (ARMv8.0~8.3) 汇编器/代码发射器，被 dynarmic 等 JIT 项目使用

## W0 依赖结论
- **运行时依赖**: 无（纯 header-only，仅 C++20 头文件）
- **构建依赖**: CMake >= 3.8、C++20 编译器（clang 15 满足）
- **测试依赖**: Catch2 3（上游 `find_package(Catch2 3 REQUIRED)` + `<catch2/catch_test_macros.hpp>`）
  - **本仓库仅有 catch2/2.13.10-r0（v2），与 v3 API 不兼容 → 测试依赖缺失**
- **是否需要拆分依赖适配**: 否。Catch2 3 是纯测试依赖，header-only 库消费者不依赖它；
  配方 `BUILD_TESTING=OFF` 跳过上游 Catch2 测试，test_package 以确定性指令编码断言做消费者验证。
  （若后续要跑上游官方测试，需单独适配 catch2/3.x 依赖库，不在本 PR 内捎带。）

## 构建系统
CMake，header-only INTERFACE library。
- `add_library(oaknut INTERFACE)` + `target_compile_features(oaknut INTERFACE cxx_std_20)`
- `install(EXPORT oaknutTargets NAMESPACE merry::)` → CMake target `merry::oaknut`
- `find_package(oaknut CONFIG)` → oaknutConfig.cmake / oaknutConfigVersion.cmake
- 测试：`oaknut-tests`（basic/fpsimd/general/vector_code_gen/_feature_detect），
  全部 `#ifdef ON_ARM64`（`__aarch64__`）包裹，JIT 执行依赖 mmap 可执行内存

## 安装路径
- 头文件: `include/oaknut/`（含 impl/ 与 feature_detection/ 子目录）
- CMake 配置: `lib/cmake/oaknut/oaknutConfig.cmake` + `oaknutTargets.cmake`
- CMake 目标: `merry::oaknut`

## OHOS 适配
- **C++20**: 共享 profile 为 cppstd=17，配方 `configure()` 强制 `cppstd=20`，
  generate() 显式 `CMAKE_CXX_STANDARD=20`（规避 E096 CMake 特性检测失败）
- **CMAKE_SYSTEM_NAME**: os=OHOS 时 `tc.blocks["generic_system"]` 设 "OHOS"
  （与 fmt/asmjit/mitama-cpp-result 一致，规避 E092 CMake 不识别平台）
- **上游测试**: `BUILD_TESTING=OFF` 跳过（Catch2 3 未发布）
- **无需补丁**: 源码纯 C++20，无 glibc/POSIX 平台假设；feature_detection 用
  `#if` 平台宏自动降级（OHOS 走 Linux ELF hwcaps 分支）

## 源码归档
- 上游无正式 release tag，采用 Debian 官方 orig tarball（该 commit 的 git 快照）
- URL: https://deb.debian.org/debian/pool/main/o/oaknut/oaknut_1.2.2+git20240301.94c726c.orig.tar.xz
- SHA256: d8160a3ebd64ea3e8c6a2f10e8259d5fcec7534b58e0a504cf25be14023d043b
- 与 Debian dsc 官方 Checksums-Sha256 一致；MD5 d222589ab6c15692164c489c74d3568b；大小 64740 字节
- 备选（真机可达 GitHub 时可用官方 tarball）:
  https://github.com/merryhime/oaknut/archive/94c726ce0338b054eb8cb5ea91de8fe6c19f4392.tar.gz

## 测试说明
- test_package 用 CodeGenerator 写入单个 uint32_t + VectorCodeGenerator 发射到 vector，
  断言指令机器码与上游 tests/general.cpp、tests/basic.cpp、README 的已知编码向量一致。
  全部为确定性编码断言，不依赖 JIT 可执行内存，不依赖 Catch2，可在任意架构编译运行。

## 真机 shadow CI 结果（已完成 2026-09-17）
- 设备: 10.62.178.77:2222（currentUser）
- 隔离 job: `ohos-users/codex/oaknut-1.2.2-git20240301.94c726c-shadow-20260917`
- 结果: **conan create passed, exit code 0**
- L0_RESULT=pass（L0j 版本无冲突；L0k 为 warn：误报 CLI 工具，实为 header-only 库无 bin/）
- L1_RESULT=pass（test_package 执行 + L1e 破坏性反向验证通过）
- L2_RESULT=skip（header-only 无 bin/，符合预期）
- L4_RESULT=pass（无补丁）
- L5_RESULT=pass（lib/ 有产物）
- test_package: **13/13 断言通过**（`PASS: oaknut header-only 库指令编码验证通过`）

### 适配过程修正点（经验）
1. **test 期望值修正**：README 示例写 `MOV(W0,42)` 输出 `0xd2800540`，实为 MOVZ X0
   （64 位 sf=1）的编码；oaknut 实际 `MOV(W0,42)`→`MOVZ(WReg)`→`0x52800540`（32 位 sf=0）。
   上游 README 该示例有笔误，编码向量以源码 `emit<...>` 模板 + 实测为准。
2. **设备环境（非配方问题）**：隔离 job 的 PATH 不含 `/data/service/hnp/bin`，
   需在 env.sh 追加 `export PATH=/data/service/hnp/bin:$PATH` 才能找到 cmake/make/ninja。
3. **/tmp 只读**（E002）：nohup 日志不能写 /tmp，需写 $HOME。
4. **make jobserver mkfifo Operation not permitted**（E074）：-j 并行构建 FIFO 受限，
   仅警告不阻塞构建。

## 路径申请（B/C 类评估）

### 路径 B（贡献创新）候选申请
本适配命中路径 B（贡献创新，10 分候选）：新增可复用方法论
「JIT/汇编器类 header-only 库的纯编码断言消费者验证」，
知识草稿：`knowledge/drafts/DRAFT-oaknut-jit-assembler-pure-encoding-assertion.{kv,md}`。

核心创新点：汇编器库在不执行机器码（不 mmap RWX、不依赖 Catch2）的前提下，用
非执行模式发射指令 + 断言机器码与上游 T() 向量/emit 模板一致，做确定性消费者验证；
并识别出"上游 README 示例编码字面量可能写混 32/64 位"这一可复用陷阱。

### 路径 C（高难度挑战）评估：不构成
对照路径 C 既有案例（enzyme：LLVM 工具链 .a stub/TableGen/lit 系统级缺口；
cling：完整 LLVM20+ORC JIT 全量构建；mlton：官方历史无修复 + bootstrap 依赖链）：
- oaknut 是 header-only 零运行时依赖库，CMake INTERFACE 构建无高难；
- 上游测试依赖的 Catch2 3 缺失属「依赖缺失」，非「系统级高难」；
- JIT 执行（mmap RWX）受 W^X 影响是已知平台限制（E045），本适配未实际攻克该点、
  也未验证 JIT 在 OHOS 真机的运行，故不构成「高难度挑战」。
最终路径分类、验收与分值由知识库维护者和赛事评审决定。
