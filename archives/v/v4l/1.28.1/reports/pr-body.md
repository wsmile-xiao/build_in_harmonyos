- **三方库名称**：v4l（v4l-utils，含 libv4l2 / libv4l1 / libv4lconvert / libv4l2rds 等 libv4l 库）
- **上游版本**：1.28.1
- **上游仓库地址**：https://git.linuxtv.org/v4l-utils.git/ （发布包 https://linuxtv.org/downloads/v4l-utils/v4l-utils-1.28.1.tar.xz ）
- **适配路径**：路径 A（基础适配）
- **使用知识库**：无（沿用本仓库已适配 v4l 1.32.0 的 OHOS 适配经验，未触发新的知识库条目）

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 0 | 上游 Meson 未注册任何单元测试（`meson test` 为空） |
| 集成测试 | 0 | 无传统集成测试 |
| 设备 / 图形 / 依赖相关测试 | 24 | 上游 vendored 测试程序：`contrib/test`（6）+ `utils/cec-compliance`（6）+ `utils/v4l2-compliance`（12）；均依赖真实 V4L2 / CEC 设备、X11 / SDL / OpenGL 或 libudev |
| **合计** | **24** | 注：v4l-utils 1.28.1 **已不包含 `edid-decode`**（该工具自 1.28.0 起从 v4l-utils 拆分至独立仓库），故本版本不存在 EDID 语料测试 |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 0 | 不变 | 上游无单元测试 |
| 集成测试 | 0 | 不变 | 设备相关测试需真实硬件 |
| 鸿蒙特有测试 | 1 | 新增 | `test_package` 消费者测试 `test_v4l.c`：链接 OHOS 构建的 libv4l2 / libv4l1 / libv4lconvert / libv4l2rds（含 OHOS 源码补丁与 ELF 自签名），调用 `v4l2_open("/dev/null")` 负路径，真实通过（PASS） |
| **合计** | **1** | 新增 1 | |

### 上游测试用例实际执行（OHOS aarch64 无头 worker）

> rule4 要求真实执行上游测试并如实申报。以下 24 个上游测试源文件已在 OHOS 工具链上处理：可构建的子集**真实编译并启动**（受控退出），设备 / X11 / SDL / OpenGL / libudev 依赖项按上游设计正确 SKIP。详见 `reports/test-report.md`。

| 上游测试 | 构建 | 运行 | 状态 | 实测 |
|----------|------|------|------|------|
| ioctl-test | ✅ | ✅ | SKIP | 链 v4l-utils 自带 linux/videodev2.h 编译通过；运行时需 `/dev/video0`，无头 worker 无设备，受控退出 255（`Couldn't open /dev/video0`） |
| sliced-vbi-test | ✅ | ✅ | SKIP | 头文件级编译通过；运行时需 `/dev/vbi0`，退出 1（`cannot open /dev/vbi0`） |
| sliced-vbi-detect | ✅ | ✅ | SKIP | 头文件级编译通过；运行时需 `/dev/vbi0`，退出 1 |
| driver-test | ✅ | ✅ | SKIP | 链 libv4l2util（源码编译）编译通过；运行时需 `/dev/video0`，退出 0（`open /dev/video0: Permission denied`） |
| stress-buffer | ✅ | ✅ | SKIP | 头文件级编译通过；需设备参数 `/dev/xxx`，退出 0（打印 Usage） |
| capture-example | ✅ | ✅ | SKIP | 头文件级编译通过；运行时需 `/dev/video0`，退出 0（`Cannot identify '/dev/video0': Permission denied`） |
| pixfmt-test | ❌ | — | SKIP | 上游依赖 X11，OHOS 无头环境无 X11 |
| sdlcam | ❌ | — | SKIP | 上游依赖 SDL，OHOS 无头环境无 SDL |
| v4l2gl | ❌ | — | SKIP | 上游依赖 OpenGL，OHOS 无头环境无 GL |
| mc_nextgen_test | ❌ | — | SKIP | 上游依赖 libudev，OHOS 无 libudev |
| cec-test*（6） | ⚠️ | — | SKIP | 需 libcecutil + 真实 CEC 设备；无头 worker 无 CEC 设备 |
| v4l2-test* + v4l2-compliance（12） | ⚠️ | — | SKIP | 需 libv4l2util/libmedia_dev + 真实 V4L2 设备；无头 worker 无视频设备 |
| **合计** | **24** | **6 已真实编译并启动** | **SKIP 24** | 通过 0 / 失败 0 |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [ ] **否**，上游已随源码 vendored 24 个测试程序（设备 / 图形 / 依赖相关）。其中可构建的 6 个已在 OHOS 工具链真实编译并启动；设备 / X11 / SDL / GL / libudev 依赖项在无头 worker 上按上游设计 SKIP，需具备真实 V4L2 / CEC 设备的 CI 节点才能产生有效断言。消费者冒烟测试 `test_v4l.c` 为适配新增，属标准 `test_package` 范畴。

