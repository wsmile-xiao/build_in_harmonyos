# libdebian-installer

## 软件描述
libdebian-installer 是 Debian 安装器（debian-installer）使用的基础库，提供磁盘分区、文件系统、包管理等安装过程中的底层能力。本项目将其适配到 HarmonyOS PC（OHOS）平台。

## 功能概述
- **系统信息**：系统包、硬件、分区的探测与枚举
- **文件系统**：文件系统类型识别与挂载辅助
- **安装支持**：debian-installer 流程所需的底层抽象

## OHOS 适配

### 构建方式
- **构建系统**：autotools（无现成 configure——autoreconf 生成）
- **交叉编译**：`--build=aarch64-unknown-linux-ohos`
- **编译器**：clang 15

### 关键攻坚点
1. **autoreconf 工具链**：环境 automake-1.17 缺 Automake/Config.pm——`PERL5LIB` 指向 automake-1.16；autoconf 需 `AUTOCONF` 环境变量指向有效路径
2. **configure.ac 版本检测**：`AC_INIT` 用 `m4_esyscmd(dpkg-parsechangelog)` 取版本（环境无 dpkg）——硬编码 0.121
3. **PKG_CHECK_MODULES 宏**：系统无 pkg.m4 导致 configure 语法错误——注释测试框架 CHECK 行（构建不需要）
4. **config.status mktemp 沙箱限制**：TMPDIR 指可写目录 + `ac_tmp` 替换为固定可写目录（同 dpkg——见 SKILL `autotools-config-status-mktemp-sandbox`）

### 与 Linux 的差异
- 静态库打包（libsystem.a、libdebian-installer.a、libdebian-installer-extra.a）
- 测试框架（check）依赖已移除

## 依赖关系
无外部依赖（纯 C 库）。

## 版本记录
| 版本 | 状态 | 编译日期 | 备注 |
|------|------|---------|------|
| 0.121 | built | 2026-08-27 | Conan 配方适配 |

## 参考资料
- 上游仓库: https://salsa.debian.org/installer-team/libdebian-installer
- 源码: https://deb.debian.org/debian/pool/main/libd/libdebian-installer/
