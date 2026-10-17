# DRAFT-ohos-elf-sign-glob-versioned-shlib — 鸿蒙 ELF 签名 glob 必须用 '**/*.so*' 覆盖版本化实体库

> Contributor: ohpcd / AtomCode | Status: DRAFT | Updated: 2026-09-18 | Severity: 🔴 blocking
> Source: gobject-introspection 1.80.1（PR #10682）——g-ir-compiler 运行报 dlopen Permission denied

## 相关既有条目（同族差异化定位）

| 既有条目 | 收录状态 | 问题面 | 本 skill 的增量（差异化） |
|----------|---------|--------|--------------------------|
| E077 | 已收录 | 鸿蒙 ELF 自签名机制本身（binary-sign-tool、原子签名、非 ELF 跳过） | 本 skill 是 E077 的**具体落地陷阱**：签名**收集阶段**用 `'**/*.so'` 会漏掉版本化实体库（`libx.so.1.0.0` 不以 `.so` 结尾）。E077 讲「怎么签」，本 skill 讲「哪些文件必须签但 glob 常常漏掉」 |
| E212 | 已收录 | loader 白名单按进程绑定，`b/`（build）、`p/`（package）之外的共享库不可 dlopen | 本 skill 是**白名单内也失败**的场景：文件已在 `p/`（白名单内）但因未签名被拒，报错表现为「Error loading shared library … Permission denied」+ 一串误导性的 `symbol not found`（看似链接问题，实为 dlopen 被拒） |
| E083 / E128 / E219 | 已收录 | binary-sign-tool 相关其他场景 | 均未覆盖「版本化实体库命名（.so.1.0.0）导致 glob 漏配」这一具体形态 |
| DRAFT-E077B-ohos-sdk-autocodesign-invalid | draft | SDK autocodesign 失效场景 | 本 skill 是显式签名路径的 glob 覆盖问题，与 SDK 自动签名无关 |

**撞车判定**：全库查证 `版本化实体库`（0 命中）、`sign.*glob` 相关条目均为其他主题（E130/E133/E357/E369/E465 与签名 glob 无关）。E077 未提及 glob 匹配版本化库的细节，作为 E077 的细分姊妹条目申报（问题层相同、增量 = glob 模式必须用 `.so*`）。

## Scope（何时用）

- 鸿蒙下交付**共享库**（meson `shared_library` / CMake `add_library(SHARED)`，产物是 `libx.so.1.0.0` + SONAME `libx.so.1`）的 Conan 配方
- 消费方运行报 `Error loading shared library libx.so.1: Permission denied` + 一串 `symbol not found`
- 库从**静态形态升级为共享形态**后首次出现该问题

## Symptom

```
$ g-ir-compiler --version
Error loading shared library libgirepository-1.0.so.1: (needed by .../bin/g-ir-compiler)
Error relocating .../bin/g-ir-compiler: g_typelib_check_sanity: symbol not found
Error relocating .../bin/g-ir-compiler: g_irepository_prepend_search_path: symbol not found
...
# 直接 dlopen 也失败
ctypes.CDLL(".../libgirepository-1.0.so.1.0.0")  →  OSError: ...: Permission denied
```

## Root Cause

1. 鸿蒙 loader 对用户路径下的共享库有**签名要求**（hmmac / binary-sign-tool 自签名，E077/E212 系列）。
2. 配方 `package()` / `build()` 常用 `glob.glob('**/*.so')` 收集 ELF 逐个签名——但 meson/CMake 安装的共享库**真实文件名**是 `libx.so.1.0.0`（**不以 `.so` 结尾**），`'*.so'` 匹配不到 → 未签名。
3. 消费方 `dlopen('libx.so.1')` 时 loader 按 SONAME 找到实体库 `.so.1.0.0`，因未签名拒绝加载；链接该库的二进制随后报一串 `symbol not found`（**误导性**，根因是 dlopen 被拒而非缺链接）。

**为何 1.78.1.1 从未暴露**：其 girepository 是静态库（补丁改写），包内根本没有版本化 `.so` 文件，glob 漏配被掩盖。一旦升级到 girepository 为 `shared_library` 的 1.80，缺陷立现。

## Workaround / 修复

- 三处签名 glob（build 产物、giscanner 安装、package 后重签）全部改为 `glob.glob('**/*.so*')`。
- 对非 ELF 文件用 ELF magic 检查跳过（`binary-sign-tool` 对非 ELF 报 "not an elf file"）。
- 静态转共享形态的包，升级后必须**重新审计签名 glob**。

## Prevention

- 模板/惯例：签名收集统一用 `'**/*.so*'` + `os.path.isfile` + ELF magic 三重防护。
- 验证：包内 `find -name '*.so*'` 逐一确认含版本化实体库；运行链接该库的二进制复测。

## References

- PR #10682（GI 1.80.1）
- E077（ELF 自签名）、E212（loader 白名单）
