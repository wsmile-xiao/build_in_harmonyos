# lib60870 2.4.0 适配笔记（HarmonyOS PC / aarch64）

## 编译环境
- 构建系统: CMake（上游工程位于源码包 `lib60870-C/` 子目录，`cmake_minimum_required(3.0...3.31)`）
- 编译日期: 2026-09-14
- 编译器: clang 15.0.4（OHOS SDK，musl libc）
- 状态: published（待 CI）

## 编译步骤

```bash
# 探索验证（本机 HarmonyOS PC 原生）
cmake ../src -DCMAKE_C_COMPILER=clang -DCMAKE_BUILD_TYPE=Release \
  -DBUILD_EXAMPLES=OFF -DBUILD_TESTS=ON \
  -DCMAKE_POLICY_VERSION_MINIMUM=3.5 -DUNIX=1
make -j1
(cd tests && ./tests)          # 90/90 PASS
# Conan 正式构建
conan create . -pr:h=~/.conan2/profiles/ohos-aarch64 -pr:b=同 --build=missing
```

## 关键适配点

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 配置报 `No SOURCES given to target: lib60870-shared / lib60870` | OHOS 适配版 conan 的 CMakeToolchain 将 `CMAKE_SYSTEM_NAME` 映射为 `HarmonyOS`，CMake 4.x 不认识该平台 → `UNIX`/`APPLE`/`WIN32` 全部未定义 → 上游 `src/CMakeLists.txt` 的 `IF(UNIX)` 分支不选中任何 HAL 源文件 | `generate()` 中对 OHOS 显式 `CMAKE_SYSTEM_NAME=Linux` + `CMAKE_SYSTEM_PROCESSOR=aarch64`（E092，先例 airspyhf/allegro4.4）——linux HAL（socket/thread/time/serial）所用的全部 API 在 OHOS musl 中可用，已由本机原生运行 90 个上游测试证实 |
| 2 | CMake 4.x 拒绝 `cmake_minimum_required(VERSION 3.0)` | 上游声明 3.0，低于 CMake 4.x 下限 | 命令行/Toolchain 传 `CMAKE_POLICY_VERSION_MINIMUM=3.5`（任务参数既定路线） |
| 3 | `-lrt` 链接 | 上游 `src/CMakeLists.txt` 在 UNIX 分支无条件 `target_link_libraries(lib60870 -lpthread -lm -lrt)`；musl 无独立 librt（clock_gettime 等在 libc 中） | 实测链接通过（clang 对 musl 静默接受 `-lrt`，无需 patch）；`package_info` 照常传播 `pthread/m/rt` |
| 4 | 库产物命名 | 上游 CMake target 名与 OUTPUT_NAME 均为 `lib60870` → 产物为 `liblib60870.so`/`liblib60870.a`（双 lib 前缀，与 libiec61850 同风格） | `cpp_info.libs = ["60870"]`（Conan 生成 `-l60870` → 链接器自动补 lib 前缀匹配 `liblib60870`） |
| 5 | make 并行 | HMDFS jobserver fifo EPERM（E074） | `cmake.build(args=["--", "-j1"])` |
| 6 | `.pc` 安装位置 | 上游装到 `share/pkgconfig` | package() 移动到 `lib/pkgconfig` |

## 上游测试（真实执行）

- 上游测试框架：Unity（`tests/unity/`），单体二进制 `tests/tests`，`tests/all_tests.c` 9633 行
- 上游总 RUN_TEST 数：121；其中 31 个 TLS 用例被 `#if (CONFIG_CS104_SUPPORT_TLS == 1)` 包裹——本包未 vendored mbedtls（上游 dependencies/ 需手动放置 mbedtls 2.28/3.6 源码），TLS 关闭时这 31 个用例**不编译**（与上游 CI 在无 TLS 配置下的行为一致）
- 实际编译并执行的用例数：**90**
- 本机（HarmonyOS PC 原生）执行结果：**90 Tests, 0 Failures, 0 Ignored — OK**，exit code 0
- conan create 阶段：`can_run(self)` 为真时 `BUILD_TESTS=ON` 并在 build() 中以 conanrun env 运行 `tests/tests`（测试二进制静态链接 lib60870 静态库，无外部共享库依赖）
- 逐用例明细：90/90 PASS（unity 输出逐行 `test_xxx:PASS`），无 FAIL/IGNORE

## 源码修改

无补丁。所有平台差异通过 Conan Toolchain 变量解决（CMAKE_SYSTEM_NAME 覆盖 + CMAKE_POLICY_VERSION_MINIMUM），源码零修改。

## 依赖版本

- 无任何 conan 依赖（纯 C，TLS 可选项未启用，sqlite server 示例未构建）
- 系统库：pthread、m、rt（musl 内建，链接器接受）

## 验证结果

```bash
# 1) 探索构建 + 上游测试（本机）
$ make -j1 && cd tests && ./tests
-----------------------
90 Tests 0 Failures 0 Ignored
OK

# 2) conan create（ohos-aarch64 profile，见 reports/）
lib60870/2.4.0: Package 'xxx' created
lib60870/2.4.0: Build folder ... conanbuild/conanrun env
test_lib60870: PASS (version 2.4.0, ASDU population, CP56Time2a, CS104 slave cycle, step position)
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方（含上游测试集成） |
| conandata.yml | 源码 URL + sha256 |
| test_package/ | 消费者测试（真实调用公开 API） |
| manifest.yaml | 版本级元数据 |
| notes.md | 本笔记 |

## 注意事项

- 上游 tag 命名：v2.4.0（`https://github.com/mz-automation/lib60870/archive/refs/tags/v2.4.0.tar.gz`），sha256 `5c4b9bde...`，239 个文件
- 上游 CMakeLists 位于 `lib60870-C/` 子目录而非源码根——conanfile `source()` strip_root 后 Conan 的 CMake 会自动找到该子目录的 CMakeLists（根目录无 CMakeLists.txt 时 CMake 向下搜索，已验证）
- 上游 `tests/CMakeLists.txt` 会 `configure_file(...COPYONLY)` 拷贝 TLS 证书到 build 目录，即使无 TLS 也执行（无害）
- `lib60870_config.h` 上游本版本已改为源码树内静态文件（`config/lib60870_config.h`），非 configure_file 生成

---

**编译结束**: 2026-09-14
**最终状态**: built（本地全绿，待 CI/发布）
