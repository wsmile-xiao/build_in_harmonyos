# accountsservice 26.27.3 适配笔记

> 本包已完成适配并编译成功（Meson，OHOS clang 15）。早期 W0 检查曾因 polkit
> 未发布而阻塞（`dependency_missing`）；polkit/127 发布后回迁补齐，本包
> `finish` 达标，状态 `built`。下方保留关键技术记录与补齐过程。

## 软件简介
accountsservice（AccountsService）：D-Bus 用户账户服务，向系统提供
`org.freedesktop.Accounts` 接口，管理用户账户属性（真实姓名、用户类型、
会话/座席 seat 状态、是否已登录等）。上游代码托管于
gitlab.freedesktop.org/accountsservice/accountsservice，**Meson** 构建，
产物为共享库 `libaccountsservice`（供下游 ayatana-indicator-a11y 经
`act_*` API 读取用户会话）+ daemon 二进制 `accounts-daemon`。本适配以
库为主交付。

## 上游版本确定
- 最新稳定 tag：**26.27.3**（gitlab API `repository/tags`，commit 4e254d96，
  release 2026-07-03）。
- 官方源码 tarball（实测可达、sha256 已核验）：
  `https://gitlab.freedesktop.org/accountsservice/accountsservice/-/archive/26.27.3/accountsservice-26.27.3.tar.gz`
  sha256=`11de07bcd499c2277f78a6fc830d1437654f3397cc7bbed19c28b3818435ba38`
- ⚠️ 版本探测坑：源码 `generate-version.sh` 在非 git checkout 时按目录名取版本，
  但若外层目录位于 git 仓库内（本机 `$HOME` 即 git worktree），`git rev-parse`
  会成功并误按外层仓库历史派生 `26.34.1`（`date +%y.%V`）。配方必须按发布 tag
  固定版本（0001-fix-version-26.27.3.patch 处理）。

## 依赖解析（Meson，全部命中）
| 上游模块 | Conan 包 | 说明 |
|---|---|---|
| glib-2.0 / gio-2.0 / gio-unix-2.0 | `glib/2.84.0.1` | 唯一传播给下游的依赖（transitive_headers/libs） |
| json-c | `json-c/0.18` | 仅 accounts-daemon 链接，private |
| dbus-1 | `dbus/1.14.10` | 仅 configure-time（install dirs 变量），private |
| polkit-gobject-1 | `polkit/127` | daemon 硬依赖（meson.build:161），private；polkit/127（已发布 OHOS 构建）提供 polkit-gobject-1 客户端库 |

> 说明：libaccountsservice 本身只链接 glib/gio/gio-unix（+ logind stub），
> 因此 `glib` 是唯一 propagated 依赖；json-c/dbus/polkit 均为 private。

## 补丁清单（5 个，全部 portability）
1. `0001-fix-version-26.27.3.patch`：固定版本号为 26.27.3（避开外层 git worktree 误派生）。
2. `0002-crypt-util-ohos.patch`：**中性特性宏方案**（R8）：meson.build 增设
   `cc.has_function()`/`cc.has_header_symbol()` 特性探测段，生成中性
   `HAVE_EXPLICIT_BZERO`/`HAVE_DECL_CRYPT`/`HAVE_GETSPNAM`/`HAVE_FGETSPENT`/
   `HAVE_UTMPX*` 等 config.h 宏（无平台 ifdef，Linux CI 可编译验证同一代码
   路径）。crypt(3)：OHOS libc.so 导出该符号但 `crypt.h` 未声明（空 libcrypt
   stub 头），`!HAVE_DECL_CRYPT` 时以标准签名声明；explicit_bzero：OHOS libc
   无此 API，`!HAVE_EXPLICIT_BZERO` 时提供 volatile 覆写等价实现（语义保留，
   非静默 no-op）。
3. `0003-wtmp-helper-ohos.patch`：**中性特性宏方案**：utmpx/wtmp API 回退由
   `!HAVE_UTMPXNAME`/`!HAVE_SETUTXENT`/`!HAVE_GETUTXENT`/`!HAVE_ENDUTXENT`
   守卫（OHOS SDK 的 utmpx.h 仅含 struct/常量定义，无函数实现）。签名修正：
   setutxent/endutxent 按 POSIX 为 void。
4. `0004-daemon-ohos.patch`：**中性特性宏方案**：shadow-password 回退由
   `!HAVE_GETSPNAM`/`!HAVE_FGETSPENT` 守卫（OHOS SDK 的 shadow.h 仅含
   struct spwd 定义，无函数实现）。
5. `0005-data-policy-ohos.patch`：OHOS 工具链缺 gettext ITS rules，.policy 文件改由
   configure_file(copy:) 未翻译安装，替代 i18n.merge_file()。

