# kinect-audio-setup

使 Microsoft Kinect 感应器的音频输入在 GNU/Linux 上可用。

当 Kinect 首次插入 USB 时表现为一个带 bulk 端点的通用 USB 设备；上传特定固件后，
设备重新枚举并暴露为 USB Audio Class (UAC) 设备。kinect-audio-setup 提供：

- **kinect_upload_fw** — 上传固件到通用 USB 设备（本仓库构建的 C 工具，静态链接 libusb-1.0）。
- **kinect_fetch_fw** — 安装时从网络下载固件（因固件不可再分发）。
- **udev 规则** — 设备插入时自动调用固件加载器，得到 USB Audio Class 设备。

官方上游：作者 Antonio Ospite 的官方 git 服务器
https://git.ao2.it/kinect-audio-setup.git （v0.5 tag）

本包（HarmonyOS PC arm64 Conan 配方）：`archives/k/kinect-audio-setup/0.5`

## 构建产物

- `sbin/kinect_upload_fw` — 命令行工具（静态链接 libusb-1.0.a，仅动态依赖 libc.so）

## 适配要点
- 纯 Makefile 构建系统（无 configure），依赖 libusb-1.0（pkg-config 发现）。
- OHOS 无 GNU install 命令，配方 package() 直接拷贝产物到 sbin。
- 上游无测试套件，test_package 以真实二进制实跑自证。

依赖：libusb/1.0.27（已发布到 ohpcd 制品仓）。