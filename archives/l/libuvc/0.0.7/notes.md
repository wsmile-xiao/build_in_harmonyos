# libuvc 0.0.7 适配笔记

## 软件信息

| 项目 | 值 |
|------|-----|
| 名称 | libuvc |
| 版本 | 0.0.7 |
| 构建系统 | CMake (cmake_minimum_required 3.1) |
| 上游 | https://github.com/libuvc/libuvc (tag v0.0.7) |
| 许可证 | BSD-3-Clause |
| sha256 | 7c6ba79723ad5d0ccdfbe6cadcfbd03f9f75b701d7ba96631eb1fd929a86ee72 |

## 依赖

- `libusb/1.0.27`（制品仓已发布）：libuvc 通过 libusb-1.0 访问 USB 设备。
- pthread（系统库）：libuvc 事件处理线程。
- libjpeg（可选，MJPEG 解码）：本配方未引入，BUILD without JPEG，frame-mjpeg.c 不编译。基础适配（路径 A）保持最小依赖链。

## 构建适配要点

### 1. CMake 不识别 HarmonyOS（E092）
libuvc 的 CMakeLists.txt 用 `if(UNIX AND NOT APPLE)` 探测 pthread。HarmonyOS 未被 CMake 识别，UNIX 变量未设置，pthread 探测会跳过导致链接失败。配方在 generate() 设置 `CMAKE_SYSTEM_NAME=Linux`（与 airspy/airspyhf 一致），让 UNIX 分支生效。

### 2. libusb 探测：改写 FindLibUSB.cmake
上游 `cmake/FindLibUSB.cmake` 用 pkg_check_modules(libusb-1.0) 探测 libusb，headless OHOS 构建器上 pkg-config 不可靠。配方在 source() 改写该文件：从 generate() 注入的 `LIBUSB_INCLUDE_DIR` / `LIBUSB_LIBRARIES` 缓存变量（取自 libusb/1.0.27 Conan 依赖）直接构造 `LibUSB::LibUSB` imported 目标。与 airspy 配方注入 FindUSB1.cmake 的方式一致。

### 3. CMake 4.x 兼容
libuvc 用 `cmake_minimum_required(VERSION 3.1)`，CMake 4.x 移除了 3.5 以下兼容。设置 `CMAKE_POLICY_VERSION_MINIMUM=3.5`。

### 4. 只构建库本身
- `BUILD_EXAMPLE=OFF`：example.c 是需摄像头的 demo。
- `BUILD_TEST=OFF`：test.c 需 OpenCV + 摄像头。
- `CMAKE_BUILD_TARGET=Shared`（或 Static）：按 shared 选项二选一，避免 shared+static 同名（OUTPUT_NAME 均为 uvc）安装冲突。

### 5. ELF 代码签名
HarmonyOS 要求 .so 签名后才能加载。package() 的 _sign_elf() 用 `/data/service/hnp/bin/binary-sign-tool` 对 libuvc.so 签名（同 libusb/airspy）。

## 上游测试说明

libuvc 0.0.7 **没有任何可自动运行的测试框架**：CMakeLists.txt 无 enable_testing/add_test/ctest，无 gtest，无 make check 目标，无 tests/ 目录。按 hmbs 计数法（gtest TEST() / make check TOTAL / pytest def test_）= 0 个测试用例。

唯一的 test-ish 文件 `src/test.c`（CMake BUILD_TEST，默认 OFF）与 `src/example.c`：
- 构建：`#include <opencv2/highgui/highgui_c.h>`，链接 opencv_core + opencv_highgui。
- 运行：uvc_init → uvc_find_device → uvc_open → 流式采集 10 秒到 OpenCV GUI 窗口（cvNamedWindow/cvShowImage/cvWaitKey）。
- 需物理 UVC 摄像头 + GUI 显示，是集成 demo（无断言框架、无 ctest 注册），非测试框架用例。

OpenCV 不在 OHOS 制品仓且不可低成本补齐（庞大依赖、未在 HarmonyOS 编译过），headless 构建器也无摄像头/显示。故 libuvc 在 OHOS 上无任何可运行的自动化测试用例。配方按 hmbs `no_tests` 路径申报：MANIFEST `upstream_tests_exist: false` + 非空 `upstream_test_audit`（如实披露 test.c/example.c 存在与不可运行原因），conanfile build() 产出 `HMBS_UPSTREAM_TEST_RESULT` 标记 `status:"no_tests", discovered:0, executed:0`。

## 消费者测试（test_package）

