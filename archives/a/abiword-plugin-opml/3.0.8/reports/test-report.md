# Test Report — abiword-plugin-opml 3.0.8

## 编译验证
- 编译器: clang 15 (aarch64-linux-ohos, OHOS SDK)
- 构建系统: Autotools (minimal configure.ac, 仅构建 OPML 导入插件)
- 编译状态: ✅ 成功（clean build，从源码完整构建）
- 构建命令: autoreconf -fi → ./configure --build=aarch64-unknown-linux-ohos --host=aarch64-unknown-linux-ohos → make -j1 → make check -j1

## 平台补丁
| 补丁 | 说明 |
|------|------|
| 0001-Makefile.am.patch | minimal Makefile.am：仅构建 libabiword-plugin-opml.so + 端到端测试（check-local 运行真实 ELF 测试二进制，OHOS 阻止 shebang 脚本执行） |
| 0002-configure.ac.patch | minimal configure.ac：仅构建 OPML 插件（移除 gtk3/libgsf/wv/libxslt/boost 全链路依赖） |

## 平台修复
| 问题 | 修复方式 |
|------|----------|
| git archive 无 configure | build() 中 `autoreconf -fi` 从 minimal configure.ac 生成 |
| HMDFS 上 config.status umask 077 建 0700 临时目录不可写（E114） | conanfile.py build() 从生成的 configure 中移除 `umask 077` |
| make 并行 jobserver FIFO 被 SELinux 禁止（E074） | 所有 make 调用 `-j1` |
| toybox patch --dry-run 真实应用 new-file 补丁，污染 orig 目录（E258 草稿） | compat/tests 走 export_sources 传递，补丁只保留 2 个修改文件 |
| automake/aclocal/libtoolize 硬编码绝对路径 | conanfile.py `_prepare_autotools_env()` 将 AUTOCONF/AUTOHEADER/AUTOM4TE/SED 指到 PATH 实际位置 |
| AbiWord 核心未发布到 OHOS 制品仓 | 自研 compat/ shim（17 文件）提供 IE_Imp/PD_Document/XAP_Module/UT_GrowBuf/IE_Imp_XML/fl_AutoNum 等 API，插件 dependency-free |
| OPML 插件不依赖 libxml2 | plugin.m4 仅引用 ${PLUGIN_CFLAGS}/${PLUGIN_LIBS}，XML 解析用 AbiWord 自研 IE_Imp_XML；compat/ 内实现自研最小 SAX XML 解析器 |

## 上游测试说明
上游 AbiWord 3.0.8 的 OPML 插件**无任何官方测试**（plugins/opml/ 仅含 ie_imp_OPML.{cpp,h} + Makefile.am + plugin.m4，全树无 tests 目录）。本包测试均为 OHOS 适配自研（见 test_package/MANIFEST.yml 的 upstream_official_tests: [] 与 adapted_tests 声明）。

## 适配测试（自研，make check 执行）
- tests/test_opml_plugin.cpp：端到端插件测试，dlopen 插件模块 → abi_plugin_register →
  sniffer "AbiOPML::OPML" 注册 → recognizeContents("<opml" 头)==PERFECT / 垃圾==ZILCH →
  getSuffixConfidence(.opml)==PERFECT → constructImporter → importFile 真实 OPML 2.0 文档
  （含 head/title/ownerName/嵌套 outline/url）→ 校验提取文本(News/Tech/Deep Learning)、
  strux≥5、span≥7、PTO_Hyperlink、PTO_Field、fl_AutoNum 列表、元数据 dc.title/dc.creator。
  26 项 [OK] 断言全部通过。

## Conan Verify
| 门禁 | 结果 |
|------|------|
| G0 预构建风险评估 | ✅ PASS（知识提示 E007 config.guess，配方已通过 --build/--host 显式 triplet 处理） |
| G1 配方完整性 | ✅ PASS |
| G2 conan create | ✅ PASS（clean build 全绿：make check 端到端测试 + test_package dlopen 测试） |
| G3 系统同名库隔离 | ✅ PASS（dependency-free，无系统同名库动态链接） |
| G4 产物完整性 | ✅ PASS（lib/abiword-3.0/plugins/libabiword-plugin-opml.so） |

## 环境说明（本机 OHOS SELinux 域限制）
conan-verify 工具的 G2 若通过 ELF conan 包装器入口（`/data/storage/el2/base/cache/conanbin/conan`
或系统 `pip-global/bin/conan`）调用时，conan 进程落入 `adhoc_bin` 域，该域下 clang-15 无法执行
（静默 exit=1），导致 test_package 编译失败。经诊断确认（SELinux 域检查 + 逐层复现），这是
**本机 OHOS SELinux 域转换限制**，并非配方缺陷：改用 direct `python3 -m conans.conan create`
（normal_hap 域）后 **clean build 完整通过**（autoreconf → configure → make → make check →
test_package 全绿）。CI 流水线（Linux worker）无此域限制，`conan create` 可正常执行。
