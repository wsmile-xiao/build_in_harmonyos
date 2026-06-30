# open-ocd 0.12.0 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-05-28
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 下载源码：`openocd-0.12.0.tar.gz`（已存在于本地）
2. 初始化编译环境：`ohc-run.py init-build open-ocd 0.12.0 --url=file:///...`
3. 修改 configure 的 umask：`sed -i 's/umask 077/umask 000/g' configure`
4. 修改 config.guess：添加 HarmonyOS 分支识别
5. 修改 config.sub：添加 ohos 三元组验证支持
6. 配置 jimtcl 子项目：在源码目录中单独配置和编译
7. 配置 libjaylink 子项目：复制 config.guess/config.sub 并配置
8. 运行 configure：VPATH 构建模式
9. 禁用 -Werror：移除编译选项中的 -Werror
10. 运行 make：编译成功
11. 运行 make install：安装到 staging 目录

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 无法创建临时文件 | HMDFS umask 077 权限限制 | 修改 configure 中 umask 077 为 umask 000 |
| 2 | config.guess 无法识别 HarmonyOS | 脚本不包含 __OHOS__ 检测 | 添加 HarmonyOS 分支，使用 echo+exit 0 格式 |
| 3 | config.sub 验证 ohos 失败 | ohos 不在白名单中 | 在 maybe_os 和 kernel-os 行添加 ohos 支持 |
| 4 | jimtcl 配置失败 | autosetup-config.guess 权限问题 | 修改 autosetup-config.guess 的 umask 和 HarmonyOS 分支 |
| 5 | jimtcl configure.gnu 格式错误 | 文件包含 -e 字符 | 使用 Python 重写 configure.gnu |
| 6 | 函数原型警告 | target_call_timer_callbacks() 缺少 (void) | 添加 (void) 参数声明 |
| 7 | 未使用变量警告导致编译失败 | 源码包含 num_regs 等警告 | 禁用 -Werror 编译选项 |

## 源码修改

修改文件列表：
- configure（umask 权限修复）
- build-aux/config.guess（HarmonyOS 识别）
- build-aux/config.sub（ohos 三元组验证）
- jimtcl/autosetup/autosetup-config.guess（umask 和 HarmonyOS）
- jimtcl/configure.gnu（重写文件格式）
- src/target/target.c（函数原型修复）
- src/jtag/drivers/libjaylink/configure（umask）
- src/jtag/drivers/libjaylink/build-aux/config.guess/config.sub（复制）

补丁文件：0001-hmdfs-permission-and-harmonyos-support.patch

## 依赖版本

- clang 15.0.4
- make 4.4.1
- autoconf 2.72
- pkg-config 0.29.2

## 验证结果

```bash
~/builds/open-ocd-0.12.0-build/src/openocd --version
Open On-Chip Debugger 0.12.0
Licensed under GNU GPL v2
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| openocd | 12MB | 主二进制文件 |
| scripts/ | ~ | 配置脚本目录 |

## 注意事项

- HMDFS 文件系统存在 UID 映射问题，导致临时文件创建失败
- 禁用 -Werror 是快速完成编译的方案，源码本身包含一些警告
- jimtcl 子项目需要单独在源码目录中编译，VPATH 构建不完全支持
