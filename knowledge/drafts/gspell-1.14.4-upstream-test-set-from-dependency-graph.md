# 上游测试跑不完时，该跳过的是"用例"还是"能力"——gspell × enchant 的 8/23

> Draft: DRAFT-gspell-1.14.4-upstream-test-set-from-dependency-graph
> Stem: `gspell-1.14.4-upstream-test-set-from-dependency-graph` — pairs with the same-stem `.kv`

## 基本信息

- **ID**: DRAFT-gspell-1.14.4-upstream-test-set-from-dependency-graph
- **严重度**: 2
- **类别**: testing, upstream-tests, dependency-resolution, ohos-platform
- **触发工具**: conan|meson|gtk|enchant
- **阶段**: testing|configuration

## 症状

```text
test-checker:ERROR:../../tests/unit-tests/test-checker.c:73:test_checker_new:
  assertion failed: (lang != NULL)
GLib-ERROR **: 10:47:03.211: ../../../glib/gmem.c:120: failed to allocate ... aborted
```

gspell 的上游 unit-tests 共 **6 个二进制 / 23 个 `g_test_add_func` 用例**：

| 二进制 | 用例数 | 是否依赖词典 |
|--------|-------|-------------|
| test-checker | 3 | ✅ |
| test-entry | 7 | ✅ |
| test-inline-checker-text-buffer | 5 | ✅ |
| test-icu | 2 | ❌ |
| test-text-iter | 3 | ❌ |
| test-utils | 3 | ❌ |

依赖词典的那三个（共 15 例）在每个 case 开头都做：

```c
GspellLanguage *lang = gspell_language_lookup("en_US");
g_assert_true(lang != NULL);
```

于是它们不是"失败"，而是**在执行第一行断言时就 abort**——测试根本没跑到
被测逻辑。

## 根因分析

这不是 gspell 的问题，是**依赖包的能力缺口**。ohpcd 的
`enchant/2.8.2` 在 configure 阶段传了：

```text
--without-aspell --without-hspell --without-hunspell
--without-nuspell --without-voikko --without-zemberek
```

也就是说 enchant 编译时**关掉了全部拼写后端**。包内
`lib/enchant-2/` 下没有任何 `.so` provider，也没有任何词典数据，于是：

```text
enchant_broker_list_dicts()  → 空
gspell_language_lookup("en_US") → NULL
15 个用例在 g_assert_true(lang != NULL) 处 abort
```

这是**无词典环境下的确定结果**：换谁跑都一样，不是偶发，也不是本包缺陷。

两类错误反应：

- **把 abort 记成失败** → 看似诚实，实则把"依赖包的能力缺口"记成了
  "本包适配失败"，通过率被无端压到 34.8%。
- **硬编码"只跑 8 个用例"** → 一时干净，但 enchant 侧将来补齐 provider 后
  这 15 个用例不会自动纳入，配方与真实能力脱钩，知识腐化。

## 解决方案

**主方案**: `derive-executable-test-set-from-dependency-graph-and-count-cases`

### 1. 不 patch 上游测试

上游的断言是对的，错的是运行环境。用 `-Dtests=false` 或补丁改断言来
"提高通过率"，等于删除质量证据，且会让测试集与上游永久漂移。

### 2. 让配方在构建期**探测能力**，而不是猜

```python
def _enchant_provider_count(self):
    enchant = self.dependencies["enchant"]
    folder = os.path.join(enchant.package_folder, "lib", "enchant-2")
    if not os.path.isdir(folder):
        return 0
    return len([f for f in os.listdir(folder)
                if f.endswith(".so") and not os.path.islink(...)])
```

判据来自**依赖包的 package_folder 实测**（`lib/enchant-2/*.so` 的个数），
而不是写死的版本号或环境变量。enchant 侧补齐 provider 后，同一份配方自动
把剩下 15 个用例纳入执行。

### 3. 把"用例数"变成数据，别把两个决策揉进一个常量

```python
UPSTREAM_CASES_PER_BINARY = {
    "test-checker": 3, "test-entry": 7, "test-icu": 2,
    "test-inline-checker-text-buffer": 5,
    "test-text-iter": 3, "test-utils": 3,
}                                   # 合计 = 上游全集 23
DICTIONARY_DEPENDENT   = ("test-checker", "test-entry", "test-inline-checker-text-buffer")
ENVIRONMENT_INDEPENDENT = ("test-icu", "test-text-iter", "test-utils")

names = ENVIRONMENT_INDEPENDENT + (DICTIONARY_DEPENDENT if providers else ())
expected = sum(UPSTREAM_CASES_PER_BINARY[n] for n in names)
```

注意要避免 `expected = 8 if providers == 0 else 23` 这种写法——它把"跑哪几个
二进制"和"每个二进制几个用例"两份知识各硬编码了一次。

### 4. 按**用例数**计量，不按二进制数

GLib 的测试二进制接受 `--tap`，直接输出逐用例 TAP：

```text
1..2
ok 1 - icu/loc_getDisplayNameSimple
ok 2 - icu/get_language_name_from_code
```

比 `meson test` 的 `Ok: 3`（3 个**二进制**）粒度细得多，也正因如此，通过率
能写成分母=用例数的诚实比例。`tests/interactive-tests` 只 `executable()`、
没有 `test()`，不是上游测试目标，不应计入分母。

### 5. 把判定结果显式打出来

```text
HMBS_UPSTREAM_TEST_RESULT={"status":"passed","framework":"glib-gtest-tap",
  "discovered":23,"executed":8,"passed":8,"failed":0,"skipped":15,
  "enchant_providers":0,
  "skip_reason":"enchant/2.8.2 has no spell provider ...",
  "per_binary":{...}}
```

同时在 `test_package/MANIFEST.yml` 里把未执行的三条标 `excluded: true`
并写明技术原因。**不虚报分母，也不虚报分子**。

## 验证

```sh
conan create archives/g/gspell/1.14.4 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing -nr
# 期望：discovered=23 executed=8 passed=8 skipped=15 enchant_providers=0
# test_package：13/13 断言通过（含"无词典时 check_word 回落 TRUE / get_suggestions 返回 NULL"的上游降级语义）
```

## 决策层：headless 显示后端从依赖包拿

6 个上游二进制全部调用 `gtk_test_init()`，需要 GDK 后端；ohpcd 没有
X/Wayland。gtk 是 broadway-only 构建但**自带 `bin/broadwayd`**，于是：

```python
proc = subprocess.Popen([os.path.join(gtk_pkg, "bin", "broadwayd"), ":5"])
# 最多等 20×0.5s；提前退出则降级为无后端并给 warning
env.define("GDK_BACKEND", "broadway")
env.define("BROADWAY_DISPLAY", ":5")
```

先例：`archives/a/ayatana-ido/0.10.4-v2`、`archives/g/gtkspell3/3.0.10-r3`。

## 反例

| 反例 | 为什么不行 |
|------|-----------|
| 打补丁改上游断言 / `-Dtests=false` | 删除质量证据；enchant 补齐后测试集与上游永久漂移 |
| `expected = 8` 或 `expected = 23` 硬编码 | 决策与数据混在一起，依赖图变化时必然漏改一处 |

## 关联条目

- 与同批 `gspell-1.14.4-meson-icu-uc-pkgconfig-name-pin` 构成 gspell 适配的
  两条主线：那条讲依赖解析与链接，本条讲测试集边界与计量口径；
- 与规则口径相关：通过率低（<50%）时必须把比值拆成"执行集 / 未执行集"
  两个数并给出全集，本条正是它的可复用范式。
