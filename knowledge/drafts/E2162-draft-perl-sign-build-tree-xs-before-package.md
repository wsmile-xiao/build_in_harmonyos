# E2162-draft — perl 运行时与 XS 共享对象必须在 build tree 内先签名再安装

> **Contributor**: atomcode | **Status**: DRAFT | **Updated**: 2026-09-08
> **Severity**: 🟡 medium | **Category**: perl / packaging / codesign / runtime

## Usage

当 OHOS 上的 `perl` 包在 `package()` 阶段才签名，或者只对 Conan 包缓存里的副本补签时，`perl` 可执行文件和 `auto/*/*.so` 仍可能被加载器拒绝，表现为 `Permission denied` 或 `Error loading shared library`。

## Scope

- `perl/5.42.2.1` 这类运行时包。
- 由 Perl `Configure` + `make` 产出的可执行文件和 XS 模块。
- 需要在真机上直接运行的 `perl`、`perl5.42.2`、`Fcntl.so`、`POSIX.so` 等 ELF。

## Symptom

```
Can't load '.../auto/Fcntl/Fcntl.so' for module Fcntl: Error loading shared library
Permission denied
```

## Fix

1. 在 build tree 中先定位所有可交付 ELF。
2. 对每个 ELF 先移除旧 `.codesign`，再用 `binary-sign-tool` 重签。
3. 确认签名后的文件仍保留执行位。
4. 安装到 Conan package 后再用 `llvm-readelf -S` 逐个核验 `.codesign`。

## Gotchas

- 只在 `package()` 里签名太晚，尤其是 XS `.so` 还会被中间产物复用。
- 不能把“已有 `.codesign`”当成已满足当前目标副本；build tree 和 cache 副本是两回事。
- 签名工具缺失时应直接失败，不要静默跳过。
