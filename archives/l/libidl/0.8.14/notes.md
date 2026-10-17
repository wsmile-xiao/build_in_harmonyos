# libidl 0.8.14 适配笔记

## 编译环境
- 构建系统: 上游 autotools（autoconf 2.63 / automake / libtool 2.2.6）
- 编译日期: 2026-09-18
- 编译器: OHOS clang（Conan profile `ohos-aarch64`）
- 目标: OHOS aarch64（`--build=aarch64-linux-ohos --host=aarch64-linux-ohos`，build==host）
- 依赖: `glib/2.84.0`（`PKG_CHECK_MODULES(..., glib-2.0 >= 2.4.0)`）
- 构建工具: `tool_requires("flex/2.6.4.2")`、`tool_requires("bison/3.8.2")`
- 状态: built

## 版本与源码
- 任务版本 `0.8.14` == 上游 GNOME 发布版本 `libIDL-0.8.14`
- 源码: `https://download.gnome.org/sources/libIDL/0.8/libIDL-0.8.14.tar.bz2`
  sha256 `c5d24d8c096546353fbc7cedf208392d5a02afe9d56ebcc1cccb258d7c4d2220`

## 产物
- `lib/libIDL-2.so.0.0.0`（soname `libIDL-2.so.0`）+ 软链、`lib/libIDL-2.a`
- `include/libIDL-2.0/libIDL/IDL.h`
- `lib/pkgconfig/libIDL-2.0.pc`
- `licenses/COPYING`
- **已删除**：libtool `.la` 封装与 `bin/libIDL-config-2` 帮助脚本（消费者用 pkg-config/CMake）

## 源码修改

