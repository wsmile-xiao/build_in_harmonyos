# kwartz-client 3.0 适配笔记

## 编译环境
- **构建系统**: none（纯 POSIX shell + 数据包；`debian/rules` 全文 4 行裸
  `dh $@`，`Architecture: all`，Build-Depends 仅 debhelper-compat(=13)，
  零编译单元、零 ELF）
- **构建日期**: 2026-10-02
- **平台**: arm64-ohos（OpenHarmony PC，profile ohos-aarch64）
- **状态**: built（Conan 配方验证通过，权威 CI 全绿）
- **补丁数量**: 0（数据包忠实原则，上游内容一字不改）

## 身份与源归档选择

kwartz-client 是法国 Kwartz 校园服务器网络的 **GNU/Linux 客户端入域配置
工具**（Debian admin 段包；非 Ruby 的 kwartz 模板引擎——同名甄别见
Scout 报告 §1）。功能主体分两块：

- `kwartz-cloud/kwartz-cloud`：24 行 POSIX sh 脚本（zenity 询问用户名 +
  host 解析 + nemo 打开 WebDAV 桌面快捷方式）；
- `debian/kwartz-install.tpl`：172 行 POSIX sh **模板**（包的主交付物），
  postinst 用 gettext-base `envsubst` 把 debconf 问卷（9 个变量）渲染成
  `/usr/sbin/kwartz-install.sh`（LDAP/PAM 接入、Samba 挂载、代理与 apt
  定时升级、/etc/cron.d 计划关机）。

### 两个候选归档（本 run 实测下载 + SHA256）

| 候选 | URL | SHA256 | 内容 |
|---|---|---|---|
| ① Debian orig | `https://deb.debian.org/debian/pool/main/k/kwartz-client/kwartz-client_3.0.orig.tar.xz` | `7a15f5f7873bf802518577434934a1ede481d130dac26a6b27425f4df44ab290`（8,624 B） | 仅 kwartz-cloud/ 6 文件 + README.md + .gitignore，**缺功能主体**（tpl、debconf config/templates/postinst 全在 debian/） |
| ② salsa tag 快照 | `https://salsa.debian.org/georgesk/kwartz-client/-/archive/debian/3.0-17/kwartz-client-debian-3.0-17.tar.gz` | `8093f591b9dec4085061fa3a7e87220d1d44562d92aab64de791d5cceb5c8167`（30,408 B） | 30 文件全树 = kwartz-cloud/ + debian/（功能主体在内） |

**选用 ②**，理由：功能性完整性——本包的主交付物 kwartz-install.tpl 与
debconf 数据流文件只存在于 debian/，纯 orig 会交付功能空心包。保真佐证：
② 的 kwartz-cloud/ 子树与 ① 逐字节一致（`diff -r` 干净），① 的 SHA256
作为上游身份旁证固定于 UPSTREAM-TESTS-EVIDENCE.json。

版本映射核查（git ls-remote 实测）：`upstream/3.0` → commit
`7e39d8b30d98096a2a5951b05b5f437c3350ceea`（tag 对象 a1c4d8d5）＝Debian
orig 3.0；`debian/3.0-17` → commit `17208cb88caf19c3074df506b4fa3f2e064a11c2`
＝当前 master HEAD＝Debian trixie/stable 3.0-17。run 版本 3.0 即
upstream 3.0 的 Debian 3.0-17 修订态。快照 URL 重复下载两次 SHA256 一致
（cgit 归档确定性）。归档域 salsa.debian.org 不在 CI mirror-fallback
改写名单内，conandata.yml 在 CI 过程保持原样（E415 教训规避）。

## 打包形态（conan create 全流程）

