# lexd 1.3.5：依赖图里两份 ICU 导致头/库错配 + `libicuio` 不在 `cpp_info` 里

> Draft: DRAFT-LEXD-135-ICU-DUAL-VERSION-ABI-MISMATCH
> Stem: `DRAFT-lexd-1.3.5-icu-dual-version-abi-mismatch` — pairs with the same-stem `.kv`

## 基本信息

- **ID**: DRAFT-LEXD-135-ICU-DUAL-VERSION-ABI-MISMATCH
- **严重度**: 2
- **类别**: linking|dependency-graph|pkg-config|icu|abi-mismatch|conan
- **触发工具**: conan|clang|ld.lld|configure
- **阶段**: linking

## 错误特征

编译 100% 成功，`make` 在链接 `bin/lexd` 时成片报未定义符号：

```
ld.lld-15: error: undefined symbol: icu_77::UnicodeString::UnicodeString(char const*)
>>> referenced by lexdcompiler.cc
ld.lld-15: error: undefined symbol: u_vfprintf_77
>>> referenced by lexdcompiler.cc: LexdCompiler::die(char const*, ...)
ld.lld-15: error: too many errors emitted, stopping now (use --error-limit=0 ...)
```

注意符号里的 **`_77` 后缀**——这是本条目的核心指纹。

## 根因分析

Conan 制品仓里同时存在两个 ICU 配方，而 lexd 的依赖图把它们同时拉了进来：

| 来源 | 包 | 大版本 |
|------|----|--------|
| lexd 自己 `requires` | `icu/76.1` | 76 |
| lttoolbox/3.7.6 传递（`transitive_headers=True`） | `icu4c/77` | 77 |

于是一次构建里出现两份 ICU：

- **头文件**取自 transitive 的 `icu4c/77`（Conan 注入的 `includedirs` 在前），
  所以源码里的符号前缀是 `icu_77`；
- **链接**时 `-licuuc` 按 `LDFLAGS` 中 `-L` 的出现顺序，命中 `icu/76.1` 的
  package folder —— 那是 ICU 76 的归档，只导出 `icu_76::*`。

两套符号命名空间互不相交，于是每一个 `UnicodeString` 引用都变成未定义符号。
这不是「ICU 小版本不兼容」，而是**同一个库的两个来源**造成的头/库错配。

第二个独立坑：`icu4c/77` 的 `package_info` 只声明

```python
self.cpp_info.libs = ["icui18n", "icuuc", "icudata"]
self.cpp_info.system_libs = ["m", "pthread"]
```

**不含 `libicuio`**。而 lexd 的 `configure.ac` 硬要求
`PKG_CHECK_MODULES([ICU_IO], [icu-io])`，`u_vfprintf` / `u_fopen` / `u_fclose`
正住在 `libicuio.a`。照抄 `cpp_info` 拼 LIBS 会在修掉第一处后立刻撞上
`undefined symbol: u_vfprintf_77`。

## 复现与定位

```bash
# 1) 图里有几份 ICU？（期望只有 icu4c/77）
conan graph info <recipe> -pr:h=ohos-aarch64-wsl -pr:b=ohos-aarch64-wsl --format=json \
  | python3 -c "import json,sys;[print(n['ref']) for n in json.load(sys.stdin)['graph']['nodes'].values() if n.get('ref') and 'icu' in n['ref']]"

# 2) 头文件的大版本 vs 归档里的符号前缀（两者必须一致）
grep -o 'U_ICU_VERSION_MAJOR_NUM [0-9]*' <icu include>/unicode/uvernum.h
nm -g --defined-only <icu lib>/libicuuc.a 2>/dev/null | grep -o 'icu_[0-9]*' | sort -u | head -1

# 3) 上游到底要哪些 ICU 模块
grep -n 'PKG_CHECK_MODULES.*icu' <src>/configure.ac

# 4) 链接命令里 -L 的顺序 vs 头文件来源（看 -licuuc 前面第一个是哪个 ICU 目录）
grep -o '\-L[^ ]*icu[^ ]*' build.log | sort -u
```

## 解决方案

**① 图里只保留一份 ICU**——跟传递依赖选同款配方：

```python
# lttoolbox/3.7.6 requires icu4c/77，lexd 也必须 requires icu4c/77
self.requires("icu4c/77", transitive_headers=True)
```

若两个配方都非留不可，只能改上游去掉其中一个依赖；靠链接技巧
（`--start-group` / `--allow-shlib-undefined`）掩盖头/库错配只会把问题推到运行期。

**② 从 `cpp_info` 推导 LIBS 时补 `-licuio`**，并放在 trio 之前（静态归档按
左到右解析，`libicuio` 自身依赖 `icuuc/icui18n/icudata`）：

```python
libs = ["-L{}".format(d) for d in dep.cpp_info.libdirs]
if dep.ref.name == "icu4c":
    libs.append("-licuio")          # cpp_info 未建模，但 configure 要求 icu-io
libs += ["-l{}".format(l) for l in dep.cpp_info.libs]
libs += ["-l{}".format(l) for l in dep.cpp_info.system_libs]
# -> -licuio -licui18n -licuuc -licudata -lm -lpthread
```

**通用判据**：从 `cpp_info` 拼 LIBS 之前，把上游 `.pc` 文件里的 `Libs:` 行与
`cpp_info.libs` 逐项对照，差集就是需要手工补的库。`.pc` 是上游作者的事实来源，
`cpp_info` 是制品作者的手工模型，两者会漂移。

## 适用边界

- 触发条件：**上游 configure 的 pkg-config 模块，其提供者与某个传递依赖是同一
  库的不同配方/版本**。自测信号：链接报错里出现 `icu_<N>::` / `libfoo_<N>_`
  这类带版本号的符号命名空间。
- 不适用于「只有一份 ICU 但仍报未定义」的情况——那通常是缺
  `system_libs`（pthread/m）或缺 `-licuio` 这类模块遗漏，按 ② 处理。
- 本仓同族高危包：apertium、lexd、以及任何 HFST / foma / lttoolbox 家族成员
  （它们共享 lttoolbox→icu4c/77 这条传递边）。

## 关联

- 复用知识库 **E355**（制品 `.pc` 的 `prefix=/`）、**E468**（`PKG_CONFIG_PATH`
  需自行追加）、**E247**（`pkg-config --static` / 静态 C++ 运行时传播）。
- 本条目来自 lexd 1.3.5（Apertium 词典编译器）HarmonyOS PC aarch64 适配。
