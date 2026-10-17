# clang 的默认 C++ 标准低于 gcc（meson 未声明 cpp_std 时）

> 草稿 ID：`mmsd-tng-2.6.4-clang-default-cppstd-below-gcc`
> 来源任务：mmsd-tng 2.6.4 适配（meson 未声明 `cpp_std`；C++ 源 `src/phone-utils.cpp`
> 引用 libphonenumber → abseil）

## 错误特征

```
<absl>/base/policy_checks.h:81:2: error: "C++ versions less than C++17 are not supported."
<absl>/meta/type_traits.h:126:12: error: no member named 'conjunction' in namespace 'std'
<absl>/meta/type_traits.h:510:41: error: no template named 'is_reference_v' in namespace 'std'; did you mean 'is_reference'?
…
fatal error: too many errors emitted, stopping now [-ferror-limit=]
20 errors generated.
```

**首错是第一行的 `#error`**，后面 `std::*` 成员缺失都是级联——不要被它们带偏去找 abseil 版本问题。

## 触发条件

- 构建系统（meson/cmake）**未显式声明 C++ 标准**（meson `project()` 里没有 `cpp_std`）；
- 编译机是 clang 15（HarmonyOS/OHOS 默认工具链）；
- 编译单元间接包含要求 **C++17** 的第三方头库（abseil、protobuf、range-v3 等）。

## 根因

编译器默认语言标准不同：

| 编译器 | 默认 C++ 标准 |
|---|---|
| gcc ≥11 | `gnu++17` |
| **clang 15** | **`gnu++14`**（clang 16 起才默认 gnu++17） |

上游只在 Debian/gcc 上开发，没有声明 `cpp_std` 也一直正常；换到 clang 15 后
meson 不下发 `-std=`，编译器用 gnu++14 → abseil 的 `#error` 直接终止。

（同类差异也存在 C 侧：clang 15 默认 `gnu17`；风险主要落在 C++。）

## 解决方案（推荐）

让 conan profile 驱动，并在配方里加兜底：

```python
tc = MesonToolchain(self)
…
if not tc.cpp_std:            # profile 未设 compiler.cppstd 时的兜底
    tc.cpp_std = "c++17"      # abseil 等第三方头库的硬下限
```

- profile 的 `compiler.cppstd=17` 会被 MesonToolchain 自动映射为 meson 的
  `cpp_std=c++17`（本仓库 `ci/conan/profiles/ohos-aarch64` 已设），**无需改上游源码**；
- 兜底可防止"换个 profile 就退回 gnu++14 再炸一次"；
- 需要更高标准时用 `tc.project_options["cpp_std"] = "c++20"` 覆盖。

## 验证

```bash
# 修复前：编译命令里没有 -std=
$ ninja -C <builddir> -t commands | grep 'phone-utils.cpp'
/data/service/hnp/bin/clang++ … -c ../src/phone-utils.cpp        # 无 -std=

# 修复后
$ ninja -C <builddir> -t commands | grep 'phone-utils.cpp'
/data/service/hnp/bin/clang++ … -std=c++17 … -c ../src/phone-utils.cpp
$ meson test -C <builddir> --print-errorlogs
Ok: 4   Fail: 0   Skip: 0
```

## 反例（不要这么做）

- ❌ 用 `-Wno-error` 关掉这些报错 —— `#error` 是预处理期主动终止，不是警告；
- ❌ 降标准（`-std=c++14`）—— 只会把故障推到运行期 ABI 不一致，且与按 C++17
  构建的依赖包（abseil/protobuf）ABI 不匹配；
- ❌ 去更换/降级 abseil 版本 —— 真正缺的是 `-std=` 没下发。

## 证据

- 错误现场：`archives/m/mmsd-tng/2.6.4/reports/01-meson-compile-ohos.log`（第 92-113 行段）
- 配方实现：`archives/m/mmsd-tng/2.6.4/conanfile.py` → `generate()`（`if not tc.cpp_std`）
- 适配笔记：`archives/m/mmsd-tng/2.6.4/notes.md` §2/E6
