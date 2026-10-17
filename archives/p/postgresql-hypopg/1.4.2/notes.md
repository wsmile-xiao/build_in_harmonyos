# postgresql-hypopg 1.4.2 适配笔记

## 编译环境
- 构建系统: pgxs (PostgreSQL Extension Building Infrastructure)
- 编译日期: 2026-06-02
- 编译器: clang
- 状态: published

## 编译步骤

1. **下载源码**: 从 GitHub 下载 HypoPG/hypopg 1.4.2 tarball
   - URL: https://api.github.com/repos/HypoPG/hypopg/tarball/1.4.2

2. **编译**: 使用 PGXS 构建系统
   ```bash
   make PG_CONFIG=/storage/Users/currentUser/usr/local/bin/pg_config
   ```

3. **安装**: 安装到 staging 目录
   ```bash
   make install DESTDIR=$TEST_PREFIX PG_CONFIG=/storage/Users/currentUser/usr/local/bin/pg_config
   ```

4. **质量门禁**: 通过 G1-G4 验证
   - G1: 二进制完整性 - PASS
   - G2: 功能可用性 - PASS (⚠️ 1 警告：PostgreSQL 扩展无独立 --version)
   - G3: 可移植性 - PASS
   - G4: 档案完整性 - PASS

5. **打包**: 创建预编译包
   - postgresql-hypopg-1.4.2-ohos-aarch64.tar.gz (75KB)

6. **本地安装**: 安装到 ~/usr/local 进行验证

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | URL 搜索失败 | 脚本不支持 GitHub API URL 格式 | 手动查询 GitHub releases API，获取 tarball URL |
| 2 | G4 门禁失败 | manifest.yaml 缺少顶级 build_system 字段 | 添加 build_system: pgxs 字段 |

## 源码修改

无补丁，使用原始源码编译。

## 依赖版本

- PostgreSQL 17.0 (提供 pg_config 和 PGXS 构建系统)

## 验证结果

```bash
# 安装产物验证
ls -la ~/usr/local/lib/postgresql/hypopg.so
-rwxrwx--- 1 file_manager 59712 hypopg.so

ls -la ~/usr/local/share/postgresql/extension/hypopg*
hypopg.control (扩展控制文件)
hypopg--*.sql (版本迁移 SQL 文件)
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| postgresql-hypopg-1.4.2-ohos-aarch64.tar.gz | 75KB | 预编译包 |
| hypopg.so | 55KB | PostgreSQL 扩展共享库 |
| hypopg.control | 148B | 扩展控制文件 |
| hypopg--*.sql | 多个 | 版本迁移 SQL 文件 |

## 注意事项

1. **构建系统**: hypopg 使用 PGXS (PostgreSQL Extension Building Infrastructure)，不是标准的 autotools/cmake
2. **依赖**: 必须先安装 PostgreSQL (pg_config 命令)
3. **验证**: PostgreSQL 扩展无法通过 --version 直接验证，需要在数据库中加载测试

---
**编译结束**: 2026-06-02 12:49
**最终状态**: published
---

**编译结束**: 2026-08-22 08:31
**最终状态**: built

**Conan adaptation completed**: 2026-08-22
**PR**: https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/merge_requests/4667
<!-- CI trigger -->
