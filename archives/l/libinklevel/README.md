# libinklevel

读取喷墨打印机墨水余量的 C 库，支持 USB、并口（LP）与 BJNP 网络协议三种连接方式，
覆盖 Canon / Epson / HP 及 BJNP 兼容设备。

- 上游主页：https://libinklevel.sourceforge.net/
- 许可：GPL-2.0
- 构建系统：autotools（configure + libtool）
- 运行时依赖：`libusb/1.0.27`、`libxml2/2.15.3`（制品仓已发布，Conan 自动拉取）
- 公共 API：`inklevel.h` —— `get_ink_level()` / `get_version_string()`

## 版本索引

| 版本 | 状态 | 适配说明 |
|------|------|---------|
| 0.9.7 | published | 首次适配 HarmonyOS PC（aarch64-linux-ohos）：config.guess/config.sub 三元组补丁、configure mktemp 分支补丁（HMDFS）、bjnp-debug.c NDEBUG 缺符号修复；上游无测试套件，补齐消费者测试 4 例 |

## 使用方式

```python
self.requires("libinklevel/0.9.7")
```

链接目标名为 `libinklevel::libinklevel`（CMakeDeps）或 `inklevel`（PkgConfigDeps / 原始链接名）。
