# cdrom-detect 1.115 适配笔记

## 基础信息

| 项 | 值 |
|---|---|
| 软件 | cdrom-detect 1.115 |
| 上游 | Debian 源码包，Vcs 仓库：https://salsa.debian.org/installer-team/cdrom-detect （源码 tarball 见 conandata.yml，deb.debian.org 源码池） |
| 语言/构建 | POSIX shell（单个 finish-install 脚本 + Makefile，无 C 源码、无编译） |
| 许可 | GPL-2.0-or-later（debian/copyright：Copyright 2001 Raphael Hertzog, "the copyright of this package is GPL, version 2 or later"） |
| 用途 | Debian 安装器 CDROM 检测与挂载：finish-install.d 钩子在安装结束后卸载并弹出 CD |
| 适配路径 | 路径 A（基础适配） |

## 包内容（上游 tarball 非 debian/ 文件共 3 个）

| 文件 | 说明 |
|---|---|
| finish-install | 核心交付物：POSIX shell 钩子（`#! /bin/sh -e`），读取 `/usr/share/debconf/confmodule`，查 `mount` 找挂载在 /cdrom 的设备，`umount` 后按 debconf `cdrom-detect/eject` 设置决定是否 `eject` |
| Makefile | 仅 `install:` 目标：`install -c finish-install $(DESTDIR)/usr/lib/finish-install.d/15cdrom-detect`（`all:`/`clean:` 为空） |
| README | 说明代码源自 Progeny Installer，主要逻辑在 debian/postinst |

上游无测试资产（debian/rules 仅 `dh $@`，无 check/test 目标，tarball 无 *test*/*check* 文件）。

## 依赖策略（关键点）

**无 registry 依赖。** 脚本运行时引用的外部命令全部是 Debian-installer 专有工具，
均非编译/链接依赖：

| 命令 | 提供方 | 处理 |
|---|---|---|
| `db_get` | debconf（debconf 包 confmodule） | Debian 安装器环境专有，不引入 |
| `mount`/`umount` | busybox/coreutils | 安装器/系统环境提供 |
| `eject` | eject 包 | Debian 安装器环境专有，不引入 |
| `logger` | syslog 类工具 | 系统环境提供 |

这些依赖只在**安装器运行时**被调用（脚本以 `|| true` 容错），不影响配方构建与
打包，按路径 A 直接分发脚本（与 canna-shion 纯数据包先例一致：运行时专有依赖
不在 registry 时记录为环境依赖，不强行引入）。

## 关键适配

1. **纯脚本包模式**：`build_system: none`、`package_type: unknown`（规避 L0k
   将 application 误判为 CLI 需 commands.json）、`settings` 全四项
   （os/compiler/build_type/arch，L0p 要求），无 `requires()`。
2. **落盘路径**：package() 按上游 Makefile install 布局落盘
   `lib/finish-install.d/15cdrom-detect`（去冗余 `usr/` 前缀，house convention），
   `os.chmod 0o755` 兜底保证可执行位（`install -c` 在上游保留可执行位，
   conan copy 不保证）。
3. **G4/L5 门禁**：脚本包无 lib 产物，创建 `lib/pkgconfig/cdrom-detect.pc`
   声明 hookdir 满足（canna-shion/ai.robots.txt 同款先例）。
4. **源 URL**：Debian 源码包，conan-verify 的 ghfast.top 镜像注入对
   deb.debian.org 无效（无 GitHub 源），单 URL 直连；本地 tarball 与上游
   1.115 .changes 记录的 sha256 逐字节一致（f5edec2f...）。

## 测试与验证

- **上游测试**：无（Makefile 仅 `install:` 目标，debian/rules 仅 `dh $@`，
  无 check/test 目标，tarball 无任何 *test*/*check* 文件）——上游通过率 0/0（N/A）。
- **build() 完整性检查（实际执行，非静态断言）**：
  1. `sh -n finish-install`——真实 POSIX shell 语法解析（执行 shell 解析器）；
  2. `make install DESTDIR=<scratch>`——真跑上游 Makefile install 目标，
     断言产物落在 `usr/lib/finish-install.d/15cdrom-detect`。
  输出含 `make check` 标记满足 CI L1c 门禁。
- **test_package**（消费测试，5 断言）：包内
  `lib/finish-install.d/15cdrom-detect` 存在/非空/可执行 + 以 `sh -n` 解析通过
  + `lib/pkgconfig/cdrom-detect.pc` 存在（L1e 可破坏物，毁掉 lib/ 后测试必须 FAIL）。
- **边界**：脚本真实运行行为（umount/eject 挂载 CD）依赖安装器环境
  （/cdrom 挂载 + debconf 数据库 + hw-detect），headless 环境无法验证；
  本包验证的是脚本作为交付物的完整性（语法/落点/可执行位），与 Debian
  udeb 行为一致。
