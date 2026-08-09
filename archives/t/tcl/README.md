# TCL (Tool Command Language)

## 简介
TCL 是一种动态编程语言，由 John Ousterhout 创建。它被设计为一种简单但强大的脚本语言，常用于快速原型开发、脚本编写、GUI 开发（通过 Tk）和测试自动化。

## 主要特点
- 简洁的语法，易于学习和使用
- 跨平台支持（包括 HarmonyOS）
- 可扩展性强，可通过 C/C++ 扩展
- 内置强大的字符串处理功能
- 支持 OOP（通过 TclOO）

## 编译版本
- **9.0.3.1** (2026-07-02) — Tcl 9.0，**动态库**形态（`libtcl9.0.so` 供 dlopen；及作 tk 等的依赖）
- **8.6.16** (2026-07-29) — Tcl 8.6，动态形态（`libtcl8.6.so` + `tclsh8.6` 终端工具）

## 编译信息
- 构建系统: 9.0.3.1 = Autotools（标准 conan，CI 原生 clang）；8.6.16 = Autotools
- 编译器: Clang（OHOS NDK）
- 平台: HarmonyOS PC / HongMeng Kernel

## OHOS 适配要点
- 9.0.3.1 产**动态** `libtcl9.0.so`（非系统同名库，R26 默认动态），供设备上 dlopen；
- `--disable-zipfs` 出**干净 ELF**（避免脚本库 zip 尾拼破坏链接器自签）→ 链接器自签有效、独立 dlopen 可加载、无需显式重签；
- 脚本库以**散文件**装 `lib/tcl9.0`，运行期靠 `TCL_LIBRARY` 指过去；
- 系统识别 uname shim + `tcl_cv_sys_version=Linux-6.6`；`umask 077→022`（E011）；跳过可选子包。

## 安装产物
- **9.0.3.1**：`libtcl9.0.so`（动态库）、`bin/tclsh`、`tclConfig.sh`、`libtclstub.a`、公共头、`lib/tcl9.0/`（散脚本库）
- **8.6.16**：`libtcl8.6.so`（动态库）、`tclsh8.6`、`libtclstub8.6.a`、公共头、`tclConfig.sh`

## 使用示例
```tcl
#!/usr/bin/tclsh8.6
puts "Hello from TCL!"
puts [info patchlevel]
```

## 依赖关系
TCL 通常不需要外部依赖，但在某些平台上可能需要：
- zlib（可选，用于压缩支持）

## 相关链接
- 官网: https://www.tcl.tk/
- 文档: https://www.tcl.tk/man/
- 源码: https://sourceforge.net/projects/tcl/
