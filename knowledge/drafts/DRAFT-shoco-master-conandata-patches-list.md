# DRAFT-shoco-master-conandata-patches-list：Conan 2 conandata.yml patches 必须用 list 格式

> Contributor: pc1-47 | Status: Draft | Updated: 2026-09-17
> Source: shoco master 适配（conan-verify G2 迭代链）

## 背景

shoco master 适配时，conanfile.py 的 build() 调用 `apply_conandata_patches(self)` 期望应用
`patches/0001-shoco-bin-alloca-h.patch`（为 shoco-bin.c 补 `<alloca.h>`）。初始 conandata.yml
把 patches 写成文件名键的 dict：

```yaml
patches:
  "0001-shoco-bin-alloca-h.patch":
    patch_file: "patches/0001-shoco-bin-alloca-h.patch"
    description: "..."
```

conan create 日志显示 "Apply patch (portability)" 从未出现，构建继续以未打补丁的源码编译，
最终在链接期报 `ld.lld: error: undefined symbol: alloca`——初看像 libc 问题，实际是补丁根本没
应用。

根因：Conan 2 的 `apply_conandata_patches` 对 **dict** 类型 patches 按
`{version: [补丁列表]}` 结构、用 `conanfile.version` 做键查找。这里的键是补丁文件名而非版本
（"master"），查找必然失配，打印 "No patches defined for version master" 后**静默返回**，
补丁完全不应用。

## 修复

改为 list 格式（无条件全量应用）：

```yaml
patches:
  - patch_file: "patches/0001-shoco-bin-alloca-h.patch"
    patch_description: "OHOS musl 下 alloca 需显式包含 <alloca.h>"
    patch_type: "portability"
```

验证：改写后 conan create 日志出现 "Apply patch (portability)"，补丁生效，编译/链接通过，
`conan-verify shoco master` G2 PASS。

## 适用范围与反例

- 适用：所有 Conan 2 配方在 conandata.yml 声明补丁的场景；version 为 "master"/滚动分支时 dict
  键查找必然失配，list 格式是唯一稳定写法。
- 反例/不适用：dict 格式本身合法（Conan 官方支持 `{version: [...]}` 多版本分支补丁）——只有
  键是**版本号**时才生效；单版本配方一律用 list。

## 查重差异

- 既有 E 条目均未覆盖该陷阱：E282（per-patch base_path 多源码根）、E515/E526（strip 语义 / -p1
  与 patch_ng 差异）均是"补丁应用"族其他维度；无条目覆盖 dict 按 version 键查找导致的静默不应用。
- 与 E282/E515/E526 同属"补丁未正确应用"族（similar_to/caused_by=无），触发机制与修复不同。