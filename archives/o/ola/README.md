# ola — Open Lighting Architecture

OLA（Open Lighting Architecture）是 DMX512 灯光控制框架：通过
Art-Net / sACN(E1.31) / ESP-Net / Pathport / ShowNet / KiNet / SandNet
等 IP 协议控制舞台灯光设备，并提供 `olad` 守护进程将 IP 协议桥接到
本地 DMX 硬件。C++ 客户端库（libolacommon / libola / libolaserver）
供灯光控制软件集成。

## Versions in this archive

- `0.10.9/` — OpenHarmony PC (aarch64) port，静态构建，路径 A

## License

双许可：
- **LGPL-2.1-or-later**：客户端库（libolacommon / libola）
- **GPL-2.0-or-later**：守护进程、工具与插件（olad / ola_trigger / 各协议插件）

下游使用需同时遵守两份许可条款。
