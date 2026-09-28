# krb5-sync

Kerberos → Active Directory 口令同步工具集（Russ Allbery /Eyrie.org）。

- **插件**：`sync.so`，由 kadmin 以 `hook_policy` / `hook_principal` 方式 dlopen，
  在每次口令修改后调用 `kadm5_chpass_principal()` 把新口令同步到 AD 侧的
  `kadmin/admindn@REALM`。
- **命令行工具**：`tools/krb5-sync`（前台包装）与 `tools/krb5-sync-backend`
  （`kadm5clnt` 后端包装），二者由 Automake 的 `sbin_PROGRAMS` 与
  `dist_sbin_SCRIPTS` 安装。
- **测试**：上游自带 C TAP 套件（`tests/runtests.c` harness + 10 个 `*-t.c`
  驱动，`tests/TESTS` 登记 17 条，`tests/data` 语料 7 个）。

## OpenHarmony PC 适配

- 路径：Conan + Autotools，依赖 `krb5/1.22.1` 与 `openldap/2.6.7`
  （均为 ohpcd 仓已发布二进制）。
- configure 通过 `--with-krb5-include/--with-krb5-lib/--with-ldap-include/
  --with-ldap-lib` 只接受 Conan 私有路径（R49），不探测宿主 `krb5-config`。
- OHOS 三元组由 `patches/0001-config-sub-ohos.patch` 教给上游自带的 2012 版
  GNU `config.sub`；HMDFS 上 configure 临时目录以 `umask 022` 创建
  （`patches/0002-config-tmpdir-umask.patch`）。
- 构建期 shell 按知识图谱 E386 做能力探测后固定，详见 `3.1/notes.md`。

版本级明细见 `3.1/manifest.yaml`，命令声明见 `commands.json`。
