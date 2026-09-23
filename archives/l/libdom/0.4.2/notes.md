# libdom 0.4.2 适配笔记

## 2026-09-03 更新：DOMTS 可运行子集实跑（Septest rule4 修正）

PR #7715 Septest 复核判 rule4 FAIL：body 把 test_package 的 17 断言当上游用例数
（严重少报），且把 libsvgtiny 2624/2624 回归套件计入本 PR「新增测试用例通过率」
（口径错位）。修正方案（本提交）：

1. **上游测试规模如实申报**：libdom-0.4.2-src.tar.gz 内 `test/testcases/tests/**/*.xml`
   共 **2190** 个 DOMTS 用例（level1 1044 / level2 94 / level3 1052；Septest 口径 ≈2207，
   差异为 alltests.xml href 计数），周边 154 `.kfail` + 25 `.notimpl` 标记。逐 suite
   列规模+运行状态写入 MANIFEST.yml / PR body。
2. **实际运行可运行子集**：DOMTS 生成管线并不依赖 libcheck/netsurf-buildsystem——
   `test/Makefile` 用 `perl transform.pl`(XML::Parser::PerlSAX) + `DOMTSHandler.pm` 把
   每个 .xml 用例转成 .c 片段，与 `test/testutils/*.{c,h}` 一起编进可执行文件。
   本机（Windows Git bash + WSL perl 5.34 + libxml-perl）离线执行 transform，把
   **level1/core 60 个用例**的 .c 片段 vendored 进 `test_package/upstream/test/domts/`
   （未修改），testutils 原样 vendored；test_package 每个片段一个可执行文件，运行期
   CWD=upstream/ 使片段的 `chdir("test/testcases/tests/level1/core/files")` 定位到
   vendored fixtures。bare 头 `<xmlparser.h>/<parser.h>/<errors.h>` 经 `upstream/shim/`
   转发到 conan 包安装的 `dom/bindings/{xml,hubbub}/*.h`。OHOS CI 实跑 60/60。
3. **本地 Linux 全量预检**：同款 standalone Makefile + 0002 补丁 + libxml2 binding 在
   WSL(Ubuntu 22.04) 构建 libparserutils/libwapcaplet/libhubbub/libdom 后，level1/core
   tarball 平铺 374 个 .xml 用例全部 transform+compile+run → **374/374 PASS**。
   证据：`wslwork/native_results.txt`（374 PASS，0 FAIL）。
4. **口径修正**：libsvgtiny 0.1.8 的 2624/2624 回归属下游消费验证，移入 PR「补充说明」，
   不再计入本 PR「新增测试用例通过率」。新增通过率只写 test_package 真实 API 断言
   (17/17) + vendored DOMTS 子集 (60/60)。

## 编译环境
- 构建系统: makefile（NetSurf NSSHARED → standalone Makefile 替换）
- 编译日期: 2026-08-26
- 编译器: clang 15.0.4 (aarch64-unknown-linux-ohos, OHOS SDK 26.0.0.18)
- 状态: built（conan-verify G1-G4 全过）

## 编译步骤

1. `source .build-context-libdom-0.4.2 && cd $BUILD_SRC_DIR`
2. 替换顶层 Makefile 为 standalone Makefile（原 Makefile include
   `$(NSSHARED)/makefiles/Makefile.tools`，本平台无 netsurf-buildsystem）
3. `make CC=clang AR=llvm-ar RANLIB=llvm-ranlib -j1` 生成 `libdom.a` + `libdom.pc`
   （src/core + src/events + src/html + src/utils + bindings/hubbub/parser.c
   + bindings/xml/libxml_xmlparser.c 全部编入 libdom.a）
