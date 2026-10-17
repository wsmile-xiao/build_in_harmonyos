# onnx 1.22.0 适配笔记

## 基本信息
- 软件: onnx（Open Neural Network Exchange）
- 版本: 1.22.0
- 构建系统: CMake（cmake_minimum_required 3.26，C++17）
- 上游仓库: https://github.com/onnx/onnx
- 许可证: Apache-2.0
- 目标平台: OHOS aarch64（armv8）

## 依赖
| 依赖 | 版本 | 用途 |
|------|------|------|
| protobuf | 33.6.1 | 核心依赖，onnx.proto 编译与 libprotobuf 链接；要求 protoc >= 4.25.1（INSTALL.md 明文），33.6 满足 |
| abseil-cpp | 20260107.1 | protobuf >= 4.22 时 onnx 直接 find_package(absl REQUIRED)，由 protobuf 传递 |
| utf8_range | protobuf 包内 | onnx 在 protobuf>=4.22 时 find_package(utf8_range)，随 protobuf 包提供 |

## 构建决策
1. **protobuf 探测路径**：ONNX CMakeLists.txt:170-183 先判断 `TARGET protobuf::libprotobuf`，
   该 target 在本构建序列中尚未由任何前置 find_package 建立，因此实际走 183-275 行的
   `find_program(protoc)` + `find_package(Protobuf)` 路径。配方通过 toolchain 变量
   `Protobuf_DIR / absl_DIR / utf8_range_DIR` 指向 conan 包内安装的 cmake config，
   使 find_package 命中包内 config（而非 FetchContent 自建 protobuf）。
2. **host protoc**：本构建机为 OHOS aarch64（与目标同架构），protobuf 33.6.1 包内 `bin/protoc`
   可直接执行（实测 `protoc --version` → libprotoc 33.6）。配方同时注入
   `ONNX_CUSTOM_PROTOC_EXECUTABLE` 与 `Protobuf_PROTOC_EXECUTABLE` 指向该 protoc，
   覆盖 ONNX 的两条探测分支（CONFIG 分支用前者，find_program 分支用后者），无需 PATH 注入。
3. **Python 绑定不建**：ONNX_BUILD_PYTHON=OFF，目标只是 C++ 库与 onnx.proto 工具链产物。
4. **测试**：默认 ONNX_BUILD_TESTS=OFF（沿用上游默认；配方保留 `build_tests` 开关）。
   本次适配已将上游 gtest 套件在 HarmonyOS PC aarch64 上实际编译并【真实执行】，
   结果见「测试」节。

## 关键坑（Error -11，本次适配最大阻塞）
- **现象**：`conan create` 在 `cmake.configure()` 处抛 `ConanException: Error -11 while executing`，
  cmake 自身零输出即 SIGSEGV；同命令、同 toolchain、同构建目录在 shell 中手动执行却完全正常。
- **根因**：配方 `generate()` 曾用 `Environment().vars(self).save_script("conanbuild")` 把
  protobuf 的 `bin/` 注入 PATH。该调用写出的文件名与 Conan 自身的聚合脚本
  `conanbuild.sh` **同名冲突**，导致聚合脚本把自身列入 source 列表：
  ```
  . "<gen>/conanbuild.sh" && . "<gen>/conanbuildenv-release-armv8.sh"
  ```
  Conan 的 `run()` 会把每条命令包装成 `. conanbuild.sh && <cmd>`，于是 source 递归 →
  栈溢出 → SIGSEGV。实测 `sh -c '. ./conanbuild.sh'` 返回 **139**，与错误码 -11 完全对应。
- **修法**：移除该 env 脚本，改为向 CMake 预置 `Protobuf_PROTOC_EXECUTABLE` cache 变量
  （`find_program` 见到已存在的变量即直接采用），一行变量替代 PATH/env 注入，零副作用。
- **教训**：Conan 配方中**不要用裸 `conanbuild`/`conanrun` 作为 `save_script` 名**
  （仓库内先例均刻意避开，如 `conanbuild_runpath`、`conanbuild_algobox_qt`）。
  该缺陷与源码、toolchain、编译环境均无关，仅表现为构建期 cmake 段错误。

## 关键文件
- conanfile.py: 配方主文件，注入三个 *_DIR 与两处 protoc 路径变量
- conandata.yml: 官方源码 URL + sha256
- test_package/: 消费者测试（最小 ModelProto + checker 校验 + 二进制回环 + IR_VERSION 断言）
- test_package/MANIFEST.yml: 上游/消费者测试清单

## 测试
- 消费者（test_package）：`test_onnx` 在 HarmonyOS PC aarch64 上真实执行，
  **11/11 断言通过**；`ctest` 用例 `onnx_minimal_model` **1/1 通过**。
- 上游（gtest，onnx/test/cpp）：本机以 conan 制品仓 `gtest/1.17.0` 增量构建 `onnx_gtests`
  并真实执行。gtest 注册 **108** 个用例（源码 TEST 宏 111 个，其中 3 个受上游平台条件编译
  保护在 HarmonyOS 下不注册），实跑 **107 通过**；唯一未能执行的是
  `CHECKER.OpenExternalDataTest`，它在宿主上触发 `Bad system call`（SIGSYS，seccomp 沙箱拦截），
  与适配无关。

## 已知限制
- 上游 Python 测试（onnx/test/*.py）不运行：Python 绑定未构建。
- `CHECKER.OpenExternalDataTest` 依赖的 syscall 被宿主沙箱拦截（SIGSYS），本机无法执行；
  CI/真机环境可覆盖。

## 状态
- 编译状态: **通过**（`conan create` exit_code=0，产物 `lib/libonnx.a` 16,819,034 B +
  `lib/libonnx_proto.a` 412,776 B + `include/onnx/`(104 头文件) + `lib/cmake/ONNX/ONNXConfig.cmake`）
- 日期: 2026-09-18

## 2026-09-19 审查整改记录（PR #10824）

- **rule4（少报）**：上游用例计数口径对齐平台审查实测 **N=1533** —— 上游 v1.22.0 发布树全仓
  `*.py` 的 `def test_*` 计数（命令 `grep -rhoE 'def test_[A-Za-z0-9_]*' . --include='*.py'`，
  输出 1533 行；分布 `onnx/test/*.py` 1530 + `onnx/backend/test` 3）。原声明 111 仅为 C++ gtest
  单口径，构成少报。PR 描述「上游库测试用例统计」合计与「验证结果」已同步为 1533；
  C++ gtest 资产 111 个作为另一统计口径单列于「适配后测试用例统计」，不重复计入合计。
- **rule2/3（测试减少原因）**：PR 描述新增「测试减少原因」节 —— Python 测试面 1533 个用例未执行
  （交付物为 C++ 静态库，`ONNX_BUILD_PYTHON=OFF`，无 pybind11 扩展与 Python 运行时）；
  C++ 面 111→108 的 3 个为上游 `#ifdef _WIN32` 等条件编译保护项；上游测试资产零改动。
- **rule11**：「⚠ test_package 需复核」讨论串已回复四段式复核说明并标记 resolved。
- 本次修订无代码逻辑变更，仅文档口径与整改记录（配方、补丁、test_package 均未改动）。
