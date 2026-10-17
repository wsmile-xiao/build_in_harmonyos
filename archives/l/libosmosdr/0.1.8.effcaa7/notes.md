# libosmosdr 0.1.8.effcaa7 适配笔记

## 编译环境

- 构建系统: cmake
- 编译日期: 2026-09-16
- 编译器: clang/clang++（Conan OHOS aarch64 profile）
- 状态: published
- 宿主平台: HarmonyOS PC (aarch64)，原生构建（非交叉编译）

## 编译步骤

1. 源码取自 Debian 官方归档 `libosmosdr_0.1.8.effcaa7.orig.tar.xz`
   （sha256 `b75476ae…6a1c60b`），上游无 configure 脚本。
2. 该包**不使用 autotools**。`Makefile.am` 仅用于 Debian 打包流程，
   tarball 内没有已生成的 `configure`，且 `AM_CONFIG_HEADER` 已废弃
   会导致 `autoreconf` 失败。经实机验证改用 CMake 构建路径。
3. 构建命令（由 Conan 驱动）：

```bash
conan create . \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing
```

4. 关键 CMake 变量: `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`（见问题 #1）。
5. 产物: `lib/libosmosdr.so`（OHOS 交叉工具链下不生成 SONAME，故无版本号后缀文件）、
   `lib/pkgconfig/libosmosdr.pc`、`include/osmosdr.h`、`include/osmosdr_export.h`、`bin/osmo_sdr`。

   > **不产物 `libosmosdr.a` 的原因**：上游 CMakeLists 的 `osmosdr_shared` 与
   > `osmosdr_static` 的 `OUTPUT_NAME` 都是 `osmosdr`，两者同名安装后 `-losmosdr`
   > 可能解析到非预期的那种；配方按 `shared` 选项只保留被选中的变体
   > （默认 `shared=True`，故包内只有 `.so`）。
   > **无 SONAME 是平台观测项**：上游设了 `SOVERSION 0 / VERSION 0.0.0`，
   > 但 OHOS 交叉工具链不产出声明的 SONAME 与版本号软链，CI 的 L5 门禁将其记为
   > warn（非阻塞），不影响链接与运行。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 4.x 报错，拒绝配置 | 上游 `CMakeLists.txt:23` 声明 `cmake_minimum_required(VERSION 2.6)`，而宿主 CMake 为 4.1.2，低于 3.5 的策略下限直接报错 | 在 `generate()` 中设缓存变量 `CMAKE_POLICY_VERSION_MINIMUM=3.5`，无需打补丁；旧版 CMake 会忽略该未用缓存项 |
| 2 | `.pc` 文件被写入 conan 缓存绝对路径 | 上游 `libosmosdr.pc.in` 剥离构建期 `-I` 的逻辑被 `IF(CMAKE_CROSSCOMPILING)` 守卫；本平台是**原生** OHOS 构建（由 conan toolchain 的 `CMAKE_SYSTEM_NAME` 决定），该标志为假，剥离分支不生效 | 在 `package()` 中用 `_drop_build_host_paths_from_pkgconfig()` 删除 Cflags 里的绝对 `-I` 项，仅保留可重定位的 `${includedir}` |
| 3 | 同名库产物冲突 | 上游同时安装 `osmosdr_shared` 与 `osmosdr_static`，两者都以 `osmosdr` 为基名 | `_keep_requested_linkage()` 按 `shared` 选项裁剪：动态保留 `.so`，静态保留 `.a` |
| 4 | 上游无任何测试 | 源码树没有 `tests/`，`CMakeLists.txt` 中没有 `enable_testing()`/`add_test()`，也没有 `check`/`ctest` 目标 | 全部测试由适配方补充（见 `test_package/`），并在 PR 中分别统计上游/新增用例 |
| 5 | CI 运行 `test_package` 时报 `Signal 11 (core dumped)` / `Error 139` | 库的公共 API 不检查 `libusb_init()` / `libusb_get_device_list()` 的返回值：CI worker 无可用 USB 栈时调用失败且出参保持未初始化，随后解引用未初始化指针 | 补 `0001-src-libosmosdr.c.patch`：出参初始化为 `NULL`，初始化失败返回"0 个设备"，设备列表获取失败先 `libusb_exit()` 再返回（详见下节） |

## 源码修改

补丁 `patches/0001-src-libosmosdr.c.patch`（`patches_applied` 已登记，类型 portability，无平台宏）：

- 覆盖 `osmosdr_get_device_count()` / `osmosdr_get_device_name()` / `osmosdr_get_device_usb_strings()` / `osmosdr_open()`
  四个公共 API：`libusb_context *ctx` 与 `libusb_device **list` 先初始化为 `NULL`；
  `libusb_init()` 失败直接返回"无设备"（count `0` / 名字 `""` / 错误码），
  `libusb_get_device_list()` 失败先 `libusb_exit(ctx)` 再返回同样结果。
- 不改动任何正常路径语义，也不改变无 USB 环境下的对外表现（仍然报告 0 个设备），
  只是把"解引用未初始化指针"改成"优雅上报无设备"。

问题 #1 通过 CMake 缓存变量解决，问题 #2/#3 在 `package()` 阶段对安装产物做规范化，
两者均未改动上游源码。

## 依赖版本

| 依赖 | 版本 | 说明 |
|------|------|------|
| libusb | 1.0.27 | W0 阶段确认制品仓已发布 OHOS armv8 二进制，`conan download` 实测存在 |

## 验证结果

