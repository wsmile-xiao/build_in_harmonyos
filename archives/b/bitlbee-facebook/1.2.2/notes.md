# bitlbee-facebook 1.2.2 适配笔记

## 编译环境
- 构建系统: autotools（tarball 无 configure，需 autogen/autoreconf 自举）
- 编译日期: 2026-09-01
- 编译器: clang 15（OHOS 原生 arm64，非交叉）
- 状态: built

## 软件定位

bitlbee（IRC ↔ IM 网关）的 Facebook Messenger 协议插件。产物为
**facebook.so 动态模块**（bitlbee 运行时 dlopen，入口
G_MODULE_EXPORT init_plugin/init_plugin_info），非命令行工具——
不适用 commands.json（R38）。libdir=plugindir=$libdir/bitlbee。

## 编译步骤

```sh
# 1) 源码（官方 tag tarball）
#    https://github.com/bitlbee/bitlbee-facebook/archive/refs/tags/v1.2.2.tar.gz
# 2) bitlbee 3.6 sdist 复现 install-dev（宿主 conan 包只含二进制）：
#    bitlbee/configure --build=aarch64-unknown-linux-ohos --ssl=openssl
#    （PKG_CONFIG_PATH=conan 依赖 pc；CPPFLAGS=-I<openssl>/include）
#    → 生成 config.h；平铺 *.h lib/*.h protocols/*.h + config.h 为 include/
# 3) 插件构建（配方内全自动）：
#    autoreconf -fi                       # tarball 无 configure
#    + E114 补丁（去 umask 077，见下）
#    ./configure --build=aarch64-unknown-linux-ohos --host=aarch64-unknown-linux-ohos
#      BITLBEE_CFLAGS=-I<bitlbee-dev>/include  BITLBEE_LIBS="-L<la-free>"
#      GLIB_CFLAGS="-I<glib>/include/glib-2.0 -I<glib>/lib/glib-2.0/include"
#      GLIB_LIBS="-L<glib>/lib -L<la-free> -lglib-2.0 -lgobject-2.0 -lgio-2.0 -lgmodule-2.0 -lffi -lpcre2-8 -lz"
#      JSON_CFLAGS="-I<json>/include/json-glib-1.0 -I<json>/include"
#      JSON_LIBS="-L<json>/lib -ljson-glib-1.0"
#      GLIB_GENMARSHAL=<glib>/bin/glib-genmarshal
#    make -j1                             # E074
# 4) conan package：make install（DESTDIR=package_folder，prefix=/）→
#    <package>/lib/bitlbee/facebook.so（删除 facebook.la，E236）
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conan bitlbee/3.6 包无头文件、无 bitlbee.pc | 宿主配方只打包 bin/bitlbee（上游 install-dev 产物不在包内） | 从 bitlbee 3.6 sdist（conandata `bitlbee_dev_source`，sha256 与宿主归档登记一致）复现 install-dev：跑其 configure 生成 config.h + 平铺 38 个头文件为私有 include 目录（同上游 CI 语义） |
| 2 | configure 报 gio-2.0.pc/gobject-2.0.pc 不存在 | conan PkgConfigDeps 只为 glib 生成聚合 glib-2.0.pc（无组件 pc）；bitlbee.pc 需自建 | 不造 pc：pkg.m4 预设变量语义——BITLBEE/GLIB/JSON 的 _CFLAGS/_LIBS 六变量 + GLIB_GENMARSHAL 全部经 AutotoolsToolchain 环境注入，两变量同时非空时 PKG_CHECK_MODULES 完全跳过 pkg-config |
| 3 | config.status: can't create ./confXXXXXX/subs1.awk: Permission denied | E114：HMDFS 上 `umask 077 && mktemp -d` 产生 drwx--S---（0700+setgid，owner 映射 20001006 ≠ 进程身份）不可写目录；chmod 不生效（E046 类） | 生成 configure 后文本替换去掉两处 umask 077（仓库既有模式，abiword-plugin 系列同款）；bitlbee 自身 configure 是定制 shell 脚本无此问题 |
| 4 | libtool: error '//lib/libpcre2-8.la' is not a valid libtool archive | E236：conan pcre2/libffi 包内 .la 文件 libdir='//lib'（打包时 prefix=/）；libtool 对 -L 目录内 .la 优先于 .a | .la-free 私有目录：仅复制 libffi.a/libpcre2-8.a/libz.a（无 .la），GLIB_LIBS 的 -lffi/-lpcre2-8/-lz 经 -L 指向该目录；conan 缓存不动 |
| 5 | BITLBEE_LIBS 从 bitlbee.pc Requires 链拉入全量 -L/-l（复现 #4） | pkg-config 解析 bitlbee.pc → Requires: glib-2.0 → 传递链引入 pcre2/libffi 库目录 | BITLBEE_LIBS 显式设为无害非空值 "-L<la-free>"（非空才触发 pkg.m4 旁路） |
| 6 | ld.lld: relocation R_AARCH64_ADR_PREL_PG_HI21 cannot be used against symbol 'z_errmsg' (zutil.o) | conan zlib/1.3.1 的 libz.a 非 PIC，不能链入共享模块 | 改用 zlib/1.3.1.1（PIC 重建，ohpcd 已发布）；glib/json-glib 不依赖 zlib，无 1.3.1↔1.3.1.1 图冲突；插件运行时确实用 zlib（facebook-util.c fb_util_zlib_deflate/inflate 压缩 MQTT payload），静态嵌入合规 |
| 7 | OHOS libc 不导出 deflate/inflate（dlopen 会失败） | 探索期漏 -lz：共享模块链接允许未定义符号而"成功"，但 DT_NEEDED 仅 libc.so 时 dlopen(RTLD_NOW) 报 symbol not found | 同 #6：PIC libz.a 静态嵌入后未定义符号审计仅剩 bitlbee API 面 + libc 符号 |
| 8 | dlopen(facebook.so, RTLD_NOW) 单独跑失败 register_protocol: symbol not found | **预期语义**：bitlbee 插件靠宿主可执行文件导出符号解析（宿主 bitlbee 全静态但导出 glib/插件 API 动态符号） | test_package 用桩宿主（导出 bitlbee API 全符号面 + -rdynamic）真实 dlopen + 调用两个入口验证 ABI 与注册行为 |
| 9 | CI 沙箱无 automake/libtoolize/pkg.m4 | /data/service/hnp/bin 仅 autoconf 家族；$HOME/.local 对 CI（USER=100）不可见 | tool_requires automake/1.18 + libtool/2.5.4（abiword-plugin 同款）；pkg.m4 随配方 m4/ 导出 + ACLOCAL_PATH 注入（docbook 同款） |

## 源码修改

无补丁（patches: {}）。所有适配在 conanfile.py 内完成：
- configure 生成后的 E114 运行时文本补丁（非源码补丁，属构建步骤）
- bitlbee 头文件供给/bitlbee-dev、.la-free 目录、环境变量注入
- m4/pkg.m4 随配方导出（宏文件，非源码修改）

## 依赖版本

| 依赖 | 版本 | 用途/形态 |
|------|------|-----------|
| glib | 2.84.0 | 静态嵌入（与 bitlbee/3.6、json-glib/1.6.6 图一致）|
| json-glib | 1.6.6 | 静态嵌入 |
| libffi | 3.4.4 | 静态嵌入（gobject 闭包编组）|
| pcre2 | 10.40 | 静态嵌入（glib 闭包拉入）|
| zlib | 1.3.1.1 | 静态嵌入（PIC 重建；插件运行时真实使用）|
| openssl | 1.1.1w | 仅构建期（bitlbee sdist configure --ssl=openssl）|
| bitlbee | 3.6 | 宿主运行时目标（不在 requires——其 conan 包只含二进制，头文件取自同版本 sdist；ABI: plugin_info.abi_version=1）|
| automake/libtool | 1.18 / 2.5.4 | tool_requires（CI 沙箱自举）|

## 验证结果

```bash
# 探索构建（$HOME/tmp/builds/bitlbee-facebook-1.2.2.work）：
make install DESTDIR=$TEST_PREFIX
# → $TEST_PREFIX/storage/Users/currentUser/usr/local/lib/bitlbee/facebook.so (4.3MB)
readelf -d facebook.so | grep NEEDED
# → Shared library: [libc.so]        （唯一 NEEDED——全静态自包含）
nm -D --defined-only facebook.so | grep init_plugin
# → T init_plugin / T init_plugin_info
nm -D --undefined-only facebook.so | <过滤 libc/bitlbee API>
# → 空（除 bitlbee 插件 API 面外无任何未解析符号）

