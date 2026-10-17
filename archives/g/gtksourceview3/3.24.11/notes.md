# gtksourceview3 3.24.11 适配笔记

## 编译环境
- 构建系统: autotools（tarball 自带 configure，无需 autoreconf）
- 编译日期: 2026-09-03
- 编译器: clang 15.0.4 (aarch64-unknown-linux-ohos, musl)
- 依赖: gtk/3.24.43（broadway 后端）、libxml2/2.15.3、pango/1.50.14.1（传递）
- 状态: published

## 编译步骤

1. `conan create . -pr:h aarch64-ohos -pr:b aarch64-ohos --build=missing`
2. recipe 内部流程：
   - source(): 官方 GNOME tarball 下载 + sha256 校验
   - export_sources(): test-data/mime（freedesktop mime 数据集）
   - build(): 运行时修复 config.guess（E160）与 configure tmpdir 模板（E011）
     → PkgConfigDeps 发现 gtk+-3.0/libxml-2.0 → configure
     → make -j1（E074：HMDFS jobserver fifo）
     → 上游 testsuite 全量运行（22 程序）
   - package(): make install + LGPL license + OHOS ELF 签名
   - test_package(): cmake + pkg-config 链接真实消费测试

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | cannot guess build type | config.guess 2018 不识别 HarmonyOS（E160） | 运行时 sed：`HarmonyOS\|HongMeng) UNAME_SYSTEM=Linux; LIBC=musl;;` |
| 2 | C compiler cannot create executables | SDK lld NEEDED libxml2.so.16 缺失 | LD_LIBRARY_PATH 注入 `/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/lib`（abx 同款） |
| 3 | config.status confXXXXXX/subs1.awk Permission denied | umask 077 mktemp 在 HMDFS 上目录不可写（E011） | 替换 configure 内嵌模板的 umask 建目录（babeltrace DRAFT-6048 同款） |
| 4 | glib-compile-resources: Operation not permitted / libffi 符号缺失 | conan 缓存 ELF 工具执行受限；系统 /data/service/hnp/bin 旧版工具坏 | 拷贝 glib 包工具到 build/conan-native-tools + binary-sign-tool 重签；make 命令行 `GLIB_COMPILE_RESOURCES=... GLIB_MKENUMS=...` 覆盖 configure 固化路径 |
| 5 | glib-mkenums: /usr/bin/perl bad interpreter | 系统 glib-mkenums 是 perl 脚本而 /usr/bin/perl 不存在 | conan glib 包的 glib-mkenums 是 python 脚本（#!/usr/bin/env python3），staged 覆盖 |
| 6 | 上游测试 cannot open display | OHOS 无 X11/Wayland；GTK3 broadway 客户端读 BROADWAY_DISPLAY 而非 DISPLAY | broadwayd 以 `:tcp41` 模式启动（TCP 127.0.0.1:9131），测试 env `GDK_BACKEND=broadway BROADWAY_DISPLAY=:tcp41` |
| 7 | HMDFS unix socket path connect ENOENT | HMDFS AF_UNIX bind 产生 abstract socket（@前缀），文件系统路径不存在 | 使用 broadwayd 的 `:tcpN` 模式（纯 TCP，绕开 unix socket 语义） |
| 8 | test-languagemanager guess-language: xslt 猜成 xml | OHOS 无 /usr/share/mime，g_content_type_is_a 无数据 | 配方自带 freedesktop mime 数据集（test-data/mime），XDG_DATA_DIRS 注入 |
| 9 | test-file-saver permissions: 384 == 432 断言失败 | HMDFS chmod(0600) 后 stat 返回 0660（组写位强制，E011/E046 同族平台语义） | 测试期 TMPDIR 重定向到 el2 分区 `/data/storage/el2/base/temp/gsv-testsuite-tmp`（实测 chmod 600 → 600） |
| 10 | test 二进制 Error 127: libc++_shared.so not found | harfbuzz（gtk 传递依赖）NEEDED libc++_shared.so，conan 依赖图不携带 | test() 里 LD_LIBRARY_PATH 加 /system/lib64（glade test 同款） |
| 11 | search occurrences 返回 -1 | gtk_source_search 异步搜索，需要主循环迭代 | 测试里 g_main_context_iteration 泵事件直到 settle |

