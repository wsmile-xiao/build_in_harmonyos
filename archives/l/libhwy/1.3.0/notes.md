# libhwy 1.3.0 适配笔记

## 编译环境

- 构建系统：cmake
- 编译日期：2026-09-19
- 编译器：clang/clang++（HarmonyOS PC 真机工具链，conan profile 提供）
- 状态：built（待 HMBS 真机预检回填实测证据后由后端提交）

## 库信息

- 软件：libhwy（Google Highway，conan-center 包名；与本仓 archives/h/highway 同源）
- 版本：1.3.0
- 许可证：Apache-2.0
- 上游：https://github.com/google/highway
- 功能：跨平台 SIMD 指令封装，aarch64 下自动选用 NEON 路径
- 依赖：零运行时依赖（system_libs 仅链接系统库 m、pthread）

## 编译步骤

配方执行 `conan create` 时的实际步骤（`build()`）：

```bash
cmake -S <src> -B _build -DBUILD_SHARED_LIBS=OFF -DBUILD_TESTING=ON \
  -DHWY_ENABLE_CONTRIB=ON -DHWY_ENABLE_EXAMPLES=OFF -DHWY_ENABLE_INSTALL=ON \
  -DHWY_ENABLE_TESTS=ON -DHWY_FORCE_STATIC_LIBS=ON -DHWY_TEST_STANDALONE=ON \
  -DHWY_WARNINGS_ARE_ERRORS=OFF -DCMAKE_INSTALL_LIBDIR=lib
cmake --build _build
ctest --output-on-failure   # 上游官方测试套件（仅 with_upstream_tests=True，默认开启）
cmake --install _build
```

test_package（消费者视角）：`find_package(hwy CONFIG)` + 链接 `hwy::hwy`，
编译 `test_libhwy.cpp` 后经 `ctest --output-on-failure` 运行，7 个显式 SIMD 检查。

## 同源配方复用说明

本仓 `archives/h/highway/1.3.0.2` 已在 HarmonyOS aarch64 真机验证通过
（上游 60/60，消费者 7 检查），libhwy 与其同源码、同版本，复用其全部
关键结论：

| # | 结论 | 来源 |
|---|------|------|
| 1 | 源码取 git tag 归档 `archive/refs/tags/1.3.0.tar.gz`，sha256 `07b3c1ba…` | highway 1.3.0.2（Buildroot 官方哈希交叉印证） |
| 2 | OHOS 下 `CMAKE_SYSTEM_NAME=Linux` + `CMAKE_SYSTEM_PROCESSOR=<arch>` | highway 1.3.0.2 generate() |
| 3 | `CMAKE_TRY_COMPILE_TARGET_TYPE=STATIC_LIBRARY` 绕过部分 worker 缺 libxml2 导致的 lld 链接失败 | highway 1.3.0.2 generate() 注释 |
| 4 | `HWY_TEST_STANDALONE=ON`，上游测试不下载 googletest | highway 1.3.0/1.3.0.2 notes |
| 5 | 消费者测试用 capped float 标签做 Load/Iota/Set/Store 运算并校验非活跃 lane 不被改写 | highway 1.3.0.2 test_highway.cpp（真机通过） |

包名差异说明：conan-center 上游生态中该库的规范包名为 `libhwy`
（cmake 包名仍为 `hwy`，target `hwy::hwy`，pkg-config `libhwy` 不变），
故本配方 `name = "libhwy"`，产物与 highway 配方二进制兼容。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Windows 检出上游 main 失败：`archives/g/gama/...patch??` 非法路径 | 上游某文件名以回车符结尾，Windows 无法创建 | 本地 sparse-checkout 排除该无关目录；不影响本配方，远端 Linux CI 不受影响 |
| 2 | Windows 大小写不敏感导致 `archives/l/libXext` 与 `archives/l/libxext` 冲突 | 上游同时存在仅大小写不同的目录 | 本地 sparse-checkout 排除 `libXext`；同上，仅本地现象 |
| 3 | 上游测试默认开关曾导致 CI worker 链接可执行文件失败 | 部分 worker 缺少 lld 所需的 libxml2 | 沿用 highway 1.3.0.2 的 `CMAKE_TRY_COMPILE_TARGET_TYPE` 方案 |

## 上游测试清点（申报）

- 上游测试目录：`hwy/tests/`（算术/逻辑/类型转换/压缩/排序/密码学/contrib 等），经 CTest 调度
- 开关：`HWY_ENABLE_TESTS=ON` + `HWY_TEST_STANDALONE=ON`（默认开启，随 `conan create` 真实运行）
- 同源 highway 1.3.0.2 真机实测：60/60 通过；本包精确计数以 HMBS 真机预检日志为准
- 防误报：`build()` 先用 `ctest -N` 取得发现数，再解析 `ctest` 输出的通过/失败数；
  解析不到或执行数与发现数不一致时直接抛错，不伪造通过

## 验证结果

本轮为工作树准备轮（依任务守则不提交、不推送、不在本机运行 conan）。
以下由 HMBS 后台真机预检回填：

```bash
# HMBS 真机预检（conan create，环境与官方 CI 同源）
# - HMBS_TEST_PACKAGE_RESULT 行（discovered/passedCount）
# - HMBS_UPSTREAM_TEST_RESULT 行（discovered/executed/passed/failed/skipped）
```

## 注意事项

- 本包为纯库，无可执行产物，不需要软件级 `commands.json`（R38 仅命令行工具需要）
- 非系统同名库，保留动态/静态产物由 Conan 管理依赖链（R26 不适用；默认静态）
- 平台判断统一使用 `str(self.settings.os) in ("Linux", "OHOS")`（R32）
