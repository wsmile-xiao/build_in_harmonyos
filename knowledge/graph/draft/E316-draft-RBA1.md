# E316: Conan 包 SONAME 实体缺失（libopenblas.so.0）导致移动包 NEEDED 解析失败

> **Contributor**: RBA1 | **Status**: DRAFT | **Created**: 2026-08-09
> **Severity**: blocking | **Category**: packaging

## 错误特征

consumer `test_package` 将包移动到 `moved-r-base` 并屏蔽 Conan cache 后运行 R，报错信息如下：

```text
Error loading shared library libopenblas.so.0: (needed by .../lib/R/bin/exec/R)
Error relocating .../exec/R: zgemm_: symbol not found
```

该错误仅在包被移动到非原路径后出现。在原始构建路径下 R 可正常运行，因为动态链接器能通过 Conan cache 的 RPATH 找到 libopenblas。

## 触发条件

1. R 4.5.1 在 HarmonyOS 上使用 Conan 打包，依赖 OpenBLAS 作为 BLAS/LAPACK 后端。
2. R 的 `exec/R` ELF 的 NEEDED 条目记录的是 OpenBLAS 的 SONAME `libopenblas.so.0`（而非 `libopenblas.so`）。
3. Conan 包的 `_prepare_relocatable_runtime` 函数只复制了 `libopenblas.so`（开发者符号链接），未复制 `libopenblas.so.0`（SONAME 实体）。
4. OpenBLAS Conan 包内 `libopenblas.so` 与 `libopenblas.so.0` 均是指向 `libopenblas_armv8p-r0.3.33.so` 的符号链接。
5. consumer test_package 将包移动到 `moved-r-base` 并屏蔽 Conan cache 后，动态链接器按 SONAME 查找 `libopenblas.so.0`，但该文件不存在，导致加载失败。
6. `zgemm_` 等 BLAS 函数符号未解析，R 启动崩溃。

## 根因分析

ELF 动态链接的 SONAME 机制要求：可执行文件的 NEEDED 条目中记录的 SONAME，必须在动态链接器的搜索路径中找到对应的实体文件。

OpenBLAS 的库文件布局如下：

```text
libopenblas.so        -> libopenblas_armv8p-r0.3.33.so  (开发者符号链接)
libopenblas.so.0      -> libopenblas_armv8p-r0.3.33.so  (SONAME 符号链接)
libopenblas_armv8p-r0.3.33.so                           (实体共享库)
```

R 的 `exec/R` 在链接时记录了 NEEDED: `libopenblas.so.0`（这是 OpenBLAS 的 SONAME，由 `readelf -d` 中的 SONAME 字段决定）。

Conan 包的 `_prepare_relocatable_runtime` 只复制了 `libopenblas.so`，未复制 `libopenblas.so.0`。在原始构建路径下，动态链接器能通过 Conan cache 的 RPATH 找到 `libopenblas.so.0`，所以问题被掩盖。但一旦包被移动到非原路径并屏蔽 Conan cache，动态链接器在包内找不到 `libopenblas.so.0`，加载失败。

## 解决方案（含验证）

### 推荐方案：copy SONAME entity（conanfile.py 修复）

在 `conanfile.py` 的 `_prepare_relocatable_runtime` 中，复制库文件时必须同时提供 SONAME 实体：

```python
shutil.copy2(os.path.join(openblas_folder, "lib", "libopenblas.so"),
             os.path.join(rlib, "libopenblas.so"))
shutil.copy2(os.path.join(openblas_folder, "lib", "libopenblas.so.0"),
             os.path.join(rlib, "libopenblas.so.0"))
```

关键设计点：

- `shutil.copy2` 跟随符号链接复制实体文件，两份均为实体（各自是 `libopenblas_armv8p-r0.3.33.so` 的完整副本）。
- 也可采用等价方式保证 SONAME 文件存在（如先复制实体再创建符号链接）。
- 打包日志应出现 `Packaged ... libopenblas.so.0`。

### 验证

```bash
# 检查 NEEDED
llvm-readelf -d <package>/lib/R/bin/exec/R | grep NEEDED
# 应包含: NEEDED libopenblas.so.0

# 检查包内 SONAME 实体
ls -lh <package>/lib/R/lib/libopenblas.so*
# 应同时存在 libopenblas.so 和 libopenblas.so.0

# consumer 移动包验证
cp -r <package> moved-r-base
cd moved-r-base && R --version
# 应正常输出版本信息
```

Round 16 retry-03 完整 CI exit 0，全部 marker PASS。

## 互引说明

- **similar_to E068**: E068 是 HarmonyOS 缺少 `/sbin/ldconfig` 导致 `ctypes.util.find_library()` 失败；E316 是 Conan 包内 SONAME 实体缺失导致动态链接器加载失败。两者均涉及共享库发现机制在 HarmonyOS 上的差异。
- **similar_to E207**: E207 是 HarmonyOS CMake 使用相对路径链接项目内库（如 `../libheif/libheif.so`），而非标准 SONAME；E316 是 Conan 包内只复制了开发者符号链接（`libopenblas.so`）而未复制 SONAME 实体（`libopenblas.so.0`）。两者均涉及 SONAME 在 HarmonyOS 打包/链接中的特殊行为，但根因不同：E207 是 CMake 链接路径问题，E316 是打包期实体复制遗漏。
- 与 E243（Rprof ITIMER）、E244（时区）、E246（install sed 范围限定）属同一 r-base 4.5.1 适配批次（Round 5-16）。
