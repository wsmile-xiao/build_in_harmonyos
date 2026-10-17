# ldapvi

ldapvi 是面向 Unix 终端的交互式 LDAP 客户端，可用文本编辑器更新 LDAP 条目，
相当于 LDAP 版的 vipw(1)。由 David Lichteblau 编写，GPL-2.0 许可。

## 软件信息

- **官网**: http://www.lichteblau.com/ldapvi/
- **源码**: http://www.lichteblau.com/download/ldapvi-1.8.tar.gz
- **分类**: Network/LDAP (命令行工具)

## 编译版本

| 版本 | 状态 | 编译日期 | 说明 |
|------|------|----------|------|
| 1.8 | built | 2026-08-16 | HarmonyOS PC 适配（依赖 openldap/ncurses/readline/popt/glib/openssl） |
| 1.7 | published | 2026-06-04 | 历史版本 |

## 功能说明

- 交互式查看与编辑 LDAP 条目（编辑器界面）
- LDIF / ldapvi 扩展语法支持
- `--in/--out/--delete/--rename` 批量操作
- SASL 支持（本构建未启用，configure 检测缺失时自动禁用）
