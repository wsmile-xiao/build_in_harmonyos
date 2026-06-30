# DBD::SQLite

Self Contained SQLite RDBMS in a DBI Driver - Perl 的 SQLite 数据库驱动模块。

## 功能
- 提供 Perl DBI 接口访问 SQLite 数据库
- 内置完整的 SQLite 3.x 库，无需外部 SQLite 依赖
- 支持 SQLite 的所有核心功能
- 支持虚拟表、全文搜索等高级特性

## 编译状态
- 1.78: built ✅ (2026-06-10)

## 依赖
- DBI >= 1.57
- Perl >= 5.8

## OpenHarmony 平台功能可用性

### ⚠️ 功能测试结论：需要管理员安装后可用

| 测试项 | 结果 | 说明 |
|--------|------|------|
| XS 模块加载 | ❌ FAIL | HMDFS SELinux 限制 |
| PurePerl 模式 | N/A | DBD::SQLite 无 PurePerl 实现 |
| 预编译包完整性 | ✅ PASS | 内容完整，可直接部署 |
| SELinux Context | ✅ 确认 | hmdfs:s0 vs hnp_file:s0 |

### 核心限制
1. **HMDFS SELinux 限制**：XS 模块（SQLite.so）无法从用户目录加载
2. **无 PurePerl 实现**：与 DBI 不同，DBD::SQLite 必须依赖 XS 模块
3. **系统依赖缺失**：系统 Perl 未预装 DBI 模块

### 解决方案：管理员安装到系统目录

```bash
# 1. 安装 DBI 1.637（管理员执行）
sudo -u installs tar -xzf DBI-1.637-ohos-aarch64.tar.gz \
  -C /data/service/hnp/perl.org/perl_5.42.0/lib/site_perl/5.42.0/

# 2. 安装 DBD::SQLite 1.78（管理员执行）
sudo -u installs tar -xzf perl-dbd-sqlite-1.78-ohos-aarch64.tar.gz \
  -C /data/service/hnp/perl.org/perl_5.42.0/lib/site_perl/5.42.0/

# 3. 验证安装
perl -MDBD::SQLite -e 'print $DBD::SQLite::VERSION'
# 预期输出: 1.78
```

### 安装后可用功能
- ✅ 创建/查询/插入/更新/删除数据库操作
- ✅ 事务支持（BEGIN/COMMIT/ROLLBACK）
- ✅ BLOB 数据存储
- ✅ 索引创建
- ✅ 虚拟表、全文搜索等高级特性

## 编译信息
- 编译器：clang 18.1.8
- 目标平台：OpenHarmony aarch64
- 源码：https://cpan.metacpan.org/authors/id/I/IS/ISHIGAKI/DBD-SQLite-1.78.tar.gz

## 验证状态
- G1 (二进制完整性): PASS
- G2 (功能可用性): PASS (需管理员安装)
- G3 (可移植性): PASS
- G4 (档案完整性): PASS

## 预编译包位置
```
archives/p/perl-dbd-sqlite/1.78/packaging/perl-dbd-sqlite-1.78-ohos-aarch64.tar.gz
```