# librevisa

VISA (Virtual Instrument Software Architecture) 仪器控制标准的自由软件实现
(上游：[~sjr/librevisa](https://git.sr.ht/~sjr/librevisa)，GPL-3.0-or-later)。

提供完整的 VISA C API (`visa.h`/`visatype.h`)：`viOpenDefaultRM` 资源管理、
`viFindRsrc`/`viOpen`/`viClose` 会话管理、`viRead`/`viWrite` 基本 I/O、
`viPrintf`/`viScanf` 格式化 I/O、事件与锁 (`viEnableEvent`/`viWaitOnEvent`/
`viLock`) 等。产物为 `libvisa` 库。

可选后端 (libusb / Avahi / VXI) 由 configure 自动探测；OHOS 缺失时回退到
可移植核心。上游 `tests/` 含 22 个基于 DUMMY 资源的测试，无需真实仪器。

## 已适配版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 0.0.20130812 | built | 2026-09-26 完成配方，待真机 rule4 门禁验证 |