```bash
$ conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
======== Testing the package: Running test() ========
libosmosdr consumer tests (HarmonyOS PC aarch64)
TC-01 device enumeration
       osmosdr_get_device_count() = 0
  [PASS] no OsmoSDR device is reported on a worker without hardware
  ...
TC-03 OHOS shared object loadability
  [PASS] libosmosdr.so resolves its dependencies at load time
  ...
13 checks, 0 failure(s)
TC-04 osmo_sdr executes on OHOS and reports its usage
======== Tested package revision: ...  ========
[exit code 0]
```

- 上游测试: 0 项（上游无测试套件）
- 适配新增测试: 4 个用例 / 13 项断言，全部通过（用例 4/4 = 100%，断言 13/13 = 100%）
- 详细报告: `reports/test-report.md`
- 用例数与断言数分别统计：1 个用例可含多项断言，故两个口径不可混用（如 TC-02 为 1 个用例 4 项断言）

## 交付物

| 文件 | 说明 |
|------|------|
| `lib/libosmosdr.so` | 动态库主体（无版本号后缀，见上「产物」说明） |
| `lib/osmosdr_static/libosmosdr.a` | 静态库（仅 `shared=False` 时保留） |
| `lib/pkgconfig/libosmosdr.pc` | pkg-config 元数据（已清理绝对路径） |
| `include/osmosdr.h` | 公共头文件 |
| `bin/osmo_sdr` | 命令行工具（`commands.json` 已声明） |

## 注意事项

- **不要在 `ci/config/no_official_test.txt` 中登记本包。** 该白名单会整体
  跳过 CI 的 L1a–L1d 检查；本包有真实 `test_package`，应当被验证而不是豁免。
- 本包在 worker 原生 OHOS 环境构建（非交叉编译），因此
  `CMAKE_CROSSCOMPILING` 为假——上游针对交叉编译写死的清理逻辑不会生效，
  后续升级上游版本时需重新确认问题 #2 是否仍然存在。
- `osmo_sdr` 无参数运行会打印用法并以退出码 1 结束，属预期行为，
  测试中按此断言。
---

### 对话 #1 — 2026-09-16（首次适配，OHOS armv8）

**目标**: 将 libosmosdr 0.1.8.effcaa7 适配到 HarmonyOS PC，产出可复现的 Conan 配方并能通过 CI。

**关键决策**:

1. **构建系统选 CMake**：发布包内没有 `configure`，且 `configure.ac` 使用过旧的
   `AM_CONFIG_HEADER` 宏导致 `autoreconf` 失败，故直接用上游自带的 CMake 构建。
2. **cmake 4.x 策略兼容**：host cmake 4.1.2 在 `CMakeLists.txt:23` 因策略版本报错，
   构建期传入 `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`。
3. **依赖**：`libusb/1.0.27` 已在制品仓发布且含 OHOS armv8 制品，直接 `requires`。
4. **测试策略**：上游仓库无任何测试套件，故在 `test_package/` 补 4 个用例，
   其中 2 个为鸿蒙特有（`.so` 可加载性、`osmo_sdr` 工具可执行性）。

**遇到的问题**:

- 交叉路径守卫在本包（原生 OHOS 构建）下不生效，`.pc` 中会泄漏构建机绝对路径，
  已记入知识草稿 E580（详见「遇到的问题与解决方案」问题 #2）。
- 环境无 SDR 硬件，`osmosdr_get_device_count()` 返回 0 个设备属预期行为，测试按此断言。

**产出**: `conanfile.py` / `conandata.yml` / `test_package/` / `commands.json` /
`README.md` / `manifest.yaml`；验证结果：`conan create` 成功、13/13 断言通过、
W3 本地 CI 12 项检查全部通过。
---

### 对话 #2 — 2026-09-17（CI Signal 11 修复）

**目标**: 修复 PR 首次 CI 绿、重跑 CI 变红后的 `test_package` 崩溃（`Signal 11 / Error 139`）。

**定位过程**:

1. 从 CI 日志确认崩溃前只打印了横幅，**没有任何 `TC-01` 输出** → 崩溃在第一个库调用内部，
   而不是测试驱动或 `self.run()`。
2. 本机 W3 同一二进制、同一输入全绿（`12 checks, 0 failure(s)`），CI 与本地在
   "签名 + 运行"两段日志完全一致 → 判定为**环境相关**，不是确定性代码缺陷。
3. 用返回失败的 libusb 替身（`libusb_init` 失败 / `libusb_get_device_list` 失败两种模式）
   在本地复现：未打补丁的库两种模式都 rc=139；确认根因是库不检查 libusb 返回值、
   解引用未初始化指针。

**关键决策**:

- 修库而不是改测试：信号发生在被测库内部，包装 `self.run()` 拦不住；且消费方在无 USB
  环境同样会崩，只跳过测试属于掩盖问题。
- 出参初始化为 `NULL` + 检查返回值，保持"无 USB 时报 0 个设备"的既有对外语义不变。
- 测试程序加 `setvbuf(stdout, NULL, _IONBF, 0)`：这次崩溃现场被 stdio 缓冲吞掉，
  导致日志里看不到停在哪一步，无缓冲后崩溃点可诊断。

**遇到的问题**:

- CI 绿过一次又变红、输入未变 → 环境相关路径（USB 设备节点）在 CI 与开发机表现相反，
  已记入知识草稿 E581。

**产出**: `patches/0001-src-libosmosdr.c.patch`（portability，无平台宏）、
`conandata.yml` 增 `patches` 段、`manifest.yaml` 增 `patches_applied` / `patch_classification`
（type=portability、platform_only=false、guard=none）与 E581 知识引用；
复验：`conan create` 成功、4 个用例 / 13 项断言全通过、W3 12 项检查全通过。
用例数与断言数不因本次修复而变化。
---

**编译结束**: 2026-09-17 15:38
**最终状态**: published
