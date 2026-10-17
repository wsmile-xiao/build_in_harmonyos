# uchardet 0.0.7 适配笔记

## 编译环境
- 构建系统: cmake
- 首次编译日期: 2026-05-25（历史归档，状态 built，无 Conan 配方）
- Conan 适配日期: 2026-09-18（本笔记，状态 built：conan-verify 全过，CI upload 待 PR 合入）
- 编译器: clang/clang++（OHOS aarch64，profile: ci/conan/profiles/ohos-aarch64）

## 历史（2026-05-25，built）→ 本次（2026-09-18，built + Conan 配方）

历史归档已验证：源码在 OHOS 上原生编译零修改（无补丁）、116 项上游测试全过。
本次工作为补齐 Conan 适配（conanfile.py + conandata.yml + test_package/ + commands.json）。

## Conan 适配步骤（2026-09-18）

1. conan-init 生成骨架 → 人工修正（见下"修正项"）
2. conan-verify 八道门禁（G0-G4 + L2/L4/L5）全绿
3. 强制重建验证：`conan create --build=uchardet/*` exit=0，
   build() 内 `cmake.test()` 执行上游 116 项语料测试 → `100% tests passed, 0 tests failed out of 116`
4. test_package 消费者测试（真实 API 调用）→ 4/4 PASS（ASCII/UTF-8/GB18030/BIG5 + reset 复用）

## 生成骨架的修正项（conan-init 模板 → 正式配方）

| # | 模板默认 | 修正为 | 原因 |
|---|---------|--------|------|
| 1 | `tc.variables["CMAKE_POLICY_VERSION_MINIMUM"]` | `tc.cache_variables[...]` | 普通 variables 写入 toolchain 文件的 set()，对 cmake_minimum_required(2.8.5) 时机太晚不生效，必须以命令行 -D 传入（CMake>=4.0 拒绝 <3.5 兼容级别）。第一次 G2 失败根因 |
| 2 | `tc.variables["CMAKE_INSTALL_PREFIX"] = "$DEFAULT_PREFIX"` | 删除 | 模板占位符错误：conan create 自带 install prefix（-DCMAKE_INSTALL_PREFIX=包目录），字面量 $DEFAULT_PREFIX 会破坏安装 |
| 3 | `tc.variables["CMAKE_BUILD_TYPE"] = "Release"` | 删除 | CMakeToolchain 从 settings.build_type 自动生成，硬编码会破坏 Debug 构建 |
| 4 | test_package/test.c 为 printf 空壳 | 重写为真实 API 测试 | R34：必须调用被测包 API。喂 4 段已知编码字节序列断言检测结果 |
| 5 | sha256 占位符 | 实测 f3635d1d...69f58 | conandata.yml 必填真实校验和 |
| 6 | 无 commands.json | 软件级 commands.json | R38：产物含 bin/uchardet CLI 工具；package_info 显式声明 bindirs=["bin"]（a52dec 先例：library + tool 混合类型） |

## 遇到的问题与解决方案（累计）

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 版本兼容性错误 | CMakeLists.txt 要求 cmake 2.8.5，CMake 4.x 拒绝 | `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`（历史已验证；conan 里必须用 cache_variables） |
| 2 | test 断言 "reset produced empty charset" 失败 | 断言逻辑错误：reset 后未喂数据，检测结果理应为空 | reset 后重新喂数据再断言相同检测结果（真实验证句柄可复用） |
| 3 | C 测试程序链接 libuchardet.a 失败风险 | 库本体 C++（operator new/delete、__cxa typeinfo） | test_package 的 CMakeLists 设 `LINKER_LANGUAGE CXX`（test.c 保持 C 编译，C++ 驱动链接） |
| 4 | /tmp 只读 | E002 | 全部临时文件走 $TMPDIR |
| 5 | shared 变体：libuchardet.so 无 SONAME，CLI 记录相对 NEEDED `../libuchardet.so` 包外不可解析 | OHOS 本机构建时 CMake 自检 CMAKE_SYSTEM_NAME=HarmonyOS（未知平台，无 Linux SONAME 版本化规则，且不落 SOVERSION 文件名） | generate() 显式 `tc.cache_variables["CMAKE_SYSTEM_NAME"]="Linux"`（abcmidi 先例）：SONAME=libuchardet.so.0 + 版本化文件名 + 规范 NEEDED，shared 变体 conan create 全流程通过 |
| 6 | 新写二进制偶发 exec EPERM（Operation not permitted） | OHOS 新文件首次执行的安全确认机制（R7/E046 环境特性），同权限旧文件可执行 | 环境特性非包缺陷；W3 本地 CI 模拟（CI 同构）通过，二进制 ELF 结构（NEEDED/SONAME）已用 readelf 验证正确 |

## 源码修改

无补丁，源码零修改。

## 依赖版本

无外部依赖（纯 C++ 库）。

## 验证结果（2026-09-18）

```bash
# conan create 强制重建（--build=uchardet/*，默认 shared=False）
exit=0
100% tests passed, 0 tests failed out of 116   # build() 内 cmake.test()

# conan create shared=True 变体（CMAKE_SYSTEM_NAME=Linux 修正后）
exit=0；116/116 上游测试；test_package 8/8；SONAME=libuchardet.so.0

# test_package（真实 API 调用）
PASS ascii -> "ASCII"
PASS utf-8 -> "UTF-8"
PASS gb18030 -> "GB18030"
PASS big5 -> "BIG5"
# + reset 复用断言 4 项

# conan-verify 门禁
G1 配方完整性 PASS / G2 干净构建 PASS / G3 系统同名库隔离 PASS /
G4 产物完整性 PASS / L2 smoke PASS / L4 安扫 PASS / L5 基线 PASS

# W3 本地 CI 模拟（build_and_test.sh，CI 同构）
JC/KC/L0 全部通过，conan create exit=0
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方（cmake 路线，shared/fPIC 选项，默认静态） |
| conandata.yml | 官方源 URL + sha256 |
| test_package/ | 消费者测试（C API，4 编码断言 + reset 复用） |
| commands.json | 软件级 CLI 工具声明（R38，bin/uchardet） |
| manifest.yaml / notes.md / reports/ | 元数据 |

## 注意事项

1. CMAKE_POLICY_VERSION_MINIMUM 必须走 cache_variables（见修正项 #1）
2. C 消费者链接需 C++ 驱动（修正项 #3）
3. CLI 工具与库同包（上游 BUILD_BINARY 默认 ON），commands.json 已声明
---

**编译结束**: 2026-09-18 18:03
**最终状态**: built（conan-verify 八道门禁全 PASS；published 待 PR 合入后 CI release 流水线 conan upload 完成）
