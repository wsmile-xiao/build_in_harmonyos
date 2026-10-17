# PC6001VX

PC-6001 / PC-6001mkII / PC-6601 模拟器（NEC PC-6001 系列），eighttails 的
PC6001V 跨平台重制版：Qt6 图形界面 + Qt Multimedia 声音输出 + SDL2 手柄输入，
由 qmake 构建。

- 上游：<https://github.com/eighttails/PC6001VX>
- 许可证：LGPL-2.1-or-later
- 包类型：GUI 应用（单可执行文件 `bin/PC6001VX`）

## HarmonyOS PC 适配

构建链按上游真实情况（**Qt6 + qmake**，不是 SDL2 图形栈）：依赖制品仓
`qtbase/6.11.1`、`qtmultimedia/6.11.1`、`sdl2/2.30.10`（静态），并用
`tool_requires` 引入 `qttools/6.11.1` 的 `lrelease` 生成翻译资源。

关键适配点（详见各版本 `notes.md`）：

- Qt6 qmake 工程在 conan 的 split-prefix Qt 安装下无法用 `QT += multimedia`
  解析模块路径 → 补丁改为由配方传入显式 `INCLUDEPATH`/`LIBS`。
- qtbase 无 OpenGL、QPA 平台插件只有 `minimal`/`offscreen` → `NO_HWACCEL`，
  并让 X11(xcb) 后端可关闭（`P6VX_NO_X11`）。
- OHOS 无 SysV 信号量（`semget` 不可用）→ Qt `QSharedMemory`/上游
  `SingleApplication` 单实例逻辑不可用，采用上游开关 `NOSINGLEAPP`。
- musl 无 `<libintl.h>` → `NOLIBINTL`（上游 Android 同款）。
- 无头冒烟执行 `bin/PC6001VX` 的纯 IO 退出路径（`--version`/`--help`/
  参数错误/缺平台插件诊断），不跑会常驻事件循环的正常启动路径。

## 版本

- `4.3.0` — 首次 HarmonyOS PC 适配（`built`）

## 使用方法

```bash
# 无头/容器环境（CI 冒烟）
QT_QPA_PLATFORM=offscreen bin/PC6001VX --version    # PC6001VX 4.3.0
QT_QPA_PLATFORM=offscreen bin/PC6001VX --help

# 桌面环境（需要 Qt 的 OHOS QPA 平台插件，见已知限制）
bin/PC6001VX
```

## 已知限制

1. 制品仓 `qtbase/6.11.1` 只提供 `minimal`/`offscreen` 两个 QPA 插件，真机桌面
   窗口显示需要平台补齐 Qt 的 OHOS 平台插件；CI 覆盖到"二进制可执行 + 无头
   退出路径"。
2. `qtmultimedia/6.11.1` 无可用音频后端插件（只有测试用 mock 插件），音频输出
   代码路径完整但真机有声输出待平台补齐。
3. `NOSINGLEAPP` 后不再限制多实例；`NO_HWACCEL` 后走软件渲染路径。
4. 手柄输入代码已编入且 SDL2 静态链接，真机手柄设备未实测。
