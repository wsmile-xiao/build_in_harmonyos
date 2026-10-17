# EXCLUDED-TESTS.md — kwartz-client 3.0 上游测试排除说明

## 结论：NOT_APPLICABLE / NO_UPSTREAM_TESTS（上游零测试，无可排除对象）

本文件不是"逐条排除理由"清单，而是**零测试上游的判定证据链**（沿用
zsdx-1.12.3 / launchctl-completion-2.0 先例范式）：上游从未有过测试套件，
因此既无 NOT_RUN 对象（NOT_RUN 语义是"有测试但被跳过"），也无从移植。

## 判定证据（四证据，均可独立复核）

判定基于对 salsa 发布 tag `debian/3.0-17`（commit
17208cb88caf19c3074df506b4fa3f2e064a11c2，归档 sha256
8093f591b9dec4085061fa3a7e87220d1d44562d92aab64de791d5cceb5c8167）
的完整清单审计：

1. **归档全清单 30 个文件，配方 build() 机读复核文件集合**（EXPECTED_FILES
   精确比对）：kwartz-cloud/ 6 文件（POSIX sh 脚本 + man/svg/desktop/conf/
   appstream xml）+ README.md + .gitignore + debian/ 22 文件（changelog/
   control/copyright/config/install/manpages/postinst/postrm/rules/
   templates/kwartz-install.tpl + po/ 10 文件 + source/format）。无 tests/、
   test/、spec/ 目录，无任何 `*_test.*` / `test_*` 文件。
2. **无任何测试入口**：`debian/rules` 全文 4 行 = 裸 `dh $@`
   （sha256 9e4a977c… 固定于配方 SOURCEFACE_SHA256），无 check/test override；
   无 Makefile/CMake/Meson/tox.ini/pytest.ini/package.json/Cargo.toml 等
   任何测试 runner 配置；`debian/control` 的 Build-Depends 仅
   `debhelper-compat (= 13)`，无测试类构建依赖。
3. **无 autopkgtest**：`debian/` 下不存在 `tests/` 目录（dep-8 测试的
   标准位置），`.gitlab-ci.yml` / `.github/` 也均不存在——salsa 上的
   Debian CI 只做构建与 lint，仓库内无任何测试定义。
4. **交叉印证**：Debian orig tarball（kwartz-client_3.0.orig.tar.xz，
   sha256 7a15f5f7…，本 run 实测下载复核）内容与 tag 快照的
   kwartz-cloud/ 子树逐字节一致（diff -r 干净），其 8 文件中同样无任何
   测试对象。

## 与 OHOS 适配点的对应关系（冒烟为何这样设计）

上游零测试时没有可移植的测试对象，断言对象替换为"适配动作本身做对了没"：

| 冒烟组 | 对准的适配决策 |
|---|---|
| A 组（2 条） | harness 就位：repo 发布的 bash/5.3 真实可用、被测包图解析成功 |
| B 组（3 条） | 纯 shell 数据包不变量：bin/kwartz-cloud 可执行、非 ELF、全包零 ELF——零编译适配（无签名、L4 readelf 空转）的结构性证明 |
| C 组（3 条） | 语法门禁：bash -n 解析脚本与模板（模板经 postinst envsubst 渲染成 /usr/sbin/kwartz-install.sh root 脚本，替换前必须是合法 shell）；POSIX sh shebang，不依赖 /bin/bash |
| D 组（5 条） | 安装面保真：对齐 debian/kwartz-client.install + manpages 的五件放置 + GPL 许可面 |
| E 组（2 条） | E241 数据保真：安装件 sha256 与上游逐字节一致 |
| F 组（3 条） | 数据流契约：模板含 postinst 导出的全部 8 个 envsubst 变量；script↔conf 的 source 契约；desktop→bin 启动链 |

## 功能面诚实披露（不属测试排除，属运行期限制）

- kwartz-client 的功能目标态（LDAP/NSS 入域、PAM-LDAP 认证、winbind/
  CIFS 挂载、debconf 问卷、apt 代理与定时升级）依赖的 Debian 运行时栈
  （gettext-base/envsubst、libnss-ldapd、libpam-ldapd、cifs-utils、
  winbind、smbclient、libpam-mount、net-tools、oidentd、inetutils-inetd、
  debconf 等 12 项）在 OHOS 上无对应物：**"可入域"不可达**，本包交付
  "装得上 + 语法对 + 模板契约断言过"的验证面。
- `kwartz-cloud` 需要 zenity/host/nemo GUI 栈，OHOS 无预装：脚本本体
  可解析、可安装，执行到 GUI 分支会失败——上游内容按数据包忠实原则
  一字不改。
- `kwartz-install.tpl` 首行检查 `id -u`=root 并写 /etc/cron.d、
  /etc/apt、/etc/pam.d 等系统路径：OHOS 上不可照搬执行，仅作为模板
  交付并做语法/契约断言。
