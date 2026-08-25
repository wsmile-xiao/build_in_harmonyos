# E324 — Qt 子模块 SBOM 外部引用 spdx 找不到

## 错误特征

```
CMake Error at qt_sbom/DocumentRef-qtmultimedia-e1f418b985d2.cmake:19
  (_qt_internal_sbom_find_external_reference_document):
  Could not find external SBOM document sbom/qtmultimedia-6.11.1.spdx in any
  of the document search paths:
  .../build/Release/qt_sbom
  .../build/Release/generators
  .../lib/cmake
```

## 触发条件

- 构建系统: cmake
- 阶段: package() install（SBOM 装配）
- 适用: Qt 6.11 子模块引用其他 Qt 模块的包（如 qttexttospeech 依赖
  qtmultimedia）

## 根因分析

Qt 6.11 的 SBOM（Software Bill of Materials）装配在 install 阶段查找
依赖模块的 spdx 外部文档。qtmultimedia 包内 spdx 位于 `p/sbom/` 目录，
而装配脚本仅在 `lib/cmake`、`generators`、`qt_sbom` 等路径搜索，导致
`qttexttospeech` 等下游模块 install 时找不到外部引用文档而失败。

## 解决方案

### 推荐方案

conan 配方 generate() 禁用 SBOM 生成：

```python
tc.variables["QT_GENERATE_SBOM"] = False
```

### 禁止做法

- ❌ 手工拷贝依赖模块的 spdx 到搜索路径（破坏依赖原子性，多版本冲突）
- ❌ 修改上游 SBOM 装配脚本（随 Qt 升级失效）

## 验证

```bash
grep -rE "Could not find external SBOM document" build/log
# 空输出即已修复
```
