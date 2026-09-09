# libmirage 1.0.0 适配笔记

## 编译环境
- 构建系统: autotools（发布 tarball 自带 configure；2006-07 版 config.guess/sub）
- 编译日期: 2026-09-04
- 编译器: clang 15.0.4（/data/service/hnp/bin），三元组 aarch64-unknown-linux-ohos
  （由补丁后的 config.guess 输出，configure 无 AC_CANONICAL_HOST，config.sub 不参与构建）
- 依赖: glib/2.88.0、libsndfile/1.2.2（传递 pcre2/10.45、zlib/1.3.1；glib 已 vendored
  libffi/gettext；libsndfile 关闭外部 codecs，自包含）
- 状态: built

## 编译步骤

conan create（ci/conan/build_and_test.sh 权威入口，显式 -pr:h/-pr:b=
ci/conan/profiles/ohos-aarch64）内自动完成：

1. `get()` 拉取 SourceForge 平铺目录归档并校验 sha256。
2. 应用补丁 0001-0003、0005（per-file difflib 生成，设备 /storage/Users/currentUser/tmp/builds
   的 .orig/.work 树 diff）。
3. configure：GLIB_*/GOBJECT_*/GMODULE_*/SNDFILE_* cache 变量（E236 la-free 目录）
   + `--disable-gtk-doc --disable-shared --enable-static`。
4. make -j1；install 后删除包内 `.la`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 2006 版 config.guess 无 HarmonyOS 分支 | E007 | 0001 补丁：主 case 插入 `*:HarmonyOS:*:*)` 分支。注意必须用 **echo+exit** 旧形式（libdaemon 0.14 先例）；现代 `GUESS=...` 形式在该年代脚本里不生效（脚本结尾不打印 GUESS，configure 拿到空三元组） |
| 2 | 2006 版 config.sub 不识别 linux-ohos | E007 白名单漏项 | 0002 补丁：KERNEL-OS 组合白名单 + OS 列表加 `-linux-ohos* | -ohos*`。本包 configure 无 AC_CANONICAL_HOST，config.sub 不参与构建（与 libdaemon 同） |
| 3 | configure mktemp/mkdir 私有目录自写被拒 | HMDFS umask 077 语义 | 0003 补丁：两处 umask 077→022（libcsv 3.0.3 / dbus-glib 0.114 先例） |
| 4 | 2006 版 config.guess 的 dummy.c 编译探针在 HMDFS 上 Permission denied | HMDFS 对 umask 077 私有目录内自写拒绝 | 探针失败非致命（LIBC=unknown 回退），HarmonyOS 分支直接 echo 不依赖 LIBC；与 libdaemon 处置一致，不改 config.guess tmpdir |
| 5 | 2006 版 config.guess 的 `__ANDROID__/LIBC=android` 锚点不存在 | 年代差异 | 不适用——该探针仅服务 Linux 分支的 LIBC 后缀，HarmonyOS 分支无需；perl 脚本 warn 属预期（score 1/5 中必需项 HarmonyOS 分支已插入） |
| 6 | `shared=True` 会吞静态 glib 形成双 GType 运行时 | glib OHOS 制品仅静态 | 配方默认 static；OHOS + shared 请求时显式 raise（dbus-glib 0.114 守卫） |
| 7 | image-ccd/cue/toc 解析器编译失败：生成 parser 以 2 参调用 `yylex(&yylval,&yylloc)`，而 `.y`/`.l` 约定 3 参（带 yyscanner） | bison 3.8.2 不再按 `%pure_parser` 生成可重入骨架（.l 为 `%option reentrant bison-bridge bison-locations`） | 0005 补丁：三处 `%pure_parser` → `%define api.pure true`，生成骨架按 3 参调用，与 lexer 一致 |

## 插件模块说明

上游 parsers/（image-b6t/ccd/cdi/cue/iso/mds/nrg/toc）与 fragments/（binary/null/sndfile）
为 `plugin_LTLIBRARIES`（`-module -avoid-version`）运行时模块。OHOS 上 glib 仅静态制品，
`--disable-shared` 下这些模块以静态档形态安装到 `lib/libmirage/*.a`；运行时 g_module
dlopen 加载在 OHOS 不可用（任何 .so 都会吞入私有 glib 副本）。本移植为编译/打包级，
镜像解析运行时功能在鸿蒙上不可达；核心库本体（libmirage.a）与其 GType 体系可完整链接。

## 依赖版本

glib/2.88.0、libsndfile/1.2.2、pcre2/10.45、zlib/1.3.1（均 ohpcd 制品仓已发布）

## 验证结果

```bash
# 权威入口（ci/conan/build_and_test.sh 同参数形态）单包验证：
conan create archives/l/libmirage/1.0.0 -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 --build="libmirage/*"            # exit=0
#   日志: 详见设备 tmp 探针日志（lm-create-5.log，run 临时产物，不入树、未抄录）
# test_package: pkg-config 静态链 test_mirage → "libmirage test_package: all checks passed"
#   （g_object_new(MIRAGE_TYPE_MIRAGE) 构造 + mirage_mirage_get_version() == "1.0.0"）
```

上游 1.0.0 无任何测试套件：tarball 无 test/ 目录；全部 Makefile.am（顶层/src/docs）
无 TESTS 变量、无自定义 check 目标 → 结论 NO_UPSTREAM_TESTS；上游零测试由真实
test_package 消费者测试覆盖，权威 CI L1 以 test_package executed 通过（非白名单路径），
未登记、未修改任何 ci 文件（上游测试 discovery 证据见 run 内报告 upstream-test-discovery.md）。

## 注意事项

- libmirage.pc 经 install 进入包内 `lib/pkgconfig/`，PkgConfigDeps 生成的 test_package
  .pc 与之同名（libmirage），消费者（cdemud）走 cache 变量路径不依赖 .pc。
- `include <linux/cdrom.h>`（mirage.h）：OHOS sysroot 内核头可用性在首次构建实测确认。
- 禁止提交：`.orig`/`.work` 树与 patches-* 临时目录留在 /storage/.../tmp/builds，不入仓。
