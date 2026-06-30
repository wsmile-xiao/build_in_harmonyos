# OpenLDAP

OpenLDAP 是一个开源的 LDAP (Lightweight Directory Access Protocol) 实现，提供目录服务功能。

## 软件信息

- **官网**: https://www.openldap.org/
- **源码**: https://github.com/openldap/openldap
- **分类**: Network/LDAP

## 编译版本

| 版本 | 状态 | 编译日期 | 说明 |
|------|------|----------|------|
| 2.6.7 | published | 2026-05-27 | 禁用 mdb 后端（LMDB robust mutex 不支持） |

## 功能说明

OpenLDAP 提供以下组件：

### 客户端工具
- `ldapsearch` - LDAP 搜索工具
- `ldapmodify` - LDAP 修改工具
- `ldapadd` - LDAP 添加工具
- `ldapdelete` - LDAP 删除工具
- `ldapcompare` - LDAP 比较工具
- `ldapmodrdn` - LDAP 修改 RDN 工具
- `ldappasswd` - LDAP 密码修改工具
- `ldapwhoami` - LDAP 身份验证工具
- `ldapexop` - LDAP 扩展操作工具
- `ldapurl` - LDAP URL 工具
- `ldapvc` - LDAP 验证证书工具

### 服务端工具
- `slapd` - LDAP 服务器主程序
- `slapadd` - 添加条目到数据库
- `slapcat` - 导出数据库内容
- `slapindex` - 重建数据库索引
- `slapmodify` - 修改数据库内容
- `slappasswd` - 生成密码哈希
- `slaptest` - 测试配置文件
- `slapacl` - 检查访问权限
- `slapauth` - 验证身份映射
- `slapdn` - 检查 DN 合法性

## 平台适配说明

### HarmonyOS 特殊处理

1. **HMDFS 临时文件限制**
   - configure 生成的 config.status 无法在 HMDFS 上创建临时文件
   - 解决方案：修改 config.status 使用固定临时目录
   - 参考文档：knowledge/graph/draft/E081-HMDFS-heredoc.kv

2. **LMDB 后端禁用**
   - 鸿蒙平台不支持 robust mutex 函数（pthread_mutexattr_setrobust）
   - 解决方案：禁用 mdb 后端，使用 ldif/monitor/relay 后端
   - 参考文档：knowledge/graph/draft/E082-LMDB-robust-mutex.kv

3. **功能限制**
   - 无法使用高性能 LMDB 数据库后端
   - 只能使用 ldif/monitor/relay 后端
   - 生产环境性能受限

## 依赖

无额外依赖（使用系统自带库）。

## 使用说明

### 安装预编译包

```bash
# 从 cmd-pkgs 安装
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- openldap 2.6.7
```

### 基本使用

```bash
# 查看版本
ldapsearch -V

# 连接 LDAP 服务器
ldapsearch -H ldap://localhost:389 -b "dc=example,dc=com" "(objectClass=*)"

# 启动 LDAP 服务器（使用 ldif 后端）
slapd -h "ldap://localhost:389" -f /path/to/slapd.conf
```

## 注意事项

1. **LMDB 后端不可用**: 由于平台限制，无法使用 mdb 后端
2. **性能受限**: 建议在其他平台编译启用 mdb 后端以获得更好性能
3. **配置文件**: 需要手动编写 slapd.conf 配置文件

## 参考资料

- OpenLDAP 官方文档: https://www.openldap.org/doc/
- ARCHIVE-SPEC: 归档规范文档
- 知识图谱: E081, E082

---
*更新时间: 2026-05-27*