# linpac — LinPac

## 软件简介

LinPac（Linux Packet Radio）是一个基于 curses 的 AX.25 分组无线电终端，由 Radek Burget (OK2JBG)
于 1998 年创建，现由 David Ranch (KI6ZHD) 维护。它把终端界面、AX.25 连接管理、BBS/邮箱、
宏脚本与应用插件组合成一个完整的业余无线电台操作环境。

**主要组成**:
- `libexec/linpac/linpac` — 终端本体（curses 界面、AX.25 通道管理、宏解释器）
- `libexec/linpac/` 下的众多辅助程序 — 通过 LinPac 应用协议与终端通信的插件式应用
  （`mail` 邮箱、`getmsg`/`forward`/`delmsg` BBS 邮件、`telnet`、`w` 用户列表、
  `mheard`、`logbook`、`autobin` 二进制传输、`rawio`、`yapp` 等）
- `liblinpac` / `libaxmail` — 编写 LinPac 应用所需的插件 API 库（含 `lpapp.h`/`tevent.h`）
- `share/linpac/` — 宏（`macro/`）、码表（`*.ctt`）、电码/字符集数据与文档

## 已编译版本

| 版本 | 状态 | 编译日期 | 补丁数 |
|------|------|----------|--------|
| 0.28 | built ✅ | 2026-09-28 | 6 |

## 使用方法

```bash
# 直接启动终端本体（真实二进制位于 libexec）
linpac

# 上游还提供 bin/linpac 启动脚本：首次运行会在 $HOME/LinPac 生成个人配置
# 目录并拷贝宏/码表/插件链接，然后 exec libexec/linpac/linpac
linpac --help 2>&1 | head        # 终端本体无 --help，直接运行即为交互式终端
```

> 说明：LinPac 的完整功能依赖 Linux AX.25 内核协议栈（`AF_AX25` socket、
> `/proc/net/ax25`、`SIOCAX25GETINFO` ioctl）以及外部 `listen`/`axlisten` 监视程序。
> OpenHarmony 内核不提供 AX.25 协议栈，因此本适配保证**构建、链接、启动与
> 界面初始化**在 OHOS 上正确工作；实际的 AX.25 连接能力取决于目标平台是否
> 提供协议栈（缺少时程序按原有逻辑降级，不会崩溃）。

## 平台适配说明

### 鸿蒙系统适配

| # | 补丁 | 内容 |
|---|------|------|
| 1 | `0001-build-aux-config.guess.patch` | 2009 版 config.guess 增加 `*:HarmonyOS:*:*` 分支，识别出 `aarch64-unknown-linux-ohos` 并立即返回 |
| 2 | `0002-build-aux-config.sub.patch` | config.sub 把 `-linux-ohos` 加入内核-OS 白名单，避免被改写成 `-linux-gnu` |
| 3 | `0003-configure.patch` | ① `AC_CHECK_LIB(ncurses)` → `ncursesw`，termcap 回退 → ncursesw；② 缺失 AX.25 `listen` 程序由硬错误降级为警告；③ config.status 临时目录 `umask 077` → `022`（E114） |
| 4 | `0004-src-applications-mailer-mail_screen.cc.patch` | `stdscr->_maxx/_maxy` → `getmaxx()/getmaxy()`；`win->_clear = TRUE` → `clearok(win, TRUE)`（Conan ncurses 为 opaque API） |
| 5 | `0005-src-compat-linux-ax25.h.patch` | 新增 `src/compat/linux/ax25.h`：绕过 OHOS `<linux/ax25.h>` 的 `sockaddr_storage` 重复定义与缺失的 `SIOCPROTOPRIVATE`，再用 `#include_next` 交给真实头文件 |
| 6 | `0006-src-linpac.cc.patch` | ① 屏幕尺寸改用公共 API；② 锁文件目录回落到可写运行目录（OHOS 无 `/var/lock`） |

**编译依赖**: `ncurses/6.6`（制品仓已发布，宽字符静态库 `libncursesw.a`）

**内部插件库**：`liblinpac`/`libaxmail` 以静态方式链接（`--enable-static
--disable-shared`），避免 libtool 把 Conan 包目录的绝对路径写进 RUNPATH。

## 验证结果

### 功能测试（test_package，消费者视角）

| 测试项 | 结果 |
|--------|------|
| 终端二进制安装于 `libexec/linpac/linpac` 且可执行 | ✅ 通过 |
| 启动并输出 `LinPac version 0.28` 版本横幅 | ✅ 通过 |
| 锁文件写入可写运行目录（OHOS 无 `/var/lock`）—— **鸿蒙特有断言** | ✅ 通过 |
| `LINPAC_LOCKDIR` 显式覆盖生效 | ✅ 通过 |
| 辅助程序 `mail`/`testapp`/`mheard`/`telnet` 齐备 | ✅ 通过 |

### 上游测试

上游 linpac 0.28 **没有任何自动化测试套件**：全部 `Makefile.am` 中不存在
`TESTS`/`check_PROGRAMS`/`check-local`，工程内无 `tests/` 目录，`make check`
输出 `Nothing to be done for 'check'`（详见 `0.28/notes.md` 与
`test_package/MANIFEST.yml` 的清点证据）。`src/applications/testapp.c` 是
LinPac 应用协议的人工演示程序，不是自动化测试。

### 质量门禁

| 门禁项 | 结果 |
|--------|------|
| G0 预构建风险评估 | ✅ 通过 |
| G1 配方完整性 | ✅ 通过 |
| G2 conan create | ✅ 通过 |
| G3 系统同名库隔离 | ✅ 通过 |
| G4 产物完整性 | ✅ 通过 |

## 源码信息

- **源码地址**: https://sourceforge.net/projects/linpac/files/LinPac/0.28/linpac-0.28.tar.gz
- **官方主页**: http://linpac.sourceforge.net/
- **官方仓库**: https://sourceforge.net/p/linpac/code/
- **许可证**: GPL-2.0-or-later
- **维护者**: David Ranch (KI6ZHD)，原作者 Radek Burget (OK2JBG)

## 相关资源

- [编译详情](./0.28/notes.md)（含上游测试清点、13 条踩坑记录与实施要点）
- 验证报告：`0.28/reports/`（test-report.md / conan-verify-report.md / audit-result.json，本地归档不随仓库发布）
