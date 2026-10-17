# ircd-irc2

## 软件描述
`ircd-irc2` 是**经典 IRC 服务器**（irc2 系列，IRC 协议最早期的实现谱系之一），C 语言 + autotools 构建。Debian 以 dfsg 版打包（移除非自由文档）。GPL-1.0-or-later。

## 功能概述
| 可执行 | 作用 |
|---|---|
| `ircd` | 服务器本体（监听客户端端口、处理 IRC 协议、channel/nick 管理） |
| `chkconf` | 配置文件检查器（启动前校验 `ircd.conf`） |
| `iauth` | 认证/授权子进程（连接鉴权） |
| `ircd-mkpasswd` | 生成 `ircd.conf` 用的口令哈希 |
| `ircdwatch` | 服务器守护/监控辅助 |

## OHOS 适配

### 构建方式
- **autotools**（照抄 Debian 的权威步骤）：顶层 `configure` 是 irc2 自写脚本，真正可用的 autoconf 是 `support/configure`
- **out-of-source**：建 `builddir/` → 复制 `support/configure` 进去 → 在其内 `./configure --with-zlib --enable-ipv6 …` → `make all`（与 Debian `override_dh_auto_configure` 完全同构）
- **依赖注入**：`AutotoolsDeps` 把 libxcrypt / zlib 的 include/lib 注入 `CPPFLAGS`/`LDFLAGS`，让老式 `AC_CHECK_LIB(crypt)`、`AC_CHECK_HEADER(zlib.h)` 命中（工程没有 pkg-config）

### 关键攻坚点
1. **构建入口有两层**：直接用顶层 `configure` 会走它自写的 `${rev}` 目录逻辑；官方（Debian）做法是复制 `support/configure` 到独立 builddir 再配置——本配方照抄，避免猜参数
2. **依赖版本要逐个探**：仓库里 `libxcrypt` 有 4.4.36 与 4.5.2 两个目录，**只有 4.5.2 已发布**（4.4.36 实测 Unable to find）
3. **产物是 5 个二进制**：Debian 也是逐个 `cp` 到 `usr/sbin`；本包逐个装到 `bin/`，缺任一即让 build 失败（不留"静默缺产物"）
4. **上游无测试**：如实记 N/A（附清点证据），验证由消费者校验承担（ELF/AArch64 审计 + ircd 指纹 + best-effort 真跑 `chkconf`）

### 与 Linux 的差异
- 代码层面无差异（POSIX C）；差异集中在**交叉构建的依赖发现**（AutotoolsDeps 注入 env）与**产物落点**（`bin/` 而非 Debian 的 `usr/sbin`）
- 本适配沙箱对 OHOS 共享对象/未签名 ELF 的加载受限，消费者校验的"真跑"会按具名环境信号记 SKIP 并打印原文

## 依赖关系
- **Conan requires**：`libxcrypt/4.5.2`（libcrypt → `crypt()`）、`zlib/1.3.1.1`（`--with-zlib`）
- 两者均已合入制品仓（R35 实测可解析）

## 版本记录
| 版本 | 状态 | 打包日期 | 备注 |
|------|------|---------|------|
| 2.11.2p3-dfsg | built | 2026-10-08 | 照抄 Debian 的 builddir + support/configure 构建法；5 个二进制产物 |

## 参考资料
- Debian 包页: https://tracker.debian.org/pkg/ircd-irc2
- 上游（Debian salsa）: https://salsa.debian.org/debian/ircd-irc2
