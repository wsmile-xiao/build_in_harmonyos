# ldap2zone 0.2 — HarmonyOS PC 适配说明

## 概况

`ldap2zone` 从 LDAP 目录（dnszone schema，BIND LDAP 后端所用）读取一个 DNS zone
的全部记录，向 stdout 打印标准 ASCII zone 文件。配套 shell 脚本 `ldap2bind`
定时从 LDAP 重建 BIND 配置与 zone 文件。产物为 `bin/ldap2zone`、
`bin/ldap2bind` 与两份 man 手册。

- 上游作者：Stig Venaas（原始主页 http://www.venaas.no/dns/ldap2zone/ 已下线；
  Debian Edu 团队接管打包，VCS 见 homepage）
- 上游版本：0.2（Debian `ldap2zone_0.2.orig.tar.gz`，即纯净上游 tarball）
- 形态：makefile（单 C 文件，无 configure/install/check 目标）
- 依赖：openldap/2.6.7（制品仓已发布，对齐 ldap2dns 0.3.1 先例）
- 许可证：ISC（源码头为标准的 ISC 授权文字，见下）
- 上游测试：0（R51 已审计，见“测试/上游”）

## 上游溯源

- 原始主页（man 页 See Also，现已不可达）：http://www.venaas.no/dns/ldap2zone/
- Debian 源码包：`ldap2zone_0.2-12.dsc`（含 PGP 签名），其中
  `Checksums-Sha256` 给出 orig 包
  `a54e95be122a07438936818b4966665bd108a8217c39bac760922e7ed994eaac`
  （7743 字节），与本配方 `conandata.yml` 一致。
- `conandata.yml` 使用 `deb.debian.org` 的 orig URL（纯净上游包，非 Debian
  重打包；对齐同日合入的 tnef 1.4.18 先例）。
- 许可证证据（`ldap2zone.c` 头）：
  `Copyright (C) 2004, 2005 Stig Venaas` + `Permission to use, copy, modify,
  and distribute this software for any purpose with or without fee is hereby
  granted, provided that the above copyright notice and this permission notice
  appear in all copies.`——即 ISC 授权文字，故 `license = "ISC"`。

## 适配要点

| # | 问题 | 处理 |
|---|------|------|
| 1 | 上游 Makefile 硬编码 `gcc`（`gcc -Wall ldap2zone.c -o ldap2zone -lldap -llber`），真机/CI 无 gcc | 不在 Makefile 上打补丁（手写补丁违反审查规则 R18），而是在 `build()` 里逐字复述该编译行，CC 从 `tools.build:compiler_executables` 获取（R33），`-I/-L` 指向 openldap 包目录（复用 ldap2dns 0.3.1 模式） |
| 2 | 是否需要 `-DLDAP_DEPRECATED=1`（ldap2dns 需要） | 不需要：ldap2zone 只用现代 LDAP API（`ldap_initialize`/`ldap_search_ext`/`ldap_result`/`ldap_first_entry`/`ldap_get_values_len`/`ldap_first_attribute` 等），OpenLDAP 2.6 头文件无条件声明这些符号 |
| 3 | 上游无 `make install` | `package()` 直接 copy：`ldap2zone`、`ldap2bind` → `bin/`；两份 `.1` 手册 → `share/man/man1/` |
| 4 | CLI 工具门禁（R38） | 软件级 `commands.json`（`type: tool`） |
| 5 | 上游零测试 | `build()` 做 live R51 审计并打印 `HMBS_UPSTREAM_TEST_RESULT`（`status: no_tests`）；`test_package/MANIFEST.yml` 写 `upstream_tests_exist: false` + 审计原文 + `upstream_test_total: 0` |

## 测试

### 上游（R51 申报）

- **上游测试数：0（上游确无测试）**
- 清点证据（`ldap2zone_0.2.orig.tar.gz` 解包后，8 个成员）：
  - `ldap2zone/`、`ldap2zone/Makefile`、`ldap2zone/ldap2bind.1`、
    `ldap2zone/changelog`、`ldap2zone/ldap2zone.1`、`ldap2zone/ldap2zone.c`、
    `ldap2zone/dnszonehowto.html`、`ldap2zone/ldap2bind`
  - 无 `tests/`/`test/` 目录，无任何 `*test*`/`*check*` 文件
  - Makefile 仅定义 `all` 与 `ldap2zone` 两个目标，无 check/test/installcheck
- 因此无上游测试可运行；`conanfile.py build()` 打印带审计证据的
  `no_tests` 标记，`MANIFEST.yml`  carries `upstream_test_total: 0`
 （口径 `auto`：单一 make 框架，可解析——无 check 目标即 0）。

### 消费者测试（test_package）

`test_package/test_ldap2zone.sh` 共 **3** 条断言，真实运行安装后的二进制
（`VirtualRunEnv` 提供 openldap 运行时库路径；`env="conanrun"`）：

1. 无参运行 → stderr 打印 `Usage: ... zone-name LDAP-URL default-ttl [serial]`，
   退出码 1（`usage()` 行为，未崩溃）。
2. `ldap2zone myzone. http://example.com/ 3600` → `Not an LDAP URL`，
   退出码 1。argv 与 URL-scheme 校验发生在 `ldap_initialize()` 之前，
   全程零网络。
3. `ldap2bind` 存在、非空且通过 `sh -n` 语法检查。

`test()` 末尾打印 `HMBS_TEST_PACKAGE_RESULT`
（`discovered`/`passedCount` 均为脚本内断言数 3）。

### 证伪说明（harness 有效性）

- 断言 1/2 同时检查“特征串出现”与“退出码为 1”：若二进制被换成恒返回 0
  的桩，`rc` 检查即失败；若 usage/错误文案丢失，`grep` 检查即失败。
  不存在“静默跳过计为通过”的分支（任一失败 → `fails+1` → 脚本 exit 1 →
  `self.run` 抛错 → `HMBS_TEST_PACKAGE_RESULT` 行不会打印）。

## 已知限制

- 无参/`-h` 行为：`usage()` 向 stderr 打印用法并 `exit(1)`（上游行为，
  测试按此断言，不修改语义）。
- 真实 zone 转换需可达的 LDAP 服务器（含 dnszone 数据），CI/真机无此环境，
  故消费者测试止于 CLI 契约层；已在断言层面保证 harness 有效性。
- Windows/macOS 未验证（`validate()` 限定 Linux/OHOS，对齐 tnef 先例）。

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Makefile 单文件构建配方，requires openldap/2.6.7；application 包 |
| conandata.yml | deb.debian.org orig URL + sha256（.dsc 签名交叉验证） |
| test_package/ | R34 实质测试（运行 ldap2zone + 语法检查 ldap2bind） |
| manifest.yaml | 版本级归档信息（状态 built，待真机回填） |
| commands.json | R38 工具声明（软件级） |
| notes.md | 本文件 |

## 验证状态

- 本轮仅完成未提交工作树；`conan create` 真机预检尚未运行，
  `manifest.yaml` 中计数待首轮预检日志回填。
