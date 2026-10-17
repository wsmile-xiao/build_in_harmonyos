# DRAFT — OHOS GNUInstallDirs 将 CMake 库包装进 lib/<triplet> 子目录导致 CMakeDeps 找不到库

> 来源：json11 1.0.0 适配（R01，2026-09-02），路径 B 知识沉淀候选。
> 本文件为草稿，不修改任何正式知识文件；登记前需复查。

## topic

OHOS 交叉编译下，CMakeToolchain/GNUInstallDirs 将 CMake 库安装到 `lib/<gnu-triplet>/`（如 `lib/aarch64-linux-ohos/`）子目录，CMakeDeps 默认从 `lib/` 查找导致 `find_package` 报 "Library not found" 的识别与配方级修复。

## error_signature

- `Library '<pkg>' not found in package. If '<pkg>' is a system library, declare it with 'cpp_info.system_libs'`
- `cmakedeps_macros.cmake:81 (message)：conan_package_library_targets`
- 包内产物位于 `lib/aarch64-linux-ohos/lib<name>.a` / `include/aarch64-linux-ohos/`（而非 `lib/`、`include/`）

## root_cause

1. OHOS Conan 的 CMakeToolchain/GNUInstallDirs 在交叉编译时把 `CMAKE_LIBRARY_ARCHITECTURE` 计算为 OHOS GNU triplet（`aarch64-linux-ohos`）。
2. 上游 CMakeLists 若用 Debian 风格 multiarch 写法 —— `install(TARGETS <t> DESTINATION lib/${CMAKE_LIBRARY_ARCHITECTURE})`、`install(FILES <hpp> DESTINATION include/${CMAKE_LIBRARY_ARCHITECTURE})` —— 产物会落到 `lib/<triplet>/`、`include/<triplet>/`。
3. 配方 `generate()` 即使传 `-DCMAKE_LIBRARY_ARCHITECTURE=""` 也可能被 GNUInstallDirs 运行时重算覆盖（实测传入空值仍安装到 triplet 子目录）。
4. CMakeDeps 的 `conan_package_library_targets` 按 `cpp_info.libdirs`（默认 `lib/`）查找库文件，找不到 → test_package `find_package` 失败。

## solution

在 conanfile.py 的 `package()` 中，`cmake.install()` 之后遍历 `self.package_folder` 下 `lib/`、`include/` 内的所有 triplet 子目录，把其中文件 `rename` 到顶层并删除空子目录，使 CMakeDeps 能从默认 `lib/`/`include/` 解析库与头文件：

```python
def package(self):
    cmake = CMake(self)
    cmake.install()
    # OHOS CMakeToolchain / GNUInstallDirs place installed artifacts under
    # lib/<gnu-triplet> and include/<gnu-triplet> (e.g. aarch64-linux-ohos)
    # even when CMAKE_LIBRARY_ARCHITECTURE is empty; flatten them back to
    # plain lib/ include/ so CMakeDeps consumers resolve libjson11.a.
    from pathlib import Path
    root = Path(self.package_folder)
    for sub in ("lib", "include"):
        base = root / sub
        if not base.is_dir():
            continue
        for tri in list(base.iterdir()):
            if not tri.is_dir():
                continue
            for item in tri.iterdir():
                item.rename(base / item.name)
            tri.rmdir()
```

配方级修复，不修改上游源码，跨上游版本稳定。

## scope

- 适用：上游 CMakeLists 使用 `lib/${CMAKE_LIBRARY_ARCHITECTURE}` / `include/${CMAKE_LIBRARY_ARCHITECTURE}` 安装路径的 CMake 库包，在 OHOS aarch64 交叉编译 + Conan 2 CMakeDeps 下构建。
- 边界：上游不依赖 `CMAKE_LIBRARY_ARCHITECTURE`（直接写 `lib/`）的包不触发；GNUInstallDirs 在标准 Linux 主机构建时通常不产生子目录。多 arch 产物包（同一包内含多 triplet 目录）需按默认 arch 展开，谨慎 flatten。

## 验证（json11 1.0.0 实证）

- conan-verify：G0–G4 + L2/L4/L5 全 PASS（`reports/conan-verify-report.md`）。
- test_package 消费者：`find_package(json11)` + 链接 `json11::json11` + 实际调用 JSON API 断言通过（非空壳）。
- W3 本地 CI：`JC_RESULT=pass`（incremental 模式 9 文件），`L0_RESULT=pass: all checks passed`，`reports/w3-local-ci.log`。
- 产物验证：包内 `lib/libjson11.a`（非 `lib/aarch64-linux-ohos/libjson11.a`）。

## 查重差异

- E255（符号链接循环/BadZipFile）、E277（vendored 依赖）、E450（AVR target sysroot 与 OHOS host 元数据分离）、E449/E499/E505（共享库运行期 libdirs / LD_LIBRARY_PATH / DT_RPATH）：均为运行期或依赖方向，未覆盖「CMake 安装路径被 OHOS triplet 子目录劫持导致 CMakeDeps 找不到库」。
- E103/E187/E458（cmake_minimum_required < 3.5 / CMAKE_POLICY_VERSION_MINIMUM）：仅覆盖 CMake 版本兼容，未覆盖安装目录问题（json11 配方同时用到，属不同知识面）。
- DRAFT-bambootracker-qt6-executable-conan：含同症状 `Library '.*' not found in package`，但根因是**纯可执行包声明了不存在的 cpp_info.libs**；本候选根因是**真实库产物被装入 triplet 子目录**，修复手段（package() flatten vs 留空 cpp_info.libs）完全不同，不构成覆盖。
- 本文档核心增量：**OHOS GNUInstallDirs / CMAKE_LIBRARY_ARCHITECTURE 安装子目录问题 + package() 压平修复**。

## 适用条件与维护

- 登记后更新 `knowledge/graph/index.tsv` 与 `knowledge/doc/`（如需）。
- 本草稿 `id` 为 `DRAFT-json11-1.0.0-cmake-library-architecture-triplet-install`，未创建正式 `E###` 条目，未修改任何既有知识文件。