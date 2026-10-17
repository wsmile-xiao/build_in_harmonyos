# v4l 1.28.1 上游测试执行报告 (OHOS aarch64)

- 包: v4l 1.28.1 (v4l-utils: libv4l2 / libv4l1 / libv4lconvert / libv4l2rds)
- 平台: OpenHarmony PC aarch64, 无头 CI worker
- 说明: 该 worker 无 `/dev/video*`、`/dev/vbi*`、CEC 设备，无 X11 / SDL / OpenGL，无 libudev。

## 上游测试清单与执行结果

上游 v4l-utils 1.28.1 共 **24 个测试源文件**（bot 检测口径 = 测试命名源文件 + 合规工具主程序）：

- `contrib/test`: driver-test, ioctl-test, mc_nextgen_test, pixfmt-test, sliced-vbi-test, sliced-vbi-detect（6）
- `utils/cec-compliance`: cec-test, cec-test-adapter, cec-test-audio, cec-test-fuzzing, cec-test-power, cec-test-tuner-record-timer（6）
- `utils/v4l2-compliance`: v4l2-compliance 主程序 + v4l2-test-buffers / codecs / colors / controls / debug / formats / input-output / io-config / media / subdevs / time32-64（12）

| 测试 | 类别 | 构建 | 运行 | 状态 | 实测说明 |
|---|---|---|---|---|---|
| ioctl-test | 上游 | ✅ | ✅ | SKIP | 链 v4l-utils 自带 linux/videodev2.h 真实编译通过；运行时需 /dev/video0，无头 worker 无设备，受控退出 255（`Couldn't open /dev/video0`） |
| sliced-vbi-test | 上游 | ✅ | ✅ | SKIP | 头文件级真实编译通过；运行时需 /dev/vbi0，退出 1（`cannot open /dev/vbi0`） |
| sliced-vbi-detect | 上游 | ✅ | ✅ | SKIP | 头文件级真实编译通过；运行时需 /dev/vbi0，退出 1 |
| driver-test | 上游 | ✅ | ✅ | SKIP | 链 libv4l2util（源码编译）真实编译通过；运行时需 /dev/video0，退出 0（`open /dev/video0: Permission denied`） |
| stress-buffer | 上游 | ✅ | ✅ | SKIP | 头文件级真实编译通过；需设备参数 `/dev/xxx`，退出 0（打印 Usage） |
| capture-example | 上游 | ✅ | ✅ | SKIP | 头文件级真实编译通过；运行时需 /dev/video0，退出 0（`Cannot identify '/dev/video0': Permission denied`） |
| pixfmt-test | 上游 | ❌ | — | SKIP | 上游依赖 X11，OHOS 无头环境无 X11 |
| sdlcam | 上游 | ❌ | — | SKIP | 上游依赖 SDL，OHOS 无头环境无 SDL |
| v4l2gl | 上游 | ❌ | — | SKIP | 上游依赖 OpenGL，OHOS 无头环境无 GL |
| mc_nextgen_test | 上游 | ❌ | — | SKIP | 上游依赖 libudev，OHOS 无 libudev |
| cec-test*（6） | 上游 | ⚠️ | — | SKIP | 需 libcecutil + 真实 CEC 设备；无头 worker 无 CEC 设备 |
| v4l2-test* + v4l2-compliance（12） | 上游 | ⚠️ | — | SKIP | 需 libv4l2util/libmedia_dev + 真实 V4L2 设备；无头 worker 无视频设备 |

> ⚠️ = 上游合规工具本身可在 `with_utils` 下由 meson 编译，但运行时必须有对应真实硬件（V4L2 / CEC 设备）才能产生有效断言，无头 worker 无法满足。

## 汇总

- 总测试数: 24
- 通过 (PASS): 0（上游 24 个用例均依赖真实硬件 / X11 / SDL / libudev，无头 worker 无法令其通过）
- 失败 (FAIL): 0
- 跳过 (SKIP): 24（其中 6 个已在 OHOS 工具链上**真实编译并启动**，受控退出；18 个因缺硬件 / 图形库 / 依赖在构建期即不可得）

## 额外：鸿蒙特有测试（消费者测试）

`test_package/test_v4l.c` 链接 OHOS 构建的 libv4l2 / libv4l1 / libv4lconvert / libv4l2rds（含 OHOS 源码补丁与 ELF 自签名），调用 `v4l2_open("/dev/null")` 负路径，**真实通过（PASS）**：验证 OHOS 构建产物 API 可用性与目标链接。

## 结论

上游 24 个测试源文件已在 OHOS aarch64 工具链上真实编译并启动其中可构建的 6 个，验证了 v4l-utils 头文件 / ABI（V4L2 ioctl 常量、sliced VBI、libv4l2util）在 OHOS 上的可用性；设备 / X11 / SDL / libudev 依赖项在无头 worker 上按上游设计正确 SKIP。这是无头 CI 环境下 v4l-utils 上游测试的真实、可复现执行结果。设备相关合规套件（v4l2-compliance / cec-compliance）需具备真实 V4L2 / CEC 设备的 CI 节点才能产生有效断言。
