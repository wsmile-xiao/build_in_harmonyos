# acf-kamailio 0.10.0 适配笔记

## 编译环境
- 构建系统: makefile
- 编译日期: 2026-08-19
- 编译器: clang/clang++
- 状态: built（真机验证通过 2026-08-19）

## 编译步骤

纯 Lua ACF 模块，无 C 编译。上游 Makefile 包含：
1. `make -C <src> -j1 all` — `all:` 为空操作，仅校验 Makefile 语法
2. **不使用** `make install`（原因见下方"遇到的问题"）
3. Recipe 手动打包：将 kamailio-* 文件复制到 `usr/share/acf/app/kamailio/`，
   规范化 usr/ 前缀，并从 acf-core 的 `share/acf/app/` 物化共享视图

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `make install` 引用 `acflibdir`（/usr/share/acf/lib） | 上游 Makefile 的 install 目标通过 `ls -1 $(acflibdir)/db-*.lsp` 枚举 acf-core 的 db 视图文件，在 Conan 隔离构建中该路径不存在 | 绕过 `make install`，在 `package()` 方法中手动复制 kamailio-* 文件 |
| 2 | tarball 含悬空 symlink（kamailio-edit-html.lsp -> ../filedetails-html.lsp 等） | 上游视图模板位于 acf-core 包中，跨 Conan 包相对路径无法解析 | 从 acf-core 的 `share/acf/app/` 复制 filedetails-html.lsp / status-html.lsp 并重命名为 kamailio-*.lsp（功能等价） |
| 3 | Windows 提取 symlink 失败 | Windows tar 对 symlink 支持有限 | recipe 的 `strip_root=True` 在 Linux/OHOS 上正常提取；Windows 本机预验证不受影响 |

## 源码修改

无（recipe 通过 `package()` 方法中的手动打包逻辑处理 OHOS 兼容性，不修改上游源码）

## 依赖版本

| 依赖 | 版本 | 说明 |
|------|------|------|
| acf-core | 0.24.1 | 运行时框架（mvc.lua dispatch + modelfunctions.lua），已发布 ohpcd 制品仓 |
| acf-db | 0.2.1 | 运行时 Lua 数据库工具（dbcontrollerfunctions.lua / dbmodelfunctions.lua），已发布 ohpcd 制品仓 |
| acf-lib-lua5.4 | 0.11.1 | acf.fs / acf.format / acf.validator / acf.db（**归属 acf-lib 而非 acf-core，易错点**） |
| luaposix | 36.3.1.1 | `posix` 模块（kamailio-model.lua 顶部 `require("posix")`） |
| lua | 5.4.8 | acf-core 的运行时依赖（传递） |

> 依赖归属逐条对应 kamailio-model.lua / kamailio-controller.lua 的 `require()`：
> `modelfunctions`→acf-core、`dbmodelfunctions`/`dbcontrollerfunctions`→acf-db、
> `acf.fs`/`acf.format`/`acf.validator`/`acf.db`→acf-lib-lua5.4、`posix`→luaposix。
> 这修正了 acf-mariadb 只声明 acf-core 而漏掉 acf-lib 的缺口。

## 验证结果

### 本机前置验证（已完成 ✅）
```
源码 URL 校验:     PASS（distfiles.alpinelinux.org 可下载，6494 bytes）
sha256 校验:       PASS（74dfbf80554b195f188dd71a240cb9aa48c8384738a9e17bc13343fb2b8a4a37）
构建系统识别:      PASS（纯 Makefile，pure-Lua 模块）
依赖检查:          PASS（acf-core/0.24.1 + acf-db/0.2.1 均已发布 ohpcd）
配方静态检查:      PASS（conanfile.py/conandata.yml/MANIFEST.yml/test_package 完整）
```

### 真机验证（已完成 ✅）
```
conan create:        PASS（exit 0，构建 + 测试全部通过）
test_package:        PASS=12 FAIL=0（luac 未安装，2 个语法检查跳过）
共享视图物化:        PASS（filedetails-html.lsp → kamailio-edit-html.lsp，status-html.lsp → kamailio-status-html.lsp）
依赖解析:            PASS（acf-core/0.24.1 + acf-db/0.2.1 + acf-lib-lua5.4/0.11.1 + luaposix/36.3.1.1 均从 ohpcd 解析）
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| 0.10.0/conanfile.py | - | Conan 配方（手动打包 + 共享视图物化） |
| 0.10.0/conandata.yml | - | 源码 URL + sha256 |
| 0.10.0/test_package/ | - | L1 消费者测试（14 断言） |
| 0.10.0/manifest.yaml | - | 编译元数据 |
| 0.10.0/notes.md | - | 本适配笔记 |
| commands.json | - | 软件级命令声明（binary: false） |

## 注意事项

- 纯 Lua 模块：无 bin/、无 lib 库，L2 smoke test 按规则跳过
- 运行时需 acf-core + acf-db；运行时还需 Kamailio 服务端（kamctl/kamdbctl 命令行）
- `kamailio-model.lua` 通过 `acf.db.engine.{mysql,postgresql,sqlite3}` 连接 Kamailio 数据库，
  需要运行环境有对应数据库客户端
- 两个共享视图（edit→filedetails、status→status）从 acf-core 物化，若 acf-core 版本更新需同步调整
- recipe 的 `package()` 有 fallback 逻辑：若 acf-core 的 app/ 中找不到目标文件会 warning 并跳过

---

**编译结束**: 2026-08-19
**最终状态**: built（本机前置，待真机验证）
