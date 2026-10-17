# onnx 1.20.0 适配笔记

## 基本信息
- 上游：https://github.com/onnx/onnx （tag `v1.20.0`）
- 源码 sha256：`e9e9273cd39d460348aa3e2eb370a444b510e138c5f45dfa86ce50461901257b`
- 构建系统：CMake >= 3.26，C++17（`CMakeLists.txt:2,79`）
- 交付物：静态 `libonnx.a` / `libonnx_proto.a` + `include/onnx/*.h`，上游 install 导出 `ONNX::onnx` / `ONNX::onnx_proto`

## 语言判定（R47）与官方裁定
- `lang-preflight` 判 `detected_language=python`：根级 `pyproject.toml` 走 manifest 优先（`lang_detect.py:107-110`）、
  绑定标记未含 `nanobind`（`:245-255`）、绑定覆盖要求 cpp 主体 ≥70%（`:190-194`），而源码 .py 占 88%。
- **2026-09-16 官方裁定：「onnx 算 C 库」** → 本库按 C/C++ 路径适配；python 判定记为仅本库的已知误判。
- 本地 `lang-preflight` 无覆盖机制；`finish`/`submit` 不会复跑该门（仅 Step 1.5 一次），裁定记录于此与最终 result。

## 依赖（W0 结论：全部可消费）
- `protobuf/33.6.1`（传递 `abseil-cpp/20260107.1`、`zlib/1.3.1`）
- `googletest/1.17.0`（测试；cmake 目标名 `GTest::gtest`，注册表另有 `gtest` 包但目标名是小写 `gtest::gtest`，不匹配 ONNX 的 `find_package(GTest)`）
- `utf8_range` 随 protobuf 包内置（`lib/cmake/utf8_range`），非独立配方

## 构建要点
1. protobuf 注册表包 `cmake_find_mode=none` → `generate()` 必须显式给 `Protobuf_DIR` / `utf8_range_DIR` / `absl_DIR`（grpc/1.70.0、etcd-cpp-apiv3 同款）。
2. **交叉 protoc**：目标包 `bin/protoc` 是 aarch64，x86_64 构建机不能执行 → 配方**不使用 `tool_requires`**；交叉构建通过 `user.onnx:host_protoc` conf 或 `ONNX_HOST_PROTOC` 环境变量传入宿主 protoc，CI 原生构建两者都不设置 → 直接用目标 `protoc`。
3. ONNX 的「自定义 protoc」分支要求 `protobuf::libprotobuf` 预先存在（`CMakeLists.txt:163-176`）→ 用 `CMAKE_PROJECT_INCLUDE` 预载 `find_package(Protobuf CONFIG)`，**不改上游 CMakeLists**。
4. 本地构建构建上下文（host zlib/protobuf）需要 `cc`/`c++`：`conan create ... -c:b tools.build:compiler_executables={"c":"/usr/bin/cc","cpp":"/usr/bin/c++"}`。

### 本地 W3（交叉）实测

- 宿主 protoc 一次性构建（x86_64）：protobuf 33.6 源码 + 构建上下文 abseil → `~/.ohos/bin/protoc`（`libprotoc 33.6`）。
- 命令：
  ```bash
  ONNX_HOST_PROTOC=$HOME/.ohos/bin/protoc conan create archives/o/onnx/1.20.0 \
    -pr:h=$PROF_AARCH64 -pr:b=default \
    -c:b 'tools.build:compiler_executables={"c":"/usr/bin/cc","cpp":"/usr/bin/c++"}'
  ```
- 结果：**CREATE_EXIT=0**（onnx 编译 100%、打包、test_package 构建通过；交叉下 ctest 跳过，由 CI 原生执行）。
- 日志：`/mnt/e/dsh working/tasks/onnx-1.20.0-2026-09-16/logs/031-conan-create-11.log`。

### 踩坑记录（供后续同类库复用）

1. 构建上下文（host）protobuf 走 `tool_requires` 不可行：仓库 zlib 配方默认 `CC=clang`（host 无 clang）；protobuf host 测试又误链 conda 的 `gmock_main.lib`。→ 改为**手工一次性构建 x86_64 protoc**（protobuf 33.6 + host abseil），配方在交叉时用 `ONNX_HOST_PROTOC`。
2. 注册表 `gtest/1.17.0` 导出的目标是 `gtest::gtest`，而 ONNX `find_package(GTest)` 之后判断 `GTest::gtest` → 链接裸 `-lgtest` 失败。→ 改用 **`googletest/1.17.0`**（`cmake_file_name=GTest`、目标 `GTest::gtest`）。
3. 直接 `self.requires(googletest)` 触发 conan「直接依赖未被 cpp_info.requires 使用」→ 改 **`self.test_requires`**。
4. CMakeDeps 包装的 ONNXConfig 会 `find_dependency(protobuf)`（小写）且引用不存在的 `protobuf::protobuf` → 配方 `package_info` 设 **`cmake_find_mode=none`**，消费者直接用上游 `lib/cmake/ONNX/ONNXConfig.cmake`；test_package 同时设 `Protobuf_DIR` 与 `protobuf_DIR`。
5. 消费 ONNX 的 CMake 项目需**显式链接 `protobuf::libprotobuf`**（与上游 `onnx/test/cmake/CMakeLists.txt` 一致），否则缺 protobuf 头文件。

## 上游测试清点（R51）
- 入口：`-DONNX_BUILD_TESTS=ON` 后由 `ctest` 驱动（`cmake/unittest.cmake` 定义 `onnx_gtests`）。
- 用例源：`onnx/test/cpp/*.cc`（12 个，含 `test_main.cc`）；测试数据 `onnx/backend/test/data`（23MB，随源码）。
- 执行：`build()` 中 `can_run(self)` 为真时跑 `ctest --output-on-failure --no-tests=error`。
- **本地交叉 W3：`onnx_gtests` 仅编译、未执行**（host profile `tools.build:skip_test=True` + 交叉无法运行 aarch64 测试）。
- **原生 CI（build #48858）：已执行上游测试，L1 门禁（测试执行验证）通过**；逐用例计数 CI 回执不发布，见完整日志 https://ohpcd.atomgit.com/ci?id=48858

## 状态
- 本地交叉：`conan create` EXIT=0、`conan-verify` G0-G3 PASS、`finish` W3 通过（`.ci-result.json` exit_code=0）。
- **原生 CI（build #48858）：校验通过**——Conan test_package / L0 结构 / L1 测试执行验证全过；AI 代码检视「未发现问题」。
- 等人工评审 / 合入。
---

**编译结束**: 2026-09-16 19:14
**最终状态**: built
