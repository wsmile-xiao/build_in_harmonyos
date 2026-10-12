# kwartz-client

Debian `admin` 段包 **kwartz-client**——法国 Kwartz 校园服务器网络的
GNU/Linux 客户端入域配置工具。纯 POSIX shell + 数据包（零编译、零 ELF，
`debian/rules` = 裸 `dh $@`，`Architecture: all`）。本仓版本 3.0 = 上游
3.0 的 Debian 修订态 3.0-17。

## 上游形态

- `kwartz-cloud/kwartz-cloud`：24 行 POSIX sh 脚本（zenity + host + nemo，
  打开学校 Kwartz/OwnCloud 的 WebDAV 桌面快捷方式）；
- `debian/kwartz-install.tpl`：172 行 POSIX sh 模板（主交付物），Debian
  postinst 以 gettext-base `envsubst` 注入 debconf 问卷的 9 个变量渲染成
  `/usr/sbin/kwartz-install.sh`（LDAP/NSS-PAM 入域、Samba/CIFS 挂载、
  代理与 apt 定时升级、计划关机）；
- 桌面集成面：desktop/svg/conf/manpage。

## OHOS 适配形态（POSIX 能力级，零平台宏）

- 零编译、零改动：源 = salsa 发布 tag `debian/3.0-17` 快照（30 文件全树，
  含功能主体 debian/；kwartz-cloud/ 子树与 Debian orig tarball 逐字节
  一致，orig SHA256 作上游身份旁证）。`build()` 仅做机读保真审计
  （文件集合 + 逐文件 SHA256 pin + debconf 模板变量契约，E241 范式）。
- 安装布局逐条复刻 `debian/kwartz-client.install` + `.manpages`：

  ```
  <pkg>/bin/kwartz-cloud                                 # chmod 755，非 ELF 不签名
  <pkg>/share/icons/kwartz-cloud.svg
  <pkg>/share/applications/kwartz-cloud.desktop
  <pkg>/etc/kwartz-cloud.conf
  <pkg>/share/doc/kwartz-client/kwartz-install.tpl
  <pkg>/share/man/man1/kwartz-cloud.1
  <pkg>/licenses/copyright                               # GPL-2+
  ```

- `package_type="application"`：kwartz-cloud 是真实安装命令，R38 以
  软件级 `commands.json` 满足（`binary: false` 如实反映非 ELF）。
- test_package 依赖仓内已发布的 `bash/5.3` 作 harness：18 条断言
  （harness / 零 ELF 不变量 / `bash -n` 语法门禁 / 安装面保真 /
  SHA256 逐字节 / debconf 模板契约与 conf-desktop 数据流）。

## 运行期诚实披露

OHOS 无 Debian 运行时栈（envsubst、libnss-ldapd、libpam-ldapd、
cifs-utils、winbind、smbclient、libpam-mount、net-tools、oidentd、
inetutils-inetd、debconf 等 12 项），kwartz-cloud 另需 zenity/host/nemo：
**入域功能在 OHOS 不可达**。本包交付的验证面 = 装得上 + 语法对 +
模板契约断言过；postinst 的渲染属 dpkg/debconf 生命周期，OHOS 上不会
发生，模板按原位原样交付。

上游无测试套件（NO_UPSTREAM_TESTS，证据链见
`3.0/test_package/EXCLUDED-TESTS.md` 与 `UPSTREAM-TESTS-EVIDENCE.json`）。

## 目录结构

```
commands.json                  软件级 CLI 声明（R38）
3.0/
  conandata.yml                源归档固定（URL + SHA256 + 选型理由）
  conanfile.py                 配方（零编译；build() = 完整性审计）
  manifest.yaml                版本 manifest
  notes.md                     适配笔记（归档选型/依赖披露/NO_UPSTREAM_TESTS）
  test_package/                消费者冒烟 + 上游测试声明三件套
```
