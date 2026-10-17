# faac 1.40 适配笔记

## 编译环境
- 构建系统: meson
- 编译日期: 2026-08-06
- 编译器: clang 15.0.4
- 状态: built

## 编译步骤

1. 下载源码: `https://github.com/knik0/faac/archive/refs/tags/faac-1.40.tar.gz`
2. 生成 Conan 配方: `ohc-run.py conan-init faac 1.40`
3. 验证配方: `ohc-run.py conan-verify faac 1.40` (G1-G4 + L2/L4/L5 全部通过)

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `meson_layout` ImportError | OHOS 适配版 conan 2.29.1 不含 `meson_layout` | 改用 `basic_layout` |
| 2 | `Meson.compile()` AttributeError | 此 conan 版本的 Meson 类用 `build()` 而非 `compile()` | 改用 `meson.build()` |
| 3 | `llvm-ar` not found | HarmonyOS `posix_spawn` 不搜索 PATH | 在 `generate()` 中设置 `tc.ar` 为完整路径 |
| 4 | `version: 1.40` YAML 解析为浮点数 | YAML 将 `1.40` 解析为 float 1.4 | 引号包裹 `version: "1.40"` |

## 源码修改

无补丁，源码直接编译。Conan 配方中的 `generate()` 方法设置了 `ar` 和 `strip` 的完整路径以解决 HarmonyOS `posix_spawn` 不搜索 PATH 的问题。

## 依赖版本

无外部依赖（仅可选 libm）

## 验证结果

```
conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
G1: PASS (recipe completeness)
G2: PASS (conan create clean build)
G3: PASS (system-name library isolation)
G4: PASS (product completeness)
L2: PASS (smoke test)
L4: PASS (checksec)
L5: PASS (product baseline)
```

## 注意事项

- HarmonyOS `posix_spawn` 不搜索 PATH，所有构建工具需使用完整路径
- conan 2.29.1 OHOS 适配版无 `meson_layout`，使用 `basic_layout` 替代
- conan 2.29.1 OHOS 适配版的 `Meson` 类用 `build()` 而非 `compile()`
- `_meta.yaml` 中的 `build_system` 需从 `autotools` 更正为 `meson`

---

**编译结束**: 2026-08-06 09:52
**最终状态**: built
