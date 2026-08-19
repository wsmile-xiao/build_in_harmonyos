# acf-mariadb 0.2.0 适配笔记

## 编译环境
- 构建系统: makefile
- 编译日期: 2026-08-19
- 编译器: clang/clang++
- 状态: built

## 编译步骤

纯 Lua ACF 模块，无 C 编译。上游 Makefile 包含：
1. `make -C <src> -j1 all` — `all:` 为空操作，仅校验 Makefile 语法
2. **不使用** `make install`（原因见下方"遇到的问题"）
3. Recipe 手动打包：将 mysql-* 文件复制到 `usr/share/acf/app/mysql/`，并创建到 acf-core lib/ 的相对 symlink

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `make install` 引用 `acflibdir`（/usr/share/acf/lib）导致失败 | 上游 Makefile 的 install 目标通过 `ls -1 $(acflibdir)/db-*.lsp` 枚举 acf-core 的 lib 文件，在 Conan 隔离构建中该路径不存在 | 绕过 `make install`，在 `package()` 方法中手动复制 mysql-* 文件 |
| 2 | tarball 含 symlink（mysql-expert-html.lsp -> ../expert-html.lsp 等）在 Windows 提取失败 | Windows tar 对 symlink 支持有限；目标文件不在 tarball 中 | recipe 的 `strip_root=True` 在 Linux/OHOS 上正常提取；Windows 本机预验证不受影响 |
| 3 | 跨 Conan 包的 symlink 路径无法用相对路径正确解析 | acf-mariadb 和 acf-core 是独立 Conan 包，package_folder 路径不同，相对路径 `../../lib/` 无法跨包解析 | 从 acf-core 的 `share/acf/app/` 直接复制基础视图模板（`expert-html.lsp`、`logfile-html.lsp`、`status-html.lsp`）并重命名为 `mysql-*.lsp`（功能等价于上游 symlink） |
| 4 | `usr/` 前缀规范化顺序 | symlinks 创建必须在 `usr/` 规范化之后进行，否则相对路径失效 | 先复制文件到 `usr/share/acf/app/mysql/`，再执行 `usr/` → 根目录规范化，最后从 acf-core 复制共享视图 |
| 5 | acf-core 的共享视图在 `share/acf/app/` 而非 `share/acf/lib/db-*` | 真机验证发现 acf-core 0.24.1 的 `share/acf/lib/` 中没有 `db-*.lsp`；基础视图模板（`expert-html.lsp`、`logfile-html.lsp`、`status-html.lsp`）实际位于 `share/acf/app/` | 修正 recipe 的 view_map 源路径为 `share/acf/app/`，源文件名去掉 `db-` 前缀 |

## 源码修改

无（recipe 通过 `package()` 方法中的手动打包逻辑处理 OHOS 兼容性，不修改上游源码）

## 依赖版本

| 依赖 | 版本 | 说明 |
|------|------|------|
| acf-core | 0.24.1 | 运行时框架（mvc.lua 分发 + acf.db/acf.fs/acf.format），已发布 ohpcd 制品仓 |
| acf-db | 0.2.1 | 运行时 Lua 数据库工具（dbcontrollerfunctions.lua / dbmodelfunctions.lua），已发布 ohpcd 制品仓 |
| lua | 5.4.8 | acf-core 的运行时依赖（传递） |

## 验证结果

### 本机前置验证（已完成）
```
源码 URL 校验:     PASS（distfiles.alpinelinux.org 可下载，2247 bytes）
sha256 校验:       PASS（1db5dc9a9adc81e32fea335b037d6bdfcef966bbb70d37eee1944dfb8dab941d）
构建系统识别:      PASS（纯 Makefile，pure-Lua 模块）
依赖检查:          PASS（acf-core/0.24.1 + acf-db/0.2.1 均已发布 ohpcd）
配方静态检查:      PASS（conanfile.py/conandata.yml/MANIFEST.yml/test_package 完整）
```

### 真机验证（已完成 ✅）
```
conan create:        PASS（构建 + 测试全部通过）
test_package:        PASS=11 FAIL=0
共享视图复制:        PASS（expert/logfile/status 从 acf-core 的 share/acf/app/ 复制成功）
包内容:              8 文件（2 .lua + 4 .lsp + .menu + .roles）
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| packaging/acf-mariadb-0.2.0.tar.gz | 2.2K | 上游源码 tarball（与 conandata.yml 一致） |

## 注意事项

- 纯 Lua 模块：无 bin/、无 lib 库，L2 smoke test 按规则跳过
- 运行时需 acf-core + acf-db；运行时还需 MariaDB 服务端/客户端（mysqladmin、mysql CLI）
- `mysql-model.lua` 中 `determineconnection()` 使用 `acf.db.engine.mysql` 连接本地 MariaDB，需要 mysql 客户端库
- 三个 symlink（expert/logfile/status 视图）指向 acf-core 的 db-*.lsp，如果 acf-core 版本更新可能需要同步调整
- recipe 的 `package()` 有 fallback 逻辑：如果 acf-core lib/ 中找不到目标文件会改用 copy

---

**编译结束**: 2026-08-19
**最终状态**: built