4. `make install PREFIX=$DEFAULT_PREFIX DESTDIR=$TEST_PREFIX` 验证安装（staging）
5. `make test` 运行 custom_test.c 冒烟测试（17 断言全过；上游 DOMTS 2207 用例依赖 netsurf-buildsystem + perl XML 模块，本平台不可用）。**该步仅本地手工验证**——conan build() 不跑 make test（test/custom_test.c 未随配方发布、依赖库路径不在 conan 缓存），conan 内测试由 test_package/test.c 承担
6. `conan-init libdom 0.4.2` 生成配方并手工修正（autotools 模板 → make 模板）
7. `conan-verify libdom 0.4.2` — G1/G2/G3/G4 全部 PASS

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 原始 Makefile `include $(NSSHARED)/makefiles/Makefile.tools` 找不到 | NetSurf 组件库使用自有 NSSHARED 构建系统，本平台无 netsurf-buildsystem | 替换为 standalone Makefile（libparserutils/libwapcaplet/libhubbub 同款方案），保留原编译标志，去除 -Werror 兼容 clang 15 |
| 2 | bindings 无 Makefile 时无法编入 libdom.a | 上游由 NSBUILD Makefile.subdir 递归；standalone 需显式列出 | Makefile 显式列出 bindings/hubbub/parser.c 与 bindings/xml/libxml_xmlparser.c |
| 3 | expat 不可用（Makefile.config 默认 WITH_EXPAT_BINDING=yes） | 本平台无 expat | 改用 WITH_LIBXML_BINDING=yes（libxml2 2.15.3.1 已适配），libsvgtiny 所需的 dom_xml_parser_* API 由 libxml_xmlparser.c 提供 |
| 4 | `<dom/bindings/xml/xmlparser.h>` 在测试中无法解析 | bindings/ 目录不在 include 路径下 | 测试目录下建 symlink `include/dom/bindings/{xml,hubbub}` → `../../../bindings/{xml,hubbub}`；install 时显式复制真实头文件（不复制 symlink） |
| 5 | 测试链接后 `xmlCreatePushParserCtxt: symbol not found` | 运行时找不到 libxml2.so.16 | 测试执行加 `LD_LIBRARY_PATH=$(SDK_LLVM_LIB):$(PREFIX)/lib` |
| 6 | `dom_node_append_child(elem, text, NULL)` 段错误 | libdom 的 append_child 无条件解引用 result 指针，不支持 NULL | 测试/下游必须传非 NULL result 指针 |
| 7 | conan create 需依赖可解析 | libwapcaplet/libhubbub 仅以 @ohpcd/stable 在缓存 | `conan export` 三个依赖为 plain ref；libdom 源码 tarball 预置到 core.sources:download_cache（禁网） |
| 8 | libsvgtiny 0.1.8 上游 AFL 套件 233 个含 DOCTYPE 内部实体的 SVG 崩溃（SIGSEGV） | libxml2 展开内部实体（`<!ENTITY ... "0<rect .../>0<g>...</g>0">`）时合成 startElementNs SAX 回调，父节点位于瞬态实体树（`_private == NULL`，未链接到 DOM），`xml_parser_start_element_ns` 把 `parent->_private`（NULL）传给 `xml_parser_add_node` → `dom_node_append_child(NULL, ...)` 崩溃（node.h 附近） | 0002 补丁：`xml_parser_start_element_ns` 在镜像前守卫 `parent->_private == NULL` 直接 return（跳过实体展开产生的伪节点镜像）；endElementNs 已有上游同款守卫（532 行）。修复后 2624 用例全过、崩溃清零 |

## 源码修改

| 文件 | 原因 | 方式 | 补丁状态 |
|------|------|------|----------|
| Makefile | NetSurf 构建系统不可用 | 完全替换为独立 Makefile | patches/0001-Makefile.patch |
| bindings/xml/libxml_xmlparser.c | libxml2 展开 DOCTYPE 内部实体时 startElementNs 收到无 DOM 链接的父节点，`parent->_private == NULL` 传 NULL 进 `dom_node_append_child` 崩溃（libsvgtiny 0.1.8 上游 233 个 AFL SVG 崩溃） | 在 `xml_parser_start_element_ns` 镜像前守卫 `parent->_private == NULL` 则跳过（endElementNs 的上游守卫 532 行保留） | patches/0002-libxml-xmlparser-guard.patch |

## 上游缺陷修复（2026-08-26 固化 0002 补丁）

**缺陷**：libdom 0.4.2 的 XML binding（bindings/xml/libxml_xmlparser.c）在 libxml2 解析含
DOCTYPE 内部实体子集的 SVG 时，libxml2 展开实体内容触发 `startElementNs` 回调，此时父节点
位于瞬态实体树（`_private == NULL`，从未链接到 DOM 节点），`xml_parser_add_text_node` /
`xml_parser_add_element_node` 收到 NULL 父节点 → `dom_node_append_child(NULL, ...)` 崩溃
（node.h:372 附近）。纯 libxml2 SAX 不崩（无 DOM 镜像逻辑）。

**修复**：0002 补丁在 `xml_parser_start_element_ns` 中，`parent == NULL → myDoc` 替换之后、
镜像子节点之前，守卫 `parent->_private == NULL` 时记录警告并 return，跳过对实体展开产生的
伪节点的 DOM 镜像。endElementNs 的上游守卫（`node->_private == NULL`，532 行）保持原样，
与 startElementNs 新守卫配合完整覆盖 open/close 两条回调路径。

