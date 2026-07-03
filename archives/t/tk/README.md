# Tk (GUI Toolkit for Tcl)

## 简介
Tk 是 Tcl 的图形界面工具包，提供按钮、画布、文本框等 GUI 组件。依赖 Tcl。

## 编译版本
- **9.0.3.1** (2026-07-03) — Tk 9.0，**动态库**形态（`libtcl9tk9.0.so`），依赖 `tcl/9.0.3.1@ohpcd/stable`

## 编译信息
- 构建系统: Autotools（标准 conan，CI 原生 clang）
- 编译器: Clang（OHOS NDK）
- 平台: HarmonyOS PC / HongMeng Kernel

## OHOS 适配要点
- 产**动态** `libtcl9tk9.0.so`，依赖 tcl：
  - configure `--with-tcl=<tcl包>/lib`（找 tclConfig.sh）+ conan `AutotoolsDeps`/`PkgConfigDeps` 注入 tcl 的 -I/-L/-l；
- `--disable-zipfs` 出**干净 ELF**（避免脚本库 zip 尾拼破坏链接器自签）→ 链接器自签有效、独立 dlopen 可加载；
- 脚本库以**散文件**装 `lib/tk9.0`，运行期靠 `TK_LIBRARY`；
- 系统识别 uname shim + `tcl_cv_sys_version=Linux-6.6`；`umask 077→022`（E011）。

## 安装产物
- `libtcl9tk9.0.so`（动态库）、`tkConfig.sh`、`libtkstub.a`、公共头、`lib/tk9.0/`（散脚本库）

## 依赖关系
- `tcl/9.0.3.1@ohpcd/stable`

## 相关链接
- 官网: https://www.tcl-lang.org/
- 源码: https://raw.gitcode.com/OpenHarmonyPCDeveloper/ohos_tk
