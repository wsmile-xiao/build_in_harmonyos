# Bonsai — OpenHarmony 编译档案

## 软件简介
Bonsai 是一个用于处理 LDAP 操作的 Python 3 模块，使用 Unix 上的 libldap2 和 Windows 上的 WinLDAP C 库。LDAP 条目映射为特殊的 Python 大小写不敏感字典，可轻松跟踪字典变化并在服务器上修改条目。仅支持 Python 3.10+ 和 LDAPv3。

## 功能概述
- 使用 C 编写的 LDAP 库（OpenLDAP / WinLDAP）实现快速处理
- 简洁的 Pythonic 设计
- 实现类字典对象映射 LDAP 条目
- 支持多种异步库（asyncio、gevent、tornado、trio）
- 支持 LDAPv3、TLS、SASL、Kerberos（可选）

## OHOS 适配要点
- Python C 扩展需链接 `ldap`、`lber`，可选 `krb5`/`gssapi`
- `setup.py` 中 `BuildExt` 会测试 Kerberos 能力，有则自动添加宏 `HAVE_KRB5`
- HarmonyOS 上若未安装 `openldap-dev`/`libldap2-dev`，回退为纯 Python 安装，离线功能（DN/URL/LDIF 解析）仍可用
- 上游测试：离线测试（`test_ldapdn`、`test_ldapurl` 等）无需服务器；网络测试需 `slapd` Docker 环境，OHOS 上标记为跳过

## 参考资料
- [Bonsai GitHub](https://github.com/noirello/bonsai)
- [Bonsai 文档](https://bonsai.readthedocs.io/)