## 源码修改

无 .patch 文件。两处运行时 sed 修复（manifest knowledge_gained 记录）：
- config.guess：HarmonyOS 识别（E160 标准做法，与 cgl/clp/coin-or 一致）
- configure：config.status tmpdir umask 剥离（E011，HMDFS SGID 语义）

## 依赖版本

- gtk/3.24.43（conan 包名 gtk，broadway 后端，shared）
- libxml2/2.15.3（shared）
- pango/1.50.14.1 → 经 gtk 传递（1.50.14.1.1 亦可，二进制等价）
- glib/2.84.0.1、cairo、gdk-pixbuf、atk、fribidi、libepoxy 等全部经 gtk 传递

## 验证结果

```text
上游 testsuite（testsuite/ 目录，22 个测试程序）:
  test-buffer: 6/6 ok
  test-buffer-input-stream: 6/6 ok
  test-buffer-output-stream: 9/9 ok
  test-completion-model: 8/8 ok
  test-completion-words: 1/1 ok
  test-encoding: 1/1 ok
  test-file-loader: 3/3 ok
  test-file-saver: 1/1 ok（含 subprocess 权限用例，TMPDIR 重定向 el2）
  test-iter: 13/13 ok
  test-language: 1/1 ok
  test-languagemanager: 3/3 ok（含 guess-language，mime 数据注入）
  test-mark: 4/4 ok
  test-printcompositor: 2/2 ok
  test-regex: 1/1 ok
  test-region: 4/4 ok
  test-search-context: 18/18 ok
  test-space-drawer: 1/1 ok
  test-stylescheme: 2/2 ok
  test-styleschememanager: 2/2 ok
  test-undo-manager: 12/12 ok
  test-utils: 2/2 ok
  test-view: 2/2 ok
  ────────────────────────────
  合计: 102/102 用例通过（100%），conan create 全绿

tests/ 目录（交互式 demo，非 make check 目标）:
  test-widget/test-completion/test-search/test-space-drawing/
  test-undo-manager-performances/test-search-performances 为交互演示
  程序（gtk_main 循环，需人工 UI 操作），python 测试为演示脚本，
  不适用 CI 自动化——如实记录，不计入通过率

conan create 最终输出:
  gtksourceview3/3.24.11 package 691b6eb98c38949ed033dc01d02677d7faed470c
  (os=OHOS, arch=armv8, clang 15, Release, shared) — build + test_package 全过
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | autotools 配方（含上游测试全量运行） |
| conandata.yml | GNOME 官方源 + sha256 |
| test_package/ | cmake 消费测试（GtkSourceBuffer/Search/StyleScheme 真实 API） |
| test-data/mime/ | freedesktop shared-mime-info 2.5.1 数据集（测试支撑，含 packages/freedesktop.org.xml） |
| manifest.yaml | 版本元数据 |
| notes.md | 本笔记 |

## 注意事项

- R40 深度适配说明：本库为 GTK 文本组件库，非图形渲染/系统底层类；
  编译期平台适配点集中在构建工具链与测试环境（见上表），库源码本身
  无需 OHOS 专属补丁（POSIX 兼容层足够）
- 上游测试全量在 conan build() 内运行（CI 可复现）：broadwayd :tcp41
  无头显示 + mime 数据 + el2 TMPDIR 三个环境要素已固化进配方
- GLib-DEBUG "pidfd signaled" 噪音输出为 musl glib 已知行为，无害
---

**编译结束**: 2026-09-03 22:06
**最终状态**: published
