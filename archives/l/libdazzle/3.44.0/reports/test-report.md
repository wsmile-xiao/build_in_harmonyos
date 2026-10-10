# libdazzle 3.44.0 功能测试报告

**日期**: 2026-09-29
**平台**: HarmonyOS PC (OHOS, aarch64)
**构建方式**: Conan 2.29.1 (OHOS adapted) + meson 1.11.0
**Profile**: ohos-aarch64 (os=OHOS, os.version=6.0, arch=armv8, compiler=clang 15)
**依赖**: glib/2.84.0.1, gtk/3.24.43（及图内 20 个传递依赖）
**补丁**: 0 个（全部适配在 conanfile.py 的 generate/build/package 阶段完成）

## 测试摘要

### 一、上游测试套件（tests/meson.build 注册 29 项，build() 内真实执行）

执行方式：broadwayd（gtk 包自带，GDK_BACKEND=broadway）提供无头显示，GTest 环境
变量（G_TEST_SRCDIR/G_TEST_BUILDDIR/GSETTINGS_BACKEND=memory/NO_AT_BRIDGE），
每个二进制执行前 binary-sign-tool 自签。结果文件：`upstream-test-results.txt`。

**通过**: 28/29 | **失败**: 1/29（平台固有不兼容，非配方缺陷）

| # | 测试 | 结果 |
|---|------|------|
| 1 | test-application | ✅ PASS |
| 2 | test-menu-manager2 | ✅ PASS |
| 3 | test-state-machine | ✅ PASS |
| 4 | test-binding-group | ✅ PASS |
| 5 | test-signal-group | ✅ PASS（上游 bug：注册运行的是 test-binding-group 二进制） |
| 6 | test-task-cache | ✅ PASS |
| 7 | test-heap | ✅ PASS |
| 8 | test-suggestion-buffer | ✅ PASS |
| 9 | test-fuzzy-index | ✅ PASS |
| 10 | test-shortcut-chord | ✅ PASS |
| 11 | test-shortcut-overlays | ✅ PASS |
| 12 | test-shortcut-theme | ✅ PASS |
| 13 | test-trie | ✅ PASS |
| 14 | test-levenshtein | ✅ PASS |
| 15 | test-int-pair | ✅ PASS |
| 16 | test-ring | ✅ PASS |
| 17 | test-list-store | ✅ PASS |
| 18 | test-directory-reaper | ❌ FAIL(-5) |
| 19 | test-list-store-adapter | ✅ PASS |
| 20 | test-util | ✅ PASS |
| 21 | test-pattern-spec | ✅ PASS |
| 22 | test-recursive-monitor | ✅ PASS |
| 23 | test-file-transfer | ✅ PASS |
| 24 | test-cancellable | ✅ PASS |
| 25 | test-graph-model | ✅ PASS |
| 26 | test-read-only-list-model | ✅ PASS |
| 27 | test-model-filter | ✅ PASS |
| 28 | test-fuzzy-highlight | ✅ PASS |
| 29 | test-mutable-scoring | ✅ PASS |

test-directory-reaper 失败根因（确定性复现，非抖动）：

```
not ok /Dazzle/DirectoryReaper/basic - FATAL-ERROR: Failed to create symlink
```

夹具在 $TMPDIR 创建 symlink，而本宿主 HMDFS 文件系统不支持 symlink
（踩坑清单 #29），该测试在本环境不可执行。

### 二、消费者端到端测试（test_package/test.c，16/16 断言 PASS）

真实消费 libdazzle-1.0.so 公开 API，覆盖「include 头 → GObject 类型系统 →
库符号 → 行为正确性」链路；依赖库经构建目录镜像实体化直连，运行前自签：

```
PASS: dzl_pattern_spec_get_type registers a GType
PASS: DzlPatternSpec is a boxed GType
PASS: dzl_pattern_spec_new returns a spec
PASS: dzl_pattern_spec_get_text round-trips the keyword
PASS: dzl_pattern_spec_match hits 'dzl-pattern-spec.c'
PASS: dzl_pattern_spec_match hits multi-token path with both words
PASS: dzl_pattern_spec_match rejects haystack missing the 'dzl' word
PASS: dzl_pattern_spec_match rejects unrelated 'gtk-widget.c'
PASS: single-word spec hits token prefix 'pattern'
PASS: single-word spec rejects haystack without matching token
PASS: dzl_pattern_spec_ref returns same instance
PASS: ref/unref lifecycle completes without crash
PASS: dzl_levenshtein identical strings == 0
PASS: dzl_levenshtein one substitution == 1
PASS: dzl_levenshtein kitten/sitting == 3
PASS: dzl_levenshtein empty haystack == needle length
RESULT: PASS (16/16 assertions)
```

## 验证命令

```bash
conan create archives/l/libdazzle/3.44.0 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing --user=ohpcd --channel=stable
# conan-verify: G0/G1/G2/G3/G4/L2/L4/L5 全部 PASS
```

## 结论

- 上游套件 28/29 真实通过，唯一失败为 HMDFS 平台限制（无 symlink），与配方无关
- 消费者端到端 16/16 断言通过
- 库产物 libdazzle-1.0.so（1.1 MB）+ 头文件 + pkg-config 元数据打包正常