**回归验证**（libsvgtiny 0.1.8 上游 test/runtest.sh 全量 2624 用例）：
- 修复前：`Exit code:139`（SIGSEGV）× 233（test/ns-afl-svg/ 内 233 个含实体的 AFL SVG）
- 修复后：`Tests:2624 Pass:2624 Fail:0 Error:0`，崩溃清零、100% 通过
- 证据日志：`reports/regression-233-afl.log`（仅保留汇总行）；完整运行日志在
  libsvgtiny-0.1.8.work/test/test.log（2624 个 SVG 条目、0 个非零退出码）
- /usr/local/lib/libdom.a 已重装含修复（strings 含 "Parent node not linked; skipping"）

## 依赖版本

- libparserutils 0.2.5（已发布，本地 cache + conan 依赖）
- libwapcaplet 0.4.3.1（已发布，本地 cache + conan 依赖）
- libhubbub 0.3.8（已发布，本地 cache + conan 依赖）
- libxml2 2.15.3.1（已发布，本地 cache + conan 依赖，XML binding 用）
- 编译工具: clang 15.0.4, llvm-ar, llvm-ranlib, GNU make 4.4.1, perl 5.42.2

## 验证结果

### 自定义 smoke test（make test，17 断言全过）

上游 DOM TS 测试依赖 netsurf-buildsystem（testrunner.pl）+ perl
XML::XPath/XML::Parser，本平台均不可用；改为自定义测试程序覆盖三块 API：

上游 DOMTS 套件共 2207 个 XML 用例（level1 1048 + level2 97 + level3 1062），
由 test/build-test.sh 逐个 transform→compile→run。本平台无 netsurf-buildsystem
包且 perl XML::XPath/XML::Parser::PerlSAX 模块未安装，2207 用例无法运行。
make test 运行 custom_test.c（17 断言冒烟测试），覆盖 core DOM + XML binding
(libxml2) + hubbub binding 三套路径。

```bash
$ make test
=== Running libdom smoke tests ===
PASS: core: create document
PASS: core: intern string 'p'
PASS: core: create element <p>
PASS: core: intern string 'hello'
PASS: core: create text node
PASS: core: append text child to element
PASS: core: get first child
PASS: core: first child is a text node
PASS: xml: create parser
PASS: xml: create document
PASS: xml: parse chunk
PASS: xml: parse completed
PASS: hubbub: create parser
PASS: hubbub: parser object
PASS: hubbub: document object
PASS: hubbub: parse chunk
PASS: hubbub: parse completed
checks=17 failures=0
ALL DOM SMOKE TESTS PASSED
# make test exit=0，17 断言 PASS，0 FAIL
```

### 下游验证（模拟 libsvgtiny 用法）

安装后以 `<dom/bindings/xml/xmlparser.h>` 解析 SVG 风格 XML 片段成功：

```bash
$ consumer OK (SVG XML parsed via installed libdom)
```

### conan create + test_package

```bash
$ ohc-run.py conan-verify libdom 0.4.2
G1: PASS  G2: PASS (conan create)  G3: PASS  G4: PASS
1/1 Test #1: test_libdom ..... Passed
（test.c 调用 dom_implementation_create_document / dom_document_create_element /
 dom_node_append_child / dom_xml_parser_* / dom_hubbub_parser_* API）
```

## 交付物

| 文件 | 说明 |
|------|------|
| libdom.a | 静态库 (633 KB, ar archive, ELF64 aarch64，含 hubbub + libxml bindings) |
| libdom.pc | pkg-config 文件 (version 0.4.2, Requires.private: libparserutils libwapcaplet libhubbub libxml-2.0) |
| include/dom/** | 公开头文件（dom.h + core/events/html）+ bindings/hubbub/{errors,parser}.h + bindings/xml/{xmlerror,xmlparser}.h |

## 注意事项

- NetSurf 组件库（libparserutils/libwapcaplet/libhubbub/libdom）均需替换为 standalone Makefile
- 静态库无需 ELF 签名与 RPATH 处理（E018）；libxml2 为动态依赖，测试运行时需 LD_LIBRARY_PATH
- 本包依赖 libparserutils/libwapcaplet/libhubbub/libxml2，conanfile `requirements()` 全部声明，
  `package_info()` 用 `cpp_info.requires` 传递链接依赖，test_package 链接时自动带上
- conandata.yml URL 为官方源，sha256 与 tarball 一致（R39）
- libdom 的 dom_node_append_child 等 API 要求 result 参数非 NULL（与 W3C DOM 规范一致）
- conan 构建时依赖源码需在 conan 下载缓存（已预置，禁网约束下避免再次网络下载）

---

**编译结束**: 2026-08-26
**最终状态**: built（conan-verify G1-G4 全过，含 0002 补丁；libsvgtiny 0.1.8 上游 2624 用例回归通过、233 AFL 崩溃清零，可走 finish/submit 提 PR）