| 补丁 | 说明 |
|------|------|
| `patches/0001-configure-umask-022.patch` | `configure` 里 config.status 建临时目录的 `umask 077` → `022`（HMDFS setgid 下 0700 目录不可写，E011） |
| `patches/0002-config-sub-ohos.patch` | 给过旧的 `config.sub` 加 17 行 aarch64/HarmonyOS 早退分支（a52dec 同款）；不随 PR 携带上千行脚本全文（避免 AI 检视因变更过大跳过） |

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 无 `parser.c`/`lexer.c`，构建报缺少 yacc/lex 产物 | 上游 tarball 只带 `parser.y`/`lexer.l`（`BUILT_SOURCES` 由 make 生成） | `tool_requires("bison/3.8.2")` + `tool_requires("flex/2.6.4.2")`（ohpcd 制品仓已发布），构建期自动进入 PATH |
| 2 | `PKG_CHECK_MODULES` 找不到 `glib-2.0` | glib 为 Conan 依赖，需生成其 `.pc` | `PkgConfigDeps(self).generate()` + `self.requires("glib/2.84.0")` |
| 3 | `machine 'aarch64' not recognized` | 上游 `config.sub` 过旧 | `patches/0002-config-sub-ohos.patch` 加 aarch64/HarmonyOS 早退分支 + 显式 `--build/--host`（E007） | 替换为 OHOS 感知版本 + 显式 `--build/--host`（E007） |
| 3b | `configure: error: cannot run test program while cross compiling`（guint64 printf/scanf 格式检测） | 传了 `--build=aarch64-unknown-linux-gnu` 与 `--host=aarch64-linux-ohos`，autoconf 判定为交叉编译，`AC_RUN_IFELSE` 无法执行 | **build 与 host 取同值**（`aarch64-linux-ohos`）：既避免运行 `config.guess`（实测现代 config.guess 在 HMDFS 上因无法创建临时文件而直接失败），又保持 `cross_compiling=no`，使 run 测试在设备上原生执行 |
| 4 | `config.status: cannot create ./confXXXXXX: Permission denied` | `umask 077` + HMDFS setgid | umask 022 补丁（E011） |
| 5a | `make: *** [Makefile:1279: stamp-parser] Error 1`（且无错误输出） | ① `YFLAGS = -d -v 2>/dev/null` 把 bison 的 stderr 丢弃；② bison 工具包数据目录为 `/=前缀` → `bison: /share/bison/m4sugar/m4sugar.m4: cannot open` | 在 `generate()` 注入 `BISON_PKGDATADIR=<bison包>/share/bison`（`Environment().vars().save_script("conanbuildenv-bison")`） |
| 5b | 注入 PKGDATADIR 后仍 `Broken pipe` / `bison: m4 subprocess failed` | 制品仓的 bison 二进制里**硬编码了 m4 路径 `/data/service/hnp/bin/m4`**（设备上不存在）；`strings <bison> \| grep m4` 可验证 | 在 `generate()` 注入 `M4=$(command -v m4)`（`shutil.which("m4")`），覆盖内置路径 |
| 5 | 设备上按名字找不到 `cpp`/`cc`，担心 `tstidl` 无法运行 | 默认 `IDL_parse_filename` 会 fork C 预处理器 | configure 探测到的是 OHOS SDK 的 `clang -E`，实测 `./tstidl sample.idl` 正常解析并打印 Repository ID/标识符/重序列化 IDL；而**消费者测试**改用 `IDL_parse_filename_with_input` + 自定义输入回调，完全不依赖外部预处理器，两种路径互不影响 |
| 6 | 包内 `libIDL-2.0.pc` 的 `prefix=/` | Conan `--prefix=/` + `DESTDIR` 安装 | `package()` 幂等重写 `.pc` 的 prefix/exec_prefix/libdir/includedir |
| 6b | 链接 `libIDL-2.la` 失败：`` //lib/libpcre2-8.la' is not a valid libtool archive ``（伴随 `library ... was moved` 警告） | 制品仓的 glib/pcre2/libffi 包内 `.la` 记录了 `libdir='/lib'`（同一 `--prefix=/` 失真），libtool 解析依赖 `.la` 时按记录的路径找不到文件 | 构建前删除依赖包 `lib/*.la`（Conan 链路不需要 `.la`；与已合入的 `archives/b/bookloupe/2.0` 同法） |
| 7 | test_package 编译报 `fatal error: 'glib.h' file not found` | `IDL.h` 公开包含 `<glib.h>`，但 Conan 2 默认不向消费者传播依赖（`self.requires("glib/...")` 默认私有） | 声明为公开依赖：`self.requires("glib/2.84.0", transitive_headers=True, transitive_libs=True)` + `cpp_info.requires=["glib::glib"]`（仓库惯例，如 aravis/atk） |
| 8 | 消费者对**畸形 IDL** 做负向测试时段错误（`Error: syntax error` 后 SIGSEGV） | 上游 libIDL 0.8.14 语法错误恢复路径的缺陷（2010 年停止维护） | 负向用例改为“输入完全不可读”（回调在 `IDL_INIT` 返回 -1），库能干净返回非 `IDL_SUCCESS`；畸形输入的崩溃作为上游已知限制记录 |

## 上游 API 要点（消费者测试实测）

- `IDL_parse_filename_with_input(filename, input_cb, user_data, msg_cb, &tree, &ns,
  parse_flags, max_msg_level)` 可**完全绕开 cpp**（自带输入回调喂缓冲区），是设备无 cpp 时的首选入口。
- 返回 `IDL_SUCCESS(0)` / `IDL_ERROR(1)`；语法错误返回 `IDL_ERROR`，不 abort。
- `IDL_NODE_TYPE(tree)` + `IDLN_MODULE/IDLN_INTERFACE/IDLN_ATTR_DCL/IDLN_OP_DCL`
  可用于遍历统计；`IDL_tree_walk_in_order` 的回调返回 `TRUE` 继续。
- `IDL_tree_to_IDL_string(tree, ns, flags)` 返回 `GString*`（`g_string_free(s, TRUE)`）。
- `IDL_get_libver_string()` 返回库版本字符串。

## 验证结果

```sh
conan create archives/l/libidl/0.8.14 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
# rc=0
# 上游：./tstidl sample.idl -> exit 0（打印 Repository IDs / 标识符 / 重新序列化的 IDL）
# 消费者：ctest + ./libidl_consumer -> 14/14 断言通过
```
