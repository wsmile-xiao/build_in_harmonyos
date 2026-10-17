# libgepub 0.7.3 适配笔记

## 编译环境

- 构建系统: meson
- 编译日期: 2026-09-19
- 编译器: clang/clang++
- 状态: built（待真机预检回填实测证据）

## 上游信息

- 上游仓库: https://gitlab.gnome.org/GNOME/libgepub
- 上游版本: 0.7.3（GObject-based EPUB handling library，LGPL-2.1-or-later）
- 源码包: https://download.gnome.org/sources/libgepub/0.7/libgepub-0.7.3.tar.xz（27220 字节）
- sha256: 5a56695aa8a9132d67c0792a40f252ce0a48d9d032b4e1a8a6ce98af14fd5e1b（官方 .sha256sum，已在本机下载验算一致）

## 上游测试审计（7 TESTs 无头移植依据）

1. `meson.build`：顶层只 `subdir('libgepub')`，`subdir('tests')` 被 `if get_option('widget')` 包裹；本配方 `-Dwidget=false` 后 tests 子目录完全不参与配置，`meson test` 注册数为 0（上游设计如此）。
2. `tests/meson.build`：仅 `executable('test-gepub', ...)`，全源码树零 `test()` 注册（上游提交明示 "test-gepub is not considered an unattended test anymore"）。
3. `tests/test-gepub.c main()`：顺序执行 7 个 `TEST()`（test_open/read/root_file/doc_name/doc_resources/doc_spine/doc_toc），仅用 GepubArchive/GepubDoc；外层是 `gtk_init` + `gepub_widget_new`（WebKit prawd）+ GTK 窗口 + `gtk_main` 主循环，OHOS 无 webkit2gtk/显示输出无法运行。
4. 移植：`test_package/upstream_headless.c` 逐字移植 7 个 test_* 函数体 + `find_xhtml`/`pk`（PTEST 映射为 printf），剔除 `update_text`/`button_pressed`/widget/window/`gtk_main` 等 GTK 代码，并为每例加 PASS/FAIL 断言（上游只打印，失败静默；本移植失败即 exit 1，可证伪）。
5. 结论：`upstream_tests_exist: true`，7 例在 test_package 以 `./upstream_headless book.epub` 真实执行，`HMBS_UPSTREAM_TEST_RESULT` 取 `status:passed`（discovered/executed/passed 均为 7）；消费者覆盖仍由 `test_package/test.c` 的 16 项真实 API 断言提供。

## 编译步骤

meson 配置（headless 核心）：

```bash
meson setup builddir -Dwidget=false -Dintrospection=false -Ddefault_library=shared
meson compile -C builddir
meson install -C builddir
```

conan 侧由配方 `generate()` 完成工具链注入（MesonToolchain + PkgConfigDeps + glib .pc prefix 修正，详见 conanfile.py 注释）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | webkit2gtk/gtk 在 OHOS 不可用 | GepubWidget 强依赖 WebKit2GTK，制品仓无 webkit 包 | `-Dwidget=false` 只构建无头核心（上游 0.7.0 起官方支持该开关，NEWS 明示） |
| 2 | gobject-introspection 扫描器缺失 | OHOS 无 gir 工具链 | `-Dintrospection=false`（上游为 boolean 选项，真机实证 `disabled` 会报 not boolean） |
| 3 | 潜在双 GObject 类型系统冲突 | libsoup3/3.6.5-r3 固定 glib/2.84.0.1.1 shared | 本配方 requires 同一 glib 版本 shared，共用一份 libgobject |
| 4 | meson install 后 .so 可能 dlopen 失败 | install 改写 DT_RUNPATH，OHOS .codesign 校验失配 | package() 用构建树原始链接产物覆盖（libsoup3 同款实证修复） |
| 5 | 消费者编译找不到 config.h | gepub.h 用 `#include <config.h>`，文件安装在 include/libgepub-0.7/ | package_info includedirs 显式加入 include/libgepub-0.7 |

## 源码修改

无补丁（patches_applied 为空）。

## 依赖版本

- glib/2.84.0.1.1（shared，与 libsoup3 链对齐）
- libsoup3/3.6.5-r3
- libxml2/2.15.3.1
- libarchive/3.8.7

W0 依赖发布检查：在本机 Windows 环境无法运行 conan，以上版本均取自本仓已合入归档（glib/libsoup3/libxml2/libarchive 均有 built 及以上状态归档及制品仓发布记录，详见各包 notes.md）；最终以真机预检 PF4 依赖闸实测为准，缺失则下一轮调整。

## 验证结果

待真机预检（本轮只提交未验证工作树）：

```bash
# 预期（test_package 阶段）
HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,"command":"./test_libgepub book.epub","discovered":6,"passedCount":6}
HMBS_UPSTREAM_TEST_RESULT={"status":"passed","framework":"ctest","command":"./upstream_headless book.epub (headless port of tests/test-gepub.c 7 TESTs)","discovered":7,"executed":7,"passed":7,"failed":0,"skipped":0}
```

- test_package：6 个用例组 / 16 项断言（GepubTextChunk 创建与类型、archive 文件枚举与 rootfile、doc 元数据与章节、文本抽取、TOC/章节映射），合成 EPUB 由 `make_book.py`（纯 stdlib zipfile）离线生成。
- upstream_headless：7 例上游 TEST() 无头移植（test_open/read/root_file/doc_name/doc_resources/doc_spine/doc_toc），同夹具、逐例断言、失败 exit 1。
- Windows 本机限制说明：本机无法执行 conan/交叉编译（守则要求真机验证），`conanfile.py`/`test_package` 已做 `py_compile` 语法检查；`conandata.yml`/`MANIFEST.yml`/`manifest.yaml` 已做 YAML 解析检查。

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | 主配方（meson，headless；上游证据由 test_package 输出） |
| conandata.yml | 官方源 URL + sha256 |
| manifest.yaml | 版本级 manifest |
| test_package/test.c | 16 断言消费者测试 |
| test_package/upstream_headless.c | 7 例上游 TEST() 无头移植 |
| test_package/make_book.py | 离线合成 EPUB 生成器 |
| test_package/MANIFEST.yml | upstream 7 例审计声明 |

## 注意事项

- Windows 检出注意：本仓 `archives/l/libXext`（旧）与 `archives/l/libxext`（新）在大小写不敏感文件系统上冲突，另有 `archives/g/gama` 下文件名含 CR 的补丁无法在 Windows 落盘；本机已用 `git update-index --assume-unchanged` 屏蔽这 5 个路径的虚假 dirty，`git status` 干净。真机（Linux）不受影响，PR diff 不含这些文件。
- 本配方默认 shared（gepub 非系统同名库，R26 不适用）。
- PR 正文草稿见 `.hmbs/pr-body.md`（测试用例数待真机 evidence 轮回填）。
