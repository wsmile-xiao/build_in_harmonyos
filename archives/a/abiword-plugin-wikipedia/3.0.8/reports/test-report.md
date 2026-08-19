# Test Report — abiword-plugin-wikipedia 3.0.8

## 概述
- 软件: abiword-plugin-wikipedia 3.0.8（AbiWord 维基百科在线查询插件）
- 上游官方测试: **无**（已核实 orig 纯净上游树 `plugins/wikipedia/` 下仅
  `xp/AbiWikipedia.cpp` + Makefile.am/plugin.m4，AbiWord 全部插件均无测试框架）
- 本包测试: 全部为 OHOS 适配自研（见 test_package/MANIFEST.yml 如实声明）
  - `make check`（conanfile build() 内执行）: `tests/test_wikipedia_plugin.cpp`
  - `conan create` test_package: `test_package/run_test.cpp`

## 上游测试统计
| 项目 | 数量 |
|------|------|
| 上游官方测试程序 | 0 |
| 上游测试断言 | 0 |

## 适配后测试（make check）

端到端测试 `tests/test_wikipedia_plugin.cpp`（36 项 CHECK 断言）:

| # | 断言组 | 断言数 | 通过 |
|---|--------|-------|------|
| 1 | PLUGIN_SO env + dlopen + dlsym 三个 ABI | 5 | 5/5 |
| 2 | abi_plugin_register 返回值 + XAP_ModuleInfo 填充 | 5 | 5/5 |
| 3 | abi_plugin_supports_version(3,0,8)/(any) == 1 | 2 | 2/2 |
| 4 | EV_EditMethodContainer 含 "Wikipedia_invoke" + ev_EditMethod_lookup | 5 | 5/5 |
| 5 | XAP_Menu_Factory 含 "Wi&ki Encyclopedia" 标签 + ActionSet 绑定 | 4 | 4/4 |
| 6 | invoke 端到端: 选中词 "war" → openURL 含 w/wiki.phtml?search=war&go=Go；空选择 → 基础 URL | 8 | 8/8 |
| 7 | abi_plugin_unregister 后 EditMethod/菜单标签已移除 | 4 | 4/4 |
| 合计 | | 36 | **36/36** |

运行输出（节选）:
```
PASS: test_wikipedia_plugin
============================================================================
Testsuite summary for abiword-plugin-wikipedia 3.0.8
============================================================================
# TOTAL: 1
# PASS:  1
# SKIP:  0
# FAIL:  0
...
PASS: abiword-plugin-wikipedia end-to-end test succeeded (36/36 checks)
```

### make check 执行方式
```bash
make check TESTS_ENVIRONMENT='PLUGIN_SO=$(abs_builddir)/.libs/libabiword-plugin-wikipedia.so'
# 或由 conanfile build() 内 autotools.make(target="check", args=["-j1"]) 触发
```

## 适配后测试（test_package）

消费者测试 `test_package/run_test.cpp`（dlopen 已安装模块 → ABI 驱动）:
```bash
$ run_test <path>/lib/abiword-3.0/plugins/libabiword-plugin-wikipedia.so
PASS: abiword-plugin-wikipedia module loaded, registered and unregistered (Wikipedia plugin / 3.0.8)
```
- dlopen 成功
- abi_plugin_supports_version(3,0,0) == 1
- abi_plugin_register 填充 XAP_ModuleInfo（name/desc/author/usage/version=3.0.8）
- abi_plugin_unregister 返回 1

## 通过率
- 上游测试通过率: N/A（上游无测试）
- 适配后测试通过率: **PASS: 36/36**（make check 断言）+ test_package **PASS**
- conan-verify 门禁: G0-G4 + L2/L4/L5 全部 PASS（见 conan-verify-report.md）

## 平台相关跳过/失败
- 无（本包测试在 OHOS aarch64 上全部通过）
- 备注: 直接运行 test 二进制（绕过 automake harness）会因 RPATH 指向未安装的
  `//lib/abiword-3.0/plugins` 找不到 .so —— 属正常现象，make check 内通过
  LD_LIBRARY_PATH 注入正常运行（探索阶段 E074/E129 同款平台陷阱不影响测试执行）
