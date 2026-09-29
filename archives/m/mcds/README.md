mcds
====

`mcds`（Macabre CardDAV Search）是一个命令行 CardDAV 地址簿查询工具，上游
<https://github.com/t-brown/mcds>，作者 Timothy Brown。它主要用作 mutt 的
联系人查询插件：向 CardDAV 服务器发一个 `REPORT` 请求，把命中的
邮箱/姓名按 mutt 期望的格式打到 stdout。

    mcds -u https://example.org/remote.php/dav/addressbooks/users/me/contacts Fred

典型输出：

    fred.smith@example.org   Fred Smith

配置可放在 `${HOME}/.mcdsrc`（`url` / `username` / `verify` / `netrc` /
`password_file` / `libsecret` 等键），详细选项见 `mcds(1)` 手册页。

HarmonyOS PC 适配版本
---------------------

| 版本 | 说明 |
|------|------|
| 1.9-git20260415 | 上游 2026-04-15 的 git 快照（提交 `0e150e9`，PR #45 gcc-16 修复线）。该快照的 `configure.ac` 仍是 `AC_INIT([mcds], [1.8])`，所以 `mcds --version` 打印的上游版本串是 1.8；任务版本串按快照日期命名，二者不是同一坐标。 |

本包在鸿蒙上交付的是纯命令行程序（无库、无头文件），依赖 `curl/8.15.0`
与 `libxml2/2.15.3`。相对上游默认构建，本包显式关闭了三项：

+ `--disable-nls`：上游 `po/` 只带模板 `mcds.pot`，没有任何 `.po` 翻译，
  关闭不损失功能，同时避开 `libintl` 链接。
+ `--disable-gpgme`：`configure.ac` 在启用 GPGME 时强制要求宿主有
  `gpgconf` 与 `gpg`/`gpg2` 可执行文件，构建主机两者皆无（缺失即
  `AC_MSG_ERROR`）。影响：不能解密 rc 文件里的 `gpg:` 前缀口令。
+ `--disable-libsecret`：制品仓没有 `libsecret` 配方，且其后端是
  Secret Service D-Bus 接口（OHOS 无 dbus socket）。
  影响：口令只能交互输入或用 `password_file`。

适配细节、踩坑与验证记录见版本目录下的 `notes.md`。
