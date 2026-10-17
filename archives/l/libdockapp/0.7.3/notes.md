# libdockapp 0.7.3 适配笔记

## 概述

libdockapp 是用于编写 Window Maker dock application 的 C 库。上游 0.7.3
使用 Autotools 构建，安装 `libdockapp.so.3.0.1`、四个公共头文件和
`dockapp.pc`。

## OHOS 适配要点

- 依赖固定为同一条已发布 X11 轨道：`libx11/6.4.0`、
  `libxext/6.4.0`、`libxpm/3.5.17`。
- 上游 2018 年版 `config.guess`/`config.sub` 不识别 HarmonyOS。补丁
  `0001-config.guess.patch` 直接识别 HarmonyOS aarch64，补丁
  `0002-config.sub.patch` 接受并规范化 `linux-ohos` 目标。
- configure 以 `--host=aarch64-linux-ohos` 进入交叉编译模式，并使用
  `/system/bin/sh`。构建目录中的 configure 副本仅把两个 `umask 077`
  调整为 `umask 022`，避免真机受限目录权限问题，不改动上游源码。
- font 与 examples 是可选安装内容；库包使用 `--without-font` 和
  `--without-examples`，不引入 X 服务器或 font-util 运行要求。上游的
  `XORG_FONT_COMMON_UTILS` 即使 font 子目录关闭仍会强制查找 `mkfontdir`，因此
  配置阶段将未执行的 `MKFONTDIR` 指向 `/system/bin/true`。
- 私有 linker view 重定位依赖的 libtool 元数据，避免依赖缓存绝对路径写入
  产物。安装后使用 `patchelf` 删除临时 RUNPATH，删除 `.la`，并把
  `dockapp.pc` 的目录变量和编译、链接参数改为相对 `pcfiledir` 的可重定位形式。
  ELF 重写后会移除旧 `.codesign` 并重新自签名，避免真机加载器拒绝失效签名。

## 测试

上游发布包没有 `TESTS` 或 `check_PROGRAMS`，因此 `make check` 的实测上游
测试数为 0；配方仍在每次构建中执行该标准目标。`test_package` 通过安装后的
CMake target 链接真实共享库，并运行 25 项断言，覆盖：

- 版本常量及 Display、Window、Leader、Icon、Depth、Visual 状态 API；
- 链表创建、索引、查找、遍历、删除与释放；
- 带单引号和双引号的命令行解析；
- HarmonyOS PC aarch64 指针宽度（`__OHOS__` 条件下执行的特有测试）。

测试路径不连接 X server，适合 CI 与真机无图形会话执行。OHOS ELF 在运行前
使用系统 `binary-sign-tool` 自签名并检查唯一 `.codesign` 节。

## 验证命令

```bash
conan create archives/l/libdockapp/0.7.3 \
  -pr:h ci/conan/profiles/ohos-aarch64 \
  -pr:b ci/conan/profiles/ohos-aarch64 \
  --build=libdockapp/0.7.3
```
