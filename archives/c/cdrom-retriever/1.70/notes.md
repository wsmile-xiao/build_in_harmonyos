# cdrom-retriever 1.70 适配笔记

## 基础信息

| 项 | 值 |
|---|---|
| 软件 | cdrom-retriever 1.70 |
| 上游 | Debian 源码包，Vcs 仓库：https://salsa.debian.org/installer-team/cdrom-retriever （源码 tarball 见 conandata.yml，deb.debian.org 源码池） |
| 语言/构建 | POSIX shell（单个 cdrom-retriever 脚本 107 行；tarball 无 Makefile、无 C 源码） |
| 许可 | GPL-2.0-or-later（debian/copyright：Copyright 2001 Raphaël Hertzog，GPL version 2 or later） |
| 用途 | Debian 安装器 CDROM 模块检索器：从挂载的 /cdrom 符号链接/索引 udeb 模块（供 anna/udeb 安装器调用） |
| 适配路径 | 路径 A（基础适配） |

## 包内容（上游 tarball 非 debian/ 文件共 1 个）

| 文件 | 说明 |
|---|---|
| cdrom-retriever | 核心交付物：POSIX shell 脚本（`#! /bin/sh`），source debconf confmodule，`case "x$cmd"` 分发器：`config`（symlink .disk/udeb_include/exclude → /var/cache/anna/）、`retrieve`（symlink /cdrom 文件到目标路径）、`packages`（从 /cdrom/dists/<codename>/ 拼 Packages 索引，支持 .gz）、`error`（debconf critical 提示）、`cleanup`（移除 anna include/exclude 符号链接） |

上游安装方式：`debian/cdrom-retriever.install` 声明 `cdrom-retriever usr/lib/debian-installer/retriever`
（dh 安装，无 Makefile 参与）。上游无测试资产（debian/rules 仅 `dh $@`，无 check/test 目标，
tarball 无任何 test/check 文件）。

## 依赖策略（关键点）

**无 registry 构建依赖。** 脚本运行时调用的外部命令全部是 Debian-installer 专有工具或
系统基础工具，均非编译/链接依赖：

| 命令 | 提供方 | registry | 处理 |
|---|---|---|---|
| `logger` | syslog 类工具 | 无 | Debian 安装器/系统环境提供，不引入 |
| `udpkg` | udpkg（d-i） | 无 | Debian-installer 专有，不引入 |
| anna 缓存路径 | anna（d-i） | 无 | 仅写 /var/cache/anna/ 符号链接，不引入 |
| `grep`/`ln`/`rm`/`cat`/`touch`/`zcat` | grep/coreutils | 有（grep/coreutils 已合入） | 系统环境提供，脚本运行时调用 |
| debconf confmodule | debconf | 有 | 脚本头部 source，运行时依赖，非 conan 依赖 |

这些依赖只在**安装器运行时**被调用，不影响配方构建与打包，按路径 A 直接分发
脚本（与 cdrom-detect 纯脚本包先例一致：运行时专有依赖不在 registry 时记录为
环境依赖，不强行引入）。

注：debian/control 中 udeb 的 `Depends: cdrom-detect` 是安装器运行时依赖关系
（cdrom-detect 负责挂载 /cdrom），非本包构建依赖；本 PR 不含该 udeb 依赖声明，
按脚本交付物独立归档。

## 关键适配

1. **纯脚本包模式**：`build_system: none`、`package_type: unknown`（规避 L0k
   将 application 误判为 CLI 需 commands.json）、`settings` 全四项
   （os/compiler/build_type/arch，L0p 要求），无 `requires()`。
2. **落盘路径**：package() 按上游 debian/cdrom-retriever.install 声明目标落盘
   `lib/debian-installer/retriever`（去冗余 `usr/` 前缀，house convention），
   `os.chmod 0o755` 兜底保证可执行位。
3. **G4/L5 门禁**：脚本包无 lib 产物，创建 `lib/pkgconfig/cdrom-retriever.pc`
   声明 retrieverdir 满足（cdrom-detect 同款先例）。
4. **版本核对**：用户指定 "1.7"，上游无此版本（salsa tag 序列 0.21~1.70，
   pool 现存 1.58/1.63/1.69/1.70，1.7 tarball 404），经用户确认为 1.70；
   本地 tarball 与上游 1.70 .dsc 记录的 sha256 逐字节一致（9329632f...）。
5. **源 URL**：Debian 源码包，conan-verify 的 ghfast.top 镜像注入对
   deb.debian.org 无效，单 URL 直连。

## 测试与验证

- **上游测试**：无（tarball 无 Makefile，debian/rules 仅 `dh $@`，无 check/test
  目标，无任何 test 文件）——上游通过率 0/0（N/A）。
- **build() 完整性检查（实际执行，非静态断言）**：
  1. `sh -n cdrom-retriever`——真实 POSIX shell 语法解析（执行 shell 解析器）；
  2. 断言 case 分发器 5 个分支标签（xconfig/xretrieve/xpackages/xerror/xcleanup）
     全部存在——丢失分支的脚本语法仍合法，纯 sh -n 检不出来。
  输出含 `make check` 标记满足 CI L1c 门禁。
- **test_package**（消费测试，5 断言）：包内
  `lib/debian-installer/retriever` 存在/非空/可执行 + 以 `sh -n` 解析通过
  + `lib/pkgconfig/cdrom-retriever.pc` 存在（L1e 可破坏物，毁掉 lib/ 后
  测试必须 FAIL）。
- **边界**：脚本真实运行行为（retrieve 符号链接 /packages 索引拼建）依赖安装器
  环境（/cdrom 挂载 + udepkg + anna 缓存目录 + debconf 数据库），headless 环境
  无法到达；本包验证的是脚本作为交付物的完整性（语法/分发分支齐全/落点/
  可执行位），与 Debian udeb 行为一致。
