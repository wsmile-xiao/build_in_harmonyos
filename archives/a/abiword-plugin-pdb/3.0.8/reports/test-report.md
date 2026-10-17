# Test Report — abiword-plugin-pdb 3.0.8

## 编译验证
- 编译器: clang 15 (aarch64-linux-ohos, OHOS SDK)
- 构建系统: Autotools (minimal configure.ac, 仅构建 pdb 插件)
- 编译状态: ✅ 成功
- 构建命令: autoreconf -fi && ./configure --prefix=$DEFAULT_PREFIX \
  --build=aarch64-unknown-linux-ohos --host=aarch64-unknown-linux-ohos \
  && make -j1 && make install DESTDIR=$TEST_PREFIX && make check -j1

## 平台补丁
| 补丁 | 说明 |
|------|------|
| 0001-Makefile.am.patch | minimal Makefile.am：仅构建 libabiword-plugin-pdb.so + 端到端测试 |
| 0002-configure.ac.patch | minimal configure.ac：仅构建 pdb 插件（移除 gtk3/libgsf/wv/libxslt 全链路依赖） |

## 平台修复
| 问题 | 修复方式 |
|------|----------|
| HMDFS 上 config.status umask 077 建 0700 临时目录不可写（E114） | conanfile.py build() 从生成的 configure 中移除 `umask 077` |
| make 并行 jobserver FIFO 被 SELinux 禁止（E074） | 所有 make 调用 `-j1` |
| toybox patch --dry-run 真实应用 new-file 补丁，污染 orig 目录（E258 草稿） | compat/tests 走 export_sources 传递，补丁只保留 2 个修改文件 |
| AbiWord 核心 / libgsf 未发布到 OHOS 制品仓 | 自研 compat/ shim（18 文件）提供 IE_Imp/IE_Exp/PD_Document/XAP_Module/UT_GrowBuf/GsfInput/GsfOutput API，插件 dependency-free |
| 导出方向（GsfOutput）API 缺失 | 新增 compat/gsf/gsf-output.h（可增长内存缓冲 + gsf_output_write/seek/tell）+ compat/ie_exp.h/ie_exp_Text.h（导出框架），glib.h 增加 gsf_off_t/GObject/g_ascii_strcasecmp（E321 草稿） |
| `xxx_UT_DEBUGMSG` / `UT_ASSERT` 未声明 | compat/ut_debugmsg.h 补齐上游永久禁用的 `xxx_UT_DEBUGMSG` 宏；compat/ie_imp.h include ut_assert.h（E321 草稿） |

## 上游测试说明
上游 AbiWord 3.0.8 的 pdb 插件**无任何官方测试**（plugins/pdb/ 仅含
ie_imp_PalmDoc/ie_exp_PalmDoc/ie_impexp_PalmDoc + Makefile.am，全树无 tests 目录）。
本包测试均为 OHOS 适配自研（见 test_package/MANIFEST.yml 的 upstream_official_tests: []
与 adapted_tests 声明）。

## 适配测试（自研，make check 执行）
- tests/test_pdb_plugin.cpp：端到端插件测试，dlopen 插件模块 → abi_plugin_register →
  sniffer 识别 TEXt/REAd PDB 头（PERFECT）→ getSuffixConfidence(.pdb) → constructImporter →
  importFile 解析合成 PalmDoc 文档 → 校验提取文本 → 导出生成 PDB（校验 DB 名/type/creator/
  numRecords/记录偏移/rec0 版本/压缩记录非空）→ 导出数据 round-trip 再导入校验。

### make check 实测输出（2026-08-13）
```
PASS: test_pdb_plugin
============================================================================
Testsuite summary for abiword-plugin-pdb 3.0.8
============================================================================
# TOTAL: 1
# PASS:  1
# SKIP:  0
# XFAIL: 0
# FAIL:  0
# XPASS: 0
# ERROR: 0
============================================================================
```
测试程序内部断言输出（直接运行 `PLUGIN_SO=... ./test_pdb_plugin`）：
```
[OK] PLUGIN_SO env set
[OK] dlopen(plugin .so)
[OK] dlsym(abi_plugin_register)
[OK] dlsym(abi_plugin_unregister)
[OK] abi_plugin_register() returns 1
[OK] XAP_ModuleInfo.name filled
[OK] XAP_ModuleInfo.desc filled
[OK] XAP_ModuleInfo.version == 3.0.8
[OK] importer sniffer 'AbiPalmDoc::PalmDoc' registered
[OK] exporter sniffer 'AbiPalmDoc::PalmDoc' registered
[OK] recognizeContents(PDB header) == PERFECT
[OK] recognizeContents(garbage) == ZILCH
[OK] recognizeContents(short buffer) == ZILCH
[OK] getSuffixConfidence() -> .pdb PERFECT
[OK] constructImporter() ok
[OK] GsfInput wrap ok
[OK] importFile(PDB sample) == UT_OK
[OK] document got Section + Block strux
[OK] document got multiple text spans
[OK] extracted text contains 'Hello PDB'
[OK] extracted text contains 'Second Line'
[OK] exporter recognizeSuffix('.pdb') == true
[OK] exporter recognizeSuffix('.txt') == false
[OK] constructExporter() ok
[OK] GsfOutput wrap ok
[OK] writeDocument() == UT_OK
[OK] exported PDB has at least a 78-byte header
[OK] exported type == 'TEXt'
[OK] exported creator == 'REAd'
[OK] exported DB name == 'sample.pdb'
[OK] exported numRecords == 2 (rec0 + 1 text)
[OK] record list[0].offset == 4096 (rec0)
[OK] record list[1].offset == 4112 (text)
[OK] rec0 version == 2 (compressed)
[OK] compressed text record is non-empty
[OK] round-trip importFile(exported PDB) == UT_OK
[OK] round-trip text contains 'Hello PDB'
[OK] round-trip text contains 'Second Line'
[OK] abi_plugin_unregister() returns 1
PASS: abiword-plugin-pdb end-to-end test succeeded (39/39 checks)
```

## 测试通过率统计
- make check: **1/1 测试通过（PASS=1, FAIL=0, ERROR=0）**
- test_pdb_plugin 内部断言: **39/39 通过（PASS: 39/39 checks）**
- test_package（conan 消费测试）: **PASS**（dlopen 插件模块 + register/unregister + 版本校验）

## Conan Verify (G0-G4)
| 门禁 | 结果 |
|------|------|
| G0 预构建风险评估 | ✅ PASS |
| G1 配方完整性 | ✅ PASS |
| G2 conan create | ✅ PASS（含 make check 1/1 + test_package PASS） |
| G3 系统同名库隔离 | ✅ PASS |
| G4 产物完整性 | ✅ PASS |

## W3 本地 CI 模拟
| 步骤 | 结果 |
|------|------|
| setup.sh | ✅ PASS |
| build_and_test.sh | ✅ PASS（G0/L0/L1/L2/L4/L5 全过） |

## 交付物
- 产物: libabiword-plugin-pdb.so → lib/abiword-3.0/plugins/
- 打包: packaging/abiword-plugin-pdb-3.0.8-ohos-aarch64.tar.gz