```bash
conan create archives/k/kwartz-client/3.0 --build=missing \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

1. **source()**: `get()` 取 salsa tag 快照并 `strip_root=True`。
2. **build()**: 零编译。仅做 E241 数据包机读审计（launchctl-completion/
   zsdx 先例范式）：30 文件集合精确比对（剔除 conan 生成的 env 脚本，
   E403 教训）→ 打包面 7 文件 + debconf 源面 4 文件（postinst/config/
   templates/rules）逐文件 SHA256 pin → postinst 必须对 9 个 debconf
   变量 `db_get kwartz/<var>` → 模板必须引用其中 8 个 `$var`/`${var}`
   （landing_page 为 postinst 专用、上游模板即不引用）→ 输出
   NO_UPSTREAM_TESTS 机读标记。
3. **package()**: 逐条复刻 `debian/kwartz-client.install` +
   `debian/kwartz-client.manpages` 的放置（Debian /usr → 包相对路径）：
   `bin/kwartz-cloud`（chmod 755，shell 脚本非 ELF、不做签名）、
   `share/icons/kwartz-cloud.svg`、`share/applications/kwartz-cloud.desktop`、
   `etc/kwartz-cloud.conf`、`share/doc/kwartz-client/kwartz-install.tpl`、
   `share/man/man1/kwartz-cloud.1`、`licenses/copyright`（GPL-2+ 声明）。
4. **package_info()**: `bindirs=["bin"]`、`resdirs=["share"]`、runenv PATH
   注入 bin。kwartz-cloud 是真实安装命令（Debian /usr/bin）→
   `package_type="application"`，R38 以软件级
   `archives/k/kwartz-client/commands.json` 满足（`binary: false` 如实
   反映非 ELF）。

## 依赖轨道

- **构建闭包为空**：无编译、无 tool_requires、无 conan requires。
- test_package 依赖 `bash/5.3`（本仓已发布 armv8 静态二进制，
  launchctl-completion 先例）：仅作 harness——被测脚本用真实 shell 做
  `bash -n` 语法门禁。
- **运行期披露（不进 conan requires，属运行目标非构建依赖）**：Debian
  运行时依赖 12 项（gettext-base/envsubst、inetutils-inetd、libnss-ldapd、
  libpam-ldapd、libpam-modules、cifs-utils、debconf、libpam-mount-bin、
  net-tools、oidentd、smbclient、winbind）在 OHOS 均无对应物。知识图
  E015/E027/E135/E142（gettext/libintl 族）在本包无链接面命中——envsubst
  是运行期工具缺失，只在 notes/manifest 披露，不阻塞打包。

## 上游测试（NO_UPSTREAM_TESTS 记录）

结论：**上游无测试套件，用例规模 0，按 NO_UPSTREAM_TESTS 如实记录
（upstream_tests: []）**。检查过的入口与证据：

| 入口 | 检查方式 | 结果 |
|------|----------|------|
| 归档全清单 | 配方 build() 机读文件集合审计（30 文件精确比对） | 无 tests/、无 debian/tests（autopkgtest）、无 *_test.* |
| `debian/rules` | 原文读取 + SHA256 pin | 4 行裸 `dh $@`，无 check/test 目标 |
| 构建/测试 runner | 清单审计 | 无 Makefile/CMake/Meson/tox/pytest/package.json/Cargo.toml；Build-Depends 仅 debhelper-compat |
| CI 配置 | 清单审计 | 无 .gitlab-ci.yml、无 .github/（salsa Debian CI 仅构建/lint） |
| 交叉印证 | orig tarball 实测 | kwartz-cloud/ 子树与快照逐字节一致，同样零测试对象 |

佐证：本包 test_package 的 18 条断言（6 组：harness/零 ELF 不变量/
bash -n 语法门禁/安装面保真/SHA256 逐字节/debconf 模板契约与
conf-desktop 数据流）是对适配可验证面的真实验证；不声称"入域功能可用"
（zsdx box2d 教训：不得把无测试当作测试通过）。

## CI 门禁契约备注（no_official_test.txt 白名单）

实测阅读 `ci/conan/build_and_test.sh` L1 段：`no_official_test.txt`
白名单**仅用于跳过 L1 检查**；不进白名单时 L1a 以 conan create 日志中的
test_package 真实执行痕迹判 pass（`grep "Launching test_package|Testing
the package|Running test()"`）。本包 test_package 会被 conan create 真实
执行，故走 zsdx 先例同款 "L1 test_package executed, no whitelist" 路径，
**无需改动任何 ci/** 文件**（Scout 报告 §4 的"需新增一行"判断与脚本
实际契约不符，以脚本为准）。

## OHOS 适配要点与诚实披露

- 纯 POSIX 能力级适配，全程无平台宏、无平台分支（R8）：适配 = 原样安装
  + 机读保真审计 + 消费者冒烟。
- **功能不可达披露**：入域功能栈（LDAP/NSS、PAM-LDAP、winbind/CIFS、
  debconf、apt）在 OHOS 不可达；验证面 = "装得上 + 语法对 + 模板契约
  断言过"。kwartz-cloud 的 zenity/host/nemo、tpl 的 root 与 Debian 系统
  路径假设均在 manifest/EXCLUDED-TESTS.md 披露。
- postinst 的 envsubst 渲染属 dpkg/debconf 生命周期，OHOS 上不会发生：
  模板按 Debian 原位（share/doc/kwartz-client/）原样交付，其"渲染产物
  必须是合法 shell"这一前提由 bash -n 断言保障。
- copyright 声明的上游 https://forge.aeif.fr/Romain/integration_gnu_linux_kwartz
  本网络 DNS 不可达（Scout 实测），权威可取源为 Debian 维护的 salsa 仓，
  仅记录不改判。
