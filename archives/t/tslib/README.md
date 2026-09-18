# tslib

触摸屏访问库（Touchscreen Access Library），为 Linux/鸿蒙 evdev 触摸设备提供统一
读取接口，附校准、过滤插件与诊断工具。

- 上游：https://github.com/libts/tslib
- 许可证：LGPL-2.1（库）；tests/tools 工具程序为 GPL
- 类型：库 + 诊断工具

## HarmonyOS PC 适配要点

- HMDFS 上 configure 的 `umask 077` mktemp 临时目录不可写（知识 E011），
  补丁放宽为 `umask 022`。
- OHOS 适配版 conan 不把 `tools.build:compiler_executables` 映射为 CC/CXX，
  配方显式注入编译器环境（adplay/1.9 先例）。
- 2018 年 config.sub/config.guess 不识别 ohos，显式
  `--build/--host=aarch64-unknown-linux-gnu`。
- 共享库构建（`--enable-shared --disable-static`）：14 个过滤/输入模块为
  运行期 dlopen 插件（`lib/ts`），静态库无法支撑插件架构。

详见各版本目录下的 `notes.md`。

## 版本

- `1.22` — 首次适配（built）
