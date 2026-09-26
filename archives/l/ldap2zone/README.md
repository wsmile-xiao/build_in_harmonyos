# ldap2zone 0.2 — HarmonyOS PC 适配说明

## 概况

`ldap2zone` 从 LDAP 目录（dnszone schema）读取 DNS zone 记录并打印标准
ASCII zone 文件；配套 `ldap2bind` 脚本从 LDAP 重建 BIND 配置与 zone 文件。

- 上游：https://salsa.debian.org/debian-edu-pkg-team/ldap2zone（原始作者主页已下线，Debian Edu 团队维护打包）
- 形态：makefile（单 C 文件，无 configure/install/check 目标）
- 产物：`bin/ldap2zone`、`bin/ldap2bind`、`share/man/man1/*.1`
- 依赖：openldap/2.6.7
- 许可证：ISC

## 适配要点

| # | 问题 | 处理 |
|---|------|------|
| 1 | 上游 Makefile 硬编码 `gcc` | `build()` 复述编译行，CC 从 Conan conf 获取（R33），不打手写补丁 |
| 2 | 是否需 `-DLDAP_DEPRECATED=1` | 不需：仅用现代 LDAP API（`ldap_initialize` 等） |
| 3 | 无 `make install` | `package()` 直接 copy 二进制、手册 |
| 4 | CLI 工具门禁 | 软件级 `commands.json` |
| 5 | 上游零测试 | live R51 审计 + `no_tests` 标记；MANIFEST 审计字段齐全 |

## 测试

### 上游

上游 **0** 测试（orig 包 8 个文件，无 tests 目录、无 check 目标）。

### 消费者测试（test_package）

`test_package/test_ldap2zone.sh` 共 **3** 条断言：无参用法+exit 1、
非 LDAP URL 拒绝+exit 1（零网络）、`ldap2bind` 存在且 `sh -n` 通过。

## 已知限制

- 真实 zone 转换需 LDAP 服务器，CI/真机无此环境，测试止于 CLI 契约层。
- Windows/macOS 未验证（`validate()` 限定 Linux/OHOS）。
