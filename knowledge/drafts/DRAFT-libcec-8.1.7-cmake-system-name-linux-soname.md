# CMAKE_SYSTEM_NAME=Linux：让 CMake 在 OHOS 上生成版本化 SONAME

> **适用范围**：OHOS 上需要版本化共享库（SONAME、`lib*.so.N`）供运行期按版本名加载的
> CMake 库（带 CLI 的库、dlopen 版本化名字的加载器）。典型对象：libcec（cec-client/
> cecc-client 经 cecloader 加载 `libcec.so.8`）、json-c 同款做法。
>
> **反例**：纯静态库无 SONAME 需求，不适用。

## 问题

libcec 8.1.7 构建安装后，运行 CLI 失败：

```
$ cec-client --version
Error loading shared library libcec.so.8: No such file or directory
Cannot load libcec.so
```

检查安装目录：只有裸 `libcec.so`，没有 `libcec.so.8` 软链；`readelf -d libcec.so` 无 SONAME 头。
CMake configure 时曾提示：`System is unknown to cmake, create: Platform/HarmonyOS ...`。

## 根因

OHOS 对 CMake 是**未知平台**（无 `Platform/HarmonyOS.cmake` 模块），CMake 不按 Linux 约定
生成版本化共享库命名——上游 `set_target_properties(... VERSION 8.1.7 SOVERSION 8 ...)` 的
版本化软链与 SONAME 头没有被产出。libcec 的 CLI（cec-client/cecc-client）经 cecloader
在**运行期**按 `libcec.so.8` 动态加载（`dlopen` 版本化名字），找不到即失败。

## 方案：构建期平台映射（json-c 同款）

conanfile `generate()`：

```python
tc = CMakeToolchain(self)
tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"   # OHOS 基于 Linux 内核，可复用 Linux 平台模块
tc.generate()
```

CMake 加载 `Platform/Linux.cmake` 后按 Linux 约定生成：

```
libcec.so.8.1.7   # 真实文件，带 SONAME=libcec.so.8
libcec.so.8 -> libcec.so.8.1.7
libcec.so  -> libcec.so.8
```

cecloader 运行期 `dlopen("libcec.so.8")` 即成功。**构建期自动生成，package() 无需手工
symlink**（与 E274 的手动方案互补）。

## 验证（libcec 8.1.7，OHOS aarch64）

```bash
readelf -d .../lib/libcec.so | grep SONAME          # → libcec.so.8
ls .../lib/ | grep 'libcec.so'                       # → libcec.so.8 / libcec.so 软链存在
cec-client --version                                 # → "CEC Parser created - libCEC version 8.1.7"
```

conan-verify G2（conan create）通过，W3 本地 CI L0-L5 pass。

## 边界与反例

- 仅适用共享库且需要版本化命名/运行期版本名加载的场景；静态库无 SONAME 需求；
- 设置 `CMAKE_SYSTEM_NAME=Linux` 仅影响 CMake 平台约定（.so 命名/install 布局），
  编译器仍是 OHOS clang + sysroot，不改变 ABI/目标三元组；
- 若库的 CLI 加载器只 fallback 裸名（`libcec.so`）而无版本名，本问题不触发，但生成
  版本化 SONAME 仍是更规范的做法。

## 关联

- similar_to：E092（cmake-toolchain，CMAKE_SYSTEM_NAME 平台检测，仅覆盖 configure 失败）、
  E274（create-soname-symlink，package() 手动软链）
- 新增差异：E092 未覆盖"平台映射 → 构建期自动生成版本化 SONAME + 运行期 CLI 加载验证"；
  E274 为 package() 手工方案，本条目为构建期自动方案
