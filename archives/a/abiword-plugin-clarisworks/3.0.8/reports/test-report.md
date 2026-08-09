# Test Report — abiword-plugin-clarisworks 3.0.8

## 编译验证
- 编译器: clang 15 (aarch64-linux-ohos, OHOS SDK)
- 构建系统: Autotools (minimal configure.ac, 仅构建 clarisworks 插件)
- 编译状态: ✅ 成功
- 构建命令: autoreconf -fi && ./configure --prefix=$DEFAULT_PREFIX && make -j1 && make check -j1

## 平台补丁
| 补丁 | 说明 |
|------|------|
| 0001-Makefile.am.patch | minimal Makefile.am：仅构建 libabiword-plugin-clarisworks.so + 端到端测试 |
| 0002-configure.ac.patch | minimal configure.ac：仅构建 clarisworks 插件（移除 gtk3/libgsf/wv/libxslt 全链路依赖） |

## 平台修复
| 问题 | 修复方式 |
|------|----------|
| HMDFS 上 config.status umask 077 建 0700 临时目录不可写（E114） | conanfile.py build() 从生成的 configure 中移除 `umask 077` |
| make 并行 jobserver FIFO 被 SELinux 禁止（E074） | 所有 make 调用 `-j1` |
| toybox patch --dry-run 真实应用 new-file 补丁，污染 orig 目录（E258 草稿） | compat/tests 走 export_sources 传递，补丁只保留 2 个修改文件 |
| AbiWord 核心 / libgsf 未发布到 OHOS 制品仓 | 自研 compat/ shim（13 文件）提供 IE_Imp/PD_Document/XAP_Module/UT_GrowBuf/GsfInput API，插件 dependency-free |

## 上游测试说明
上游 AbiWord 3.0.8 的 clarisworks 插件**无任何官方测试**（plugins/clarisworks/ 仅含
ie_imp_ClarisWorks.{cpp,h} + Makefile.am，全树无 tests 目录）。本包测试均为 OHOS 适配自研
（见 test_package/MANIFEST.yml 的 upstream_official_tests: [] 与 adapted_tests 声明）。

## 适配测试（自研，make check 执行）
- tests/test_clarisworks_plugin.cpp：端到端插件测试，dlopen 插件模块 → abi_plugin_register →
  sniffer 识别 CWK5 头（PERFECT）→ getSuffixConfidence(.cwk) → constructImporter → importFile
  解析合成 CWK 文档 → 校验提取文本（20 项 CHECK 断言，全部通过）

## Conan Verify (G0-G4)
| 门禁 | 结果 |
|------|------|
| G0 预构建风险评估 | ✅ PASS |
| G1 配方完整性 | ✅ PASS |
| G2 conan create | ✅ PASS |
| G3 系统同名库隔离 | ✅ PASS |
| G4 产物完整性 | ✅ PASS |

## W3 本地 CI 模拟
| 步骤 | 结果 |
|------|------|
| setup.sh | ✅ PASS |
| build_and_test.sh | ✅ PASS（L0/L1/L4/L5 全过，L1e 破坏性负向测试确认 R34 实质依赖） |

## test_package (R34)
- run_test.cpp：消费者 dlopen 测试，驱动 abi_plugin_supports_version/register/unregister，
  校验 XAP_ModuleInfo 各字段与版本号，PASS

## 交付物
- 产物: libabiword-plugin-clarisworks.so → lib/abiword-3.0/plugins/
- 打包: packaging/abiword-plugin-clarisworks-3.0.8-ohos-aarch64.tar.gz
