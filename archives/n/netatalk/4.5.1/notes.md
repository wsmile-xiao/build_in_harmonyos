# netatalk 4.5.1 适配笔记

## 编译环境

- 构建系统: meson
- 编译日期: 2026-09-09
- 编译器: clang/clang++
- 状态: built（待真机预检回填实测结果）

## 上游信息

- 上游仓库: https://github.com/Netatalk/netatalk
- 发布页: https://github.com/Netatalk/netatalk/releases/tag/netatalk-4-5-1
- 源码包: netatalk-4.5.1.tar.xz（1305244 字节，sha256 已用官方 .sha256sum 交叉验证）
- 许可证: GPL-2.0-only
- 构建要求: meson >= 0.62.0，ninja，C11 编译器

## 编译步骤

Netatalk 4.x 使用 Meson（Autotools 仅遗留支持），推荐流程：

```bash
meson setup build -Dwith-cnid-backends=sqlite -Dwith-eventloop=libevent \
  -Dwith-tests=true -Dwith-testsuite=false -Dwith-docs=[] \
  -Dwith-init-style=none -Dwith-acls=false -Dwith-appletalk=false \
  -Dwith-cracklib=false -Dwith-cups=false -Dwith-dtrace=false \
  -Dwith-gssapi=false -Dwith-kerberos=false -Dwith-krbV-uam=false \
  -Dwith-ldap=false -Dwith-pam=false -Dwith-quota=false \
  -Dwith-tcp-wrappers=false -Dwith-zeroconf=false -Dwith-spotlight=false \
  -Dwith-shell-check=false -Dwith-init-hooks=false \
  -Dwith-install-hooks=false -Dwith-statedir-creation=false \
  -Dwith-rpath=false -Dwrap_mode=nodownload
meson compile -C build
meson test -C build
meson install -C build
```

Conan 配方通过 MesonToolchain 下发上述全部选项，并用 PkgConfigDeps
提供 bstring / iniparser / libevent / libgcrypt / sqlite3。

## 上游测试清点（适配前）

- test/test_byteorder.c：字节序单元测试（meson test 注册）。
- test/afpd/：afpd 服务端集成测试 harness（test.c、subtests.c、
  afpfunc_helpers.c），链接 afpd 实现直接测试内部路径，输出 TAP；
  仅当 -Dwith-tests=true 且 sqlite 后端启用时编译（test/meson.build）。
- test/testsuite/：AFP 客户端测试程序（afp_spectest、afp_logintest、
  约 50 个 FP*.c / T2_*.c 测试集，另有 afparg 等客户端工具）；
  需要指向一个运行中的 AFP 服务器与测试卷，不在 meson test 中自动运行，
  本配方以 -Dwith-testsuite=false 编译但源码随包提供。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CNID 后端需要 Berkeley DB，OHOS 上探测脆弱 | 上游默认 backends 为 dbd+mysql+sqlite，BDB 走自定义头/库搜索而非 pkg-config | 只启用 sqlite 后端（-Dwith-cnid-backends=sqlite），sqlite3 制品仓已有 3.49.1；dbd/mysql 在补充说明中声明未启用 |
| 2 | 可选子系统依赖在 OHOS 不可用 | ACL/CUPS/Kerberos/LDAP/PAM/quota/Zeroconf/Spotlight/dtrace 需系统服务或冷门库 | 全部显式关闭，仅保留 AFP 核心 + FCE + iconv；musl/OHOS 无 pam/ldap/cups，直接禁用而非打桩 |
| 3 | 安装钩子会触碰宿主系统目录 | with-init-hooks/with-install-hooks/with-statedir-creation 默认 true | 全部设 false，statedir 由运行时创建；with-init-style=none |
| 4 | 文档构建需要 pandoc/cmark/doxygen | with-docs 默认含 developer/html/man/readmes | with-docs=[] 关闭文档构建 |
| 5 | 子项目可能联网下载 | bstring/iniparser 在缺失时走 subproject fallback | 五个依赖全部用 conan requires 提供，并设 wrap_mode=nodownload 杜绝网络 |

## 源码修改

无补丁（patches 为空）。全部适配通过 Meson 选项完成，未修改上游源码。

## 依赖版本

- bstring/1.0.3（AFP 字符串库，上游缺共享库时本会作为 subproject 内建）
- iniparser/4.2.6（afp.conf 解析，必填）
- libevent/2.1.12（netatalk 服务控制器事件循环，与 libev 二选一，选 libevent）
- libgcrypt/1.11.0（DHX2 等 UAM 加密，>= 1.2.3，必填）
- sqlite3/3.49.1（sqlite CNID 后端 + afpd 集成测试前提）

以上版本均为仓库中已存在的配方版本。

## 验证结果

```bash
conan create archives/n/netatalk/4.5.1 --user=ohpcd --channel=stable（真机预检）
meson test -C build（配方 build() 内自动执行）
./afpd -V / ./dbd -V / ./netatalk -V（test_package/test.sh 消费者冒烟；cnid_dbd/cnid_metad 仅 dbd 后端才构建，sqlite 配置下不存在）
```

实测数字待 HMBS 真机预检回填后写入 PR 正文，本轮不预填通过率。

## 交付物

| 文件 | 说明 |
|------|------|
| sbin/afpd | AFP 文件服务守护进程 |
| sbin/netatalk | 服务控制器 |
| bin/afppasswd、bin/dbd、bin/nad 等 | AFP 口令与 CNID/工具（cnid_dbd、cnid_metad 仅 dbd 后端才构建，本 sqlite 配置不含） |
| lib/libatalk.* | 内部共享/静态库 |

## 注意事项

- 本配方是 AFP 文件服务器（application 类型），产物含可执行文件，
  软件级 commands.json 已声明。
- dbd/mysql CNID 后端、Spotlight（xapian/tracker）、Zeroconf（avahi）、
  Kerberos/LDAP/PAM、CUPS、CrackLib、quota、ACL、TCP wrappers、dtrace、
  AppleTalk 传输层均未启用，属有意裁剪，见 PR 补充说明。
- testsuite 客户端套件需 live 服务器，未接入 meson test；
  上游 afpd TAP 集成测试已在 build() 中通过 meson test 执行。