# test_package 桩宿主测试：
./run_test <package>/lib/bitlbee/facebook.so
# → OK: facebook.so loaded (RTLD_NOW), plugin_info{abi=1, name=facebook,
#   version=1.2.2}, init_plugin ran (register_protocol x1, root_command_add x3)
# 断言 6/6 通过（dlopen/ABI三元组/注册行为×2）

# L1e 破坏性反证：
./run_test /nonexistent/facebook.so → FAIL dlopen, exit=1 ✓
# （包内缺失路径由 test_package conanfile 存在性检查硬失败，双保险）
```

## 遗留风险

- **运行时宿主集成未经端到端验证**：桩宿主测试证明模块可加载、ABI
  正确、注册入口行为正确；真实 bitlbee 宿主 dlopen + 登录 Facebook
  的端到端链路需网络账号，无法在 CI 环境验证（如实记录）。
- facebook.so 静态嵌入 glib（宿主 bitlbee 二进制同样静态嵌入自己的
  glib 副本）：两副本间数据结构（GList/GHashTable 等）跨边界传递为
  纯内存操作，安全；插件 GType/GObject（FbApi/FbMqtt）自成体系不经
  宿主；事件循环经 bitlbee b_* API（非跨副本 GMainContext），无已知
  功能性风险——但双副本场景上游未设计，属适配架构差异。
- zlib 上游版本差异：包内静态嵌入 1.3.1.1（=1.3.1 的 PIC 重建），
  系统另有 /usr/lib/libz.so.1 (1.2.13)——模块未链接系统副本，无冲突。
---

**编译结束**: 2026-09-01 16:42
**最终状态**: built

---

## W4 提交阶段运维记录（2026-09-01）

- **僵尸 rebase 状态**：工作区曾残留空壳 `.git/rebase-merge/`（仅含 autostash
  引用，无 todo/orig-head），导致一切 `git commit` 报 "You are currently
  rebasing"。`git rebase --quit` 安全清除（autostash 自动转为普通 stash 条目，
  不动工作区）。教训：rebase 失败后必须确认状态目录已清理。
- **ohc-run.py 必须用项目仓自己的 `scripts/ohc-run.py`**：直接调用 skill 资源
  目录（~/.opendesk/apps/skills/resources/openharmony-compile-agent/scripts/）
  会把 ARCHIVE_DIR 解析到 skill 模板树（find_project_dir 按 SKILL.md 定位），
  Gate 1 误报 finish 未完成，且在模板树里留下 .handoff.json 残留（已清理）。
- **已全部提交时 submit 的 commit 步骤**：本机 git 2.45.2 在脏树（他人未提交
  文件共存）下输出 "no changes added to commit"（stdout），工具仅识别
  "nothing to commit" 变体，会误报 git_commit_failed 且错误信息为空。绕行：
  保证归档内有真实待提交内容（本节即为此留），或提交前保持工作树干净。
- **本机 OHOS CPython 的 posix_spawn 裸名缺陷**：`_IS_HARMONYOS` 补丁让无
  cwd 的裸名 subprocess 也走 posix_spawn 快路径，而 posix_spawn 不做 PATH
  搜索（按相对路径解析）→ `subprocess.run(["git",...])` 直接 ENOENT。带
  cwd= 参数的调用走 fork+execvp 慢路径不受影响。PR 创建路径的
  `_git_toplevel()`/preflight `changed_files()` 均中招，报 "PF0 环境闸:
  preflight 执行异常"。绕行：在项目根放符号链接 `git -> /data/service/hnp/bin/git`
  （posix_spawn 相对 cwd 解析到它），跑完 submit 删除。bash 不受影响
  （bash 自行做 PATH 搜索，不读 ./git）。
