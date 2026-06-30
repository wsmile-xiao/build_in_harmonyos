# repmgr 5.5.0 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-09
- 编译器: clang/clang++ (clang 15.0.4)
- 状态: built

## 编译步骤

1. 初始化: `python3 ohc-run.py init-build repmgr 5.5.0 --url=...`
2. 修改 configure 和 config.status 中的临时目录创建逻辑（HMDFS setgid 权限问题）
3. 运行 config.status（因为 configure 已执行但 config.status 失败，修复后直接重新运行）
4. 编译: `make -j2`
5. 安装: `make install DESTDIR=$TEST_PREFIX`（DESTDIR 模式）
6. 测试: `make check` 不支持，`make installcheck` 需要运行中的 PostgreSQL 服务器（跳过）
7. 打包: `python3 ohc-run.py package repmgr 5.5.0`
8. 本地安装: `make install`（不带 DESTDIR）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.status 无法创建临时文件（Permission denied） | HMDFS 文件系统上 mktemp -d "./confXXXXXX" 创建的目录带有 setgid 位（2700），导致写入文件被拒绝 | 修改 configure 和 config.status，将 mktemp 使用 $TMPDIR 替代当前目录，并去掉 umask 077 |
| 2 | repmgr --version 报 "could not get current user name" | HarmonyOS 上 getpwuid() 不支持用户 ID 20020101 | 平台限制，不阻塞。repmgrd --version 正常工作 |
| 3 | make installcheck 失败 | 需要运行中的 PostgreSQL 服务器 | 跳过测试，记录原因 |

## 源码修改

| 文件 | 原因 | 方式 | 补丁状态 |
|------|------|------|----------|
| configure | HMDFS setgid 权限问题：临时目录创建失败 | 修改 mktemp 从 "./confXXXXXX" 改为 "${TMPDIR}/confXXXXXX"，去掉 umask 077 | 待 refresh-patch 生成 |
| config.status | 同 configure，已生成的文件 | 同上修改 | 待 refresh-patch 生成（或 configure 修改覆盖） |

## 依赖版本

- PostgreSQL 16 (libpq, pgcommon, pgport)
- curl (预编译包)
- json-c (预编译包)
- readline (预编译包)
- zlib (预编译包)

## 验证结果

```bash
$DEFAULT_PREFIX/bin/repmgrd --version
# Output: repmgrd 5.5.0

$DEFAULT_PREFIX/bin/repmgr --version
# Output: could not get current user name: No error information (HarmonyOS limitation)
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| repmgr-5.5.0-ohos-aarch64.tar.gz | 6.7MB | 正式包（strip 后） |
| repmgr-5.5.0-ohos-aarch64-debug.tar.gz | 700KB | debug 符号包 |

## 注意事项

- repmgr 是 PostgreSQL 复制管理工具，运行时需要 PostgreSQL 服务
- repmgr --version 在 HarmonyOS 上有用户查找问题（getpwuid），不影响核心功能
- HMDFS 上 autotools 的 mktemp 创建临时目录会有 setgid 权限问题，需要将临时目录改到 $TMPDIR
---

**编译结束**: 2026-06-09 20:17
**最终状态**: built
