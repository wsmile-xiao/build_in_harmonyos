# E2160-draft — OHOS SDK lld 链接器运行时依赖注入

> **Contributor**: atomcode | **Status**: DRAFT | **Updated**: 2026-08-24
> **Severity**: 🔴 blocking | **Category**: toolchain / lld / dynamic-linking

## Usage

当 OHOS PC 上任何库用 clang 链接（默认调用 SDK 的 lld）时，链接阶段报
`Error loading shared library libxml2.so.16: (needed by .../llvm/bin/lld)`
或 `Error relocating lld: xmlFreeDoc: symbol not found`，即 OHOS SDK 的 lld
链接器自身被链接进了 libxml2（DT_NEEDED）——须向 lld 注入其原生 RUNPATH
目标目录，而非 conan 的 libxml2（版本符号不匹配）。

## Scope

- OHOS SDK（ohos-sdk_*/ohos/native/llvm）自带的 lld 链接器（编译时链入
  libxml2，RUNPATH=$ORIGIN/../lib → SDK llvm/lib 自带 2.14.0）。
- 链接阶段失败：`Error loading shared library libxml2.so.16: (needed by lld)`
  或 `Error relocating lld: xml*: symbol not found`（约 18 个符号）。
- 不适用于运行时 dlopen 找不到依赖（那是 E088 musl namespace 范畴）。

## Symptom

```
LD_RUN_PATH=".../conan/.../lib" clang -shared ... -o LibXML.so -lxml2
Error loading shared library libxml2.so.16: (needed by /data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/lld)
Error relocating .../llvm/bin/lld: xmlFreeDoc: symbol not found
clang-15: error: linker command failed due to signal
make: *** [Makefile:552: .../LibXML.so] Error 1
```

## Fix

```python
# 链接前注入 lld 自身 RUNPATH 目标（SDK llvm/lib——lld 编译环境原生 libxml2）
sdk_llvm_lib = "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib"
self.run(f"LD_LIBRARY_PATH={sdk_llvm_lib} make", cwd=self.source_folder)
```

## Gotchas

1. **不要注入 conan 的 libxml2（2.15.3）**——lld 用 SDK 自带 2.14.0 编译，加载
   conan 版本符号版本不匹配（`xmlFreeDoc: symbol not found`）。
2. **readelf 动态解析 lld RUNPATH 在 CI 上不可靠**（实测 `_ld_env` 为空导致裸
   make 仍失败）——须硬编码 SDK llvm/lib 绝对路径。
3. 验证命令：`readelf -d lld | grep -E "NEEDED|RUNPATH"`（确认 DT_NEEDED 与
   RUNPATH 目标），`nm -D SDK/libxml2.so.16 | grep xmlFreeDoc`（确认符号完整）。
