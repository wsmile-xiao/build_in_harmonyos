# GNU Hello

## 软件简介

GNU Hello 是 GNU 项目的示例程序，用于展示 GNU 软件的标准结构和特性。

- **官方网站**: https://www.gnu.org/software/hello/
- **源码仓库**: https://ftp.gnu.org/gnu/hello/
- **许可证**: GPLv3+

## 已编译版本

- hello 2.12 (2026-05-21)

## 编译说明

### 构建系统

- Autotools (autoconf + automake)

### 关键补丁

编译过程中应用了 3 个功能性补丁：

1. **0001-build-aux-config.guess.patch**
   - 添加 HarmonyOS 系统识别分支
   - 输出标准三元组: aarch64-unknown-linux-ohos

2. **0002-build-aux-config.sub.patch**
   - 在 kernel-os 白名单中添加 linux-ohos*
   - 解决三元组验证失败问题

3. **0003-configure.patch**
   - 修改 umask 077 为 umask 022
   - 解决 HMDFS UID 映射导致的临时目录权限问题 (E011)

### 已知问题

1. **文档编译依赖缺失**
   - makeinfo (texinfo) 未预装
   - 解决方案: 跳过文档编译（SUBDIRS=lib src）

2. **gnulib 替换函数链接失败**
   - rpl_optarg, rpl_getopt_long, rpl_optind, error 等符号未定义
   - 解决方案: 手动编译 getopt.o、getopt1.o、error.o 并重新打包静态库

### 平台适配要点

- config.guess 和 config.sub 需要同时修改才能完整支持 HarmonyOS
- configure 的 umask 修改是 HMDFS 平台的通用解决方案
- autotools 项目在鸿蒙上的编译需要处理多个平台限制