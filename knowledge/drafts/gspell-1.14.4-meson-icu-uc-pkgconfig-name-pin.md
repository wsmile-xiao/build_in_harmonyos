# meson 的 `dependency('icu-uc')` 为什么"找不到包"——以及找到之后链接为什么还是炸

> Draft: DRAFT-gspell-1.14.4-meson-icu-uc-pkgconfig-name-pin
> Stem: `gspell-1.14.4-meson-icu-uc-pkgconfig-name-pin` — pairs with the same-stem `.kv`

## 基本信息

- **ID**: DRAFT-gspell-1.14.4-meson-icu-uc-pkgconfig-name-pin
- **严重度**: 2
- **类别**: dependency-resolution, meson, pkg-config, conan, ohos-platform
- **触发工具**: conan|meson|pkg-config|clang
- **阶段**: configuration|linking

## 错误特征

第一阶段，meson 配置期：

```text
meson.build:25:10: ERROR: Dependency "icu-uc" not found, tried pkgconfig and cmake
```

第二阶段（换到能解析的版本之后），链接期：

```text
ld.lld: error: undefined symbol: __gxx_personality_v0
ld.lld: error: undefined symbol: __cxa_begin_catch
       referenced by libicuuc.a(uclnvr.o), libicudata.a(...)
```

这两个报错都**不指向真正的原因**：第一个看着像远程缺包或网络抖动，
第二个看着像编译器配置错误。它们实际是同一件事的两半。

## 根因分析

### 一半：meson 按 `.pc 文件名` 解析，不是按 Conan 包名

gspell 的 `meson.build` 里 ICU 是**私有依赖**：

```meson
icu_dep = dependency('icu-uc', version: '>= 0')     # 无版本约束
```

meson 的 `dependency()` 默认走 pkg-config 协议，它要的是一个叫
**`icu-uc.pc`** 的文件。Conan 的 `PkgConfigDeps` 生成 `.pc` 时，文件名由
recipe 的 `cpp_info.set_property("pkg_config_name", ...)` 决定，
**缺省等于 Conan 包名**：

| icu4c 版本 | `pkg_config_name` | `fPIC` 选项 | PkgConfigDeps 产出 | meson 能否解析 |
|-----------|-------------------|------------|-------------------|---------------|
| 77 | `"icu-uc"` | 有（`True`） | `icu-uc.pc` | ✅ |
| 78 | 未设置 | 无 | `icu4c.pc` | ❌ 配置期即失败 |

所以 78 不是"版本太新"，而是**recipe 少了一个 property**。这个报错在
CI 里表现为每次 `meson setup` 都挂，重跑无用——它是确定性的。

### 另一半：能用的那个版本是**静态 C++ 归档**

`icu4c/77` 默认 `shared=False`，交付的是 `libicudata.a` / `libicuuc.a` /
`libicui18n.a`。而 gspell 是**纯 C 工程**（`project('gspell', 'c', ...)`，
`libgspell-1.so.3` 全部由 C 源编译）：

```text
libicuuc.a 是 C++ 编的 → 带 C++ 运行时引用（异常/类型信息）
纯 C 链接命令      → 不会自动附加 C++ 运行时
→ undefined symbol: __gxx_personality_v0 / __cxa_begin_catch
```

注意这是**静态归档**特有的问题：如果 icu4c 是共享库，`DT_NEEDED` 会自己
带上 `libc++_shared.so`；静态归档则把符号解析责任推给了最终链接。

## 解决方案

**主方案**: `pin-by-pkg_config_name-and-add-lcxx-to-c-links`

### 第 1 步：钉版本前先核对 `pkg_config_name`

```sh
conan download icu4c/77 -r ohpcd          # 取回 recipe
grep -n 'pkg_config_name' ~/.conan2/p/*/e/conanfile.py
# → proj.set_property("pkg_config_name", "icu-uc")  (archives/i/icu4c/77/conanfile.py:138)
```

判据是二元的：**上游要的名字有没有对应的 `.pc`**。同族问题在 meson 里报
`Dependency "X" not found`，在 CMake 里报 `Could not find a package
configuration file`，看起来都像缺包/网络问题，实际都可能在依赖包里。

### 第 2 步：给 C 链接补 C++ 运行时

```python
tc = MesonToolchain(self)
if "-lc++" not in tc.c_link_args:
    tc.c_link_args.append("-lc++")
tc.generate()
```

OHOS 用 libc++；仓库内先例是 `archives/c/cif-api/0.4.2/conanfile.py`。
只补 C 链接就够了，C++ 链接本来就带运行时。

### 第 3 步：验收用**可观测行为**，不要停在"配置通过"

- `readelf -d libgspell-1.so.3` 看 `DT_NEEDED` 与符号解析是否完整；
- 消费者测试里断言上游自己声明的语义，例如 ICU 数据确实内嵌可用——
  gspell 的 `test-icu` 断言 `en_US -> "English (United States)"`，这正是
  "ICU 数据真的链进来了"的证据。

## 验证

```sh
conan create archives/g/gspell/1.14.4 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing -nr
# meson setup 不再出现 'Dependency "icu-uc" not found'
# 构建期上游单测 test-icu（2 例）通过：en_US 显示名断言成立
```

## 反例

| 反例 | 为什么不行 |
|------|-----------|
| `dependency('icu-uc', required: false)` / `-Dicu=disabled` | 把私有依赖整体关掉 = 阉割语言名本地化（`_gspell_icu_*`），换来"配置能过"而非"依赖解析正确"；退化不会在 CI 报错 |
| 钉 `icu4c/78` | recipe 缺 `pkg_config_name` 与 `fPIC`，配置期确定性失败；报错文案还误导成网络问题 |

## 关联条目

- 与同批 `gspell-1.14.4-upstream-test-set-from-dependency-graph` 构成 gspell
  适配的两条主线：本条讲**依赖解析与链接**，那条讲**测试集边界与计量口径**；
- 与仓库内 `cif-api/0.4.2` 共享 `-lc++` 处理；
- 与 `archives/i/icu4c` 的版本选择知识互为印证。