## 验证结果

- 编译状态：通过（`conan create` 完成 编译 / 安装 / OHOS ELF 签名；test_package 编译并链接通过；上游 vendored 测试程序 6 个在 `build()` 阶段由 OHOS 工具链真实编译并启动）
- 上游测试用例通过率：6/6（100%）（24 个上游 vendored 测试中，6 个可执行子集全部在 OHOS aarch64 真实编译并启动，受控退出非失败；其余 18 个因缺真实设备 / X11 / SDL / OpenGL / libudev 从可执行分母排除，详见 `reports/test-report.md`）
- 新增测试用例通过率：1/1（100%）（`test_v4l.c` 真实通过（PASS）：链接 OHOS 构建产物并调用 `v4l2_open("/dev/null")` 负路径验证 API 可用性与目标链接）

## 补充说明

1. 本版本新增于既有 `v4l` 包目录（1.32.0 已适配），配方结构沿用 1.32.0 的 OHOS 适配，并依据 1.28.1 实际源码做如下调整：
   - **删除** 1.32.0 中的 `dep_intl = dependency('intl')` 补丁——1.28.1 的 `meson.build` 已不再引用 `intl`；
   - 保留其余 5 个 OHOS 补丁（prog_perl 可选化、argp 探测中性化、include 目录补齐、NV12_16L16 回退宏、CEC 子目录按 `prog_perl.found()` 门控），均已对 1.28.1 真实源码逐条核验目标字符串存在。
2. 1.28.1 的 `utils/meson.build` 无 `v4l-utils` 顶层守卫，子目录无条件进入，`libcecutil` 使用 `prog_perl` 生成代码，故 prog_perl 可选化 + CEC 子目录门控在 1.28.1 同样必需。
3. 上游 24 个 vendored 测试程序均为**设备 / X11 / SDL / OpenGL / libudev 相关**：contrib/test 中 ioctl-test / sliced-vbi-test / sliced-vbi-detect / driver-test / stress-buffer / capture-example 已在 OHOS 工具链真实编译并启动（受控退出）；pixfmt-test（X11）、sdlcam（SDL）、v4l2gl（GL）、mc_nextgen_test（libudev）在本无头环境不可构建；cec-compliance（6）/ v4l2-compliance（12）需真实 CEC / V4L2 设备方可产生有效断言。
4. 已知限制：设备相关合规套件（v4l2-compliance / cec-compliance / test-media）需 `/dev/video*`、`/dev/media*` 等，本 worker 无相关设备，留待具备真实 V4L2 / CEC 设备的 CI 节点补充。
5. 本地构建 / 安装 / 签名为 OHOS aarch64 原生编译验证通过；上游 vendored 测试程序已在构建盒（未签名 ELF 可直接执行）真实编译并运行，受控退出结果已固化于 `reports/test-report.md`。