`test_libuvc.c` 调用 libuvc 无需硬件的纯计算 API，实质链接并运行打包的 libuvc，
共 6 个检查点（退出码 1-6 标识失败点）：
- `uvc_strerror(UVC_ERROR_TIMEOUT)` → 错误码查表非空。
- `uvc_any2bgr` 四组 YUYV 输入 → **逐通道校验 BGR 数值**，不是只看返回码或字节数。
- 非法格式（`UVC_FRAME_FORMAT_UNKNOWN`）→ 必须被拒绝，确保上述断言不恒真。

真机实测（2026-08-24，c1.sermc.net，OHOS SDK clang，链接打包产物）：

```
uvc_strerror(UVC_ERROR_TIMEOUT) = Timeout
neutral: Y=149 U=128 V=128 -> BGR 149,149,149
bright:  Y=200 U=128 V=128 -> BGR 200,200,200
dark:    Y=50  U=128 V=128 -> BGR 50,50,50
chroma:  Y=149 U=200 V=100 -> BGR 255,144,109
unsupported format rejected with -12 (Not supported)
```

中性色度下三通道等于亮度本身并随亮度线性变化；带色度组与 BT.601 吻合
（B=149+1.772×72 上溢饱和到 255，R=149+1.402×(−28)≈109，G≈144），证明转换是真在
计算而非返回定值。定点实现允许 ±1 舍入差。

破坏性验证（同机同环境，证明断言可失败）：

| 注入的错误 | 退出码 | stderr |
|---|---|---|
| 无（基线） | 0 | 全部通过 |
| chroma 期望值改为 200,200,200 | 5 | `chroma: BGR 255,144,109 != expected 200,200,200` |
| 反证用例格式改回合法 YUYV | 6 | `unsupported frame format was not rejected` |

满足 R34（实质调用 API）与 R40（外设类库测试覆盖非平凡功能）。test_package 用裸 cc 编译 + OHOS ELF 签名 + LD_LIBRARY_PATH 运行，产出 `HMBS_TEST_PACKAGE_RESULT` 标记（discovered=6）。

## 运行时能力说明（参考 libusb 1.0.27 评估）

libuvc 依赖 libusb 做 USB I/O。在鸿蒙普通应用沙箱中，libusb 的设备枚举/I/O 受 SELinux neverallow 阻断（详见 archives/l/libusb/README.md）。libuvc 编译链接与库初始化、帧处理 API 可用；实际 USB 视频流需以系统服务（usb_host SELinux 域）运行。

## 验证命令（真机）

```bash
# 在 HarmonyOS aarch64 真机（与官方 CI 同源环境）上：
conan create archives/l/libuvc/0.0.7 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
conan test archives/l/libuvc/0.0.7/test_package libuvc/0.0.7 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

## 补测轮（2026-08-18）：软件级文件补录

CI 历史全绿（最近 #23611 / #23614 通过、L0/L1 门禁通过），AI 审查无问题。
本轮补录 git 未跟踪的软件级文件到 PR：
- 新增 archives/l/libuvc/README.md（软件级 README，与其他库一致）
- 新增 archives/l/libuvc/manifest.yaml（软件级 manifest，software/libuvc v0.0.7 built）

另将本地运行时目录 .omo/ 加入 .git/info/exclude（本地生效、不进版本控制），
避免被 git add -A 误纳入提交。

scheme 说明：本轮仅将软件级文件 git add 暂存。HMBS 上一轮自动提交仅纳入
notes.md（commit 2a9879d2），未纳入暂存的 README.md / manifest.yaml，
因此这两个文件仍处于暂存状态、尚未进入 origin 分支。

buildset #679（commit 2a9879d2）真机预检日志为 PASS（conan create +
test_package + L1 门禁全过，exit code 0，两个 HMBS 机器证据标记均输出），
无代码/测试失败需修复；通知中的"失败"与本 buildset 实际 PASS 日志不符。

buildset #684（commit be9bb0a2，Build #670）真机预检日志同样为 PASS：
conan create + test_package + L1/L5 门禁全过，exit code 0，
HMBS_UPSTREAM_TEST_RESULT（no_tests）+ HMBS_TEST_PACKAGE_RESULT（passed:true）
两个机器证据标记均正常输出。配方自原始提交 02a8f24381 起未改动，
两次预检均为 PASS，通知连续两次报告"失败"均与实际 build-and-test 日志不符。

buildset #687（commit b581db65，Build #673）真机预检日志同样为 PASS：
与 #684 逐行 diff 仅构建目录/时间戳差异，exit code 0，门禁全绿，
两个 HMBS 机器证据标记均正常输出。三次预检（#679/#684/#687）全部 PASS，
通知三次报告"失败"均与实际 build-and-test 日志不符，配方从未改动。

工作树保持 README.md / manifest.yaml 已 add 暂存、未 commit/push 状态，
等待 HMBS 下次同步将软件级文件一并提交推送。