## 适配完整性人工确认标注（R40，stub 化降级说明）
> **[适配完整性人工确认标注]** OHOS libc（musl 系）无 shadow 密码与 utmpx/wtmp
> 登录记账 API，0003/0004 补丁在特性探测缺失时提供回退实现。**行为=返回
> 无口令/无记录**，属降级适配，需人工确认适配完整性：
>
> - **shadow 口令（0004）**：`getspnam()`→NULL 使 `user_update_from_pwent()`
>   视每个账户为"无 shadow 条目"（regular 密码模式、永不 locked），
>   `build_shadow_users_hash()` 查无 shadow 用户（本地用户本就来自
>   getpwnam()/用户缓存目录）。密码过期策略字段、locked 检测不可用——
>   OHOS 无 /etc/shadow 子系统，"无 shadow 条目"是真实状态而非错误。
> - **wtmp 记账（0003）**：`getutxent()`→NULL 使登录频次/上次登录记录为空；
>   `utmpxname()` 返回 0 使 `wtmp_helper_start()` 提前返回。OHOS 无
>   wtmp/utmpx 登录记账子系统可读，"无记录"是真实状态而非错误。
> - **对 accounts-daemon 核心功能的影响评估**：账户枚举/属性读写/图标等
>   核心路径不依赖这两组 API；受影响的仅是密码策略字段与登录统计两项
>   附属能力。**评估结论：降级对核心功能可接受**（OHOS 侧无对应接口可
>   接入；若后续 OHOS 提供账号/口令存储或登录记录接口，可在
>   `!HAVE_GETSPNAM`/`!HAVE_GETUTXENT` 分支替换为真实实现）。
> - **test_package 断言覆盖（P2 修复）**：测试对 no_service、
>   `act_user_manager_get_user_by_id()` 用户对象、`act_user_is_loaded()`=FALSE、
>   `act_user_get_password_hint()`=NULL、`act_user_get_uid()`=-1 做确定性断言，
>   覆盖无 daemon 下的客户端默认路径（与 stub 语义一致性可观测）。

## 构建配置（Meson）
```bash
-Dsystemdsystemunitdir=no     # OHOS 无 systemd
-Dwtmpfile=/var/log/wtmp      # OHOS libc 无 _PATH_WTMPX / WTMPX_FILENAME
-Dtests=false -Dintrospection=false -Dvapi=false
-Ddocbook=false -Dgtk_doc=false -Dcreate_homed=false
```
- default_library=shared；wrap_mode=nodownload。
- systemd stub：配方内以 C 实现极小 logind stub 编译链接，替代上游对
  systemd/logind 的 libelogind/libsystemd 依赖（OHOS 无）。
- dbus `dbus-1.pc` 别名：dbus/1.14.10 配方生成 `dbus.pc`，meson `dependency('dbus-1')`
  需 `dbus-1.pc`，配方创建别名 pc 处理（_create_dbus_pc_alias）。

## 编译环境
- 构建系统: meson（init-build 需显式 meson，勿误检 autotools）
- 编译器: clang 15 (aarch64-linux-ohos)，Conan profile `ci/conan/profiles/ohos-aarch64`
- meson 版本 1.11.1，ninja 可用

## 测试
- 上游测试（tests/ meson test 注册清单 N=19：check-format 1 + test-libaccountsservice.py
  13 + test-daemon.py 4 + util 1）：19 项在 OHOS headless CI 均无法运行（17 项 D-Bus
  system bus 集成 + util 交叉编译不可运行 + check-format 需 git+uncrustify），以
  -Dtests=false 禁用，functional coverage 由 test_package 提供（逐项禁用原因见
  reports/test-report.md）。
  口径修正：2026-09-11 rule4 打回（实测 N=19 > 声明 N=0 少报），PR 正文与测试报告
  已统一修正为 19 实测口径。
- test_package（CMake + C）：调用 `act_user_manager_get_default()`/
  `act_user_manager_get_type()`/`act_user_manager_no_service()`/
  `act_user_manager_get_user_by_id()`/`act_user_is_loaded()`/
  `act_user_get_password_hint()`/`act_user_get_uid()` 等 `act_*` API 验证
  libaccountsservice 库可链接可用，并对无 daemon 下的客户端默认路径
  （no_service=TRUE、is_loaded=FALSE、password_hint=NULL、uid=-1）做确定性
  断言（R40 stub 路径可观测覆盖），构建测试实测 PASS。
- 已知限制：headless 无 D-Bus 系统总线，运行期 `org.freedesktop.Accounts`
  服务不可用；包交付以编译期库可用性为准。

## 注意事项
- `/tmp` 只读（E002）：中间产物一律用 `$HOME/tmp`。
- GitHub 沙箱不可达（gh-proxy 403），但 **gitlab.freedesktop.org 可达**，
  官方 archive tarball 可直接下载（本报告 sha256 即官方源实测）。
---

**编译结束**: 2026-09-03 14:15（2026-09-10 R8/P2 修复重验证；2026-09-11 rule4 上游
测试数申报口径修正 N=0→19，归档与 PR 正文同步）
**最终状态**: built
