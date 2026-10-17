# DRAFT-lwow-4.0.0-cmake-subdir-no-install-manual-packaging：CMake 子工程库无 install 规则时的 Conan 2 手动打包

> Contributor: pc7-22 | Status: Draft | Updated: 2026-09-23
> Source: lwow 4.0.0 适配（Path B 知识库扩展，PR 与 lwow 归档同 PR）
> 对应：`knowledge/drafts/DRAFT-lwow-4.0.0-cmake-subdir-no-install-manual-packaging.kv`

## 问题

适配 `lwow`（LwOW — Lightweight OneWire 库）时，`conan create` 的 test_package 反复报：

```
Library 'lwow_devices' not found in package
No built lwow library archive found in build folder
CMake.configure() got an unexpected keyword argument 'source_dir'
```

## 根因

1. **上游子目录工程无 install 规则**：`lwow/CMakeLists.txt` 只有 `include(library.cmake)`，
   `library.cmake` 只 `add_library(lwow)` / `add_library(lwow_devices)` + `target_sources`，
   **没有任何 `install()` 规则** → `cmake install` 无产物 → test_package 必然找不到库。
2. **CMake.configure 无 source_dir 参数**：Conan 2 的 `CMake.configure()` 不支持
   `source_dir`，子目录工程必须用 `build_script_folder="<子目录>"`。
3. **cmake_layout 的 build_folder 语义**：Conan 2 `cmake_layout` 下
   `self.build_folder` 已经指向 `<cache>/p/b/<hash>/b/build/Release`，
   再拼 `os.path.join(self.build_folder, "build", "Release")` 会指向
   `.../build/Release/build/Release`（不存在）→ copy 静默零文件 → 空包。

## 方案

### build()：指向库子目录

```python
def build(self):
    apply_conandata_patches(self)
    cmake = CMake(self)
    cmake.configure(build_script_folder="lwow")  # lwow/ 是独立 CMake 工程
    cmake.build()
```

### package()：候选路径探测库产物

```python
def package(self):
    candidates = [
        os.path.join(self.build_folder, "build", "Release"),
        os.path.join(self.build_folder, "Release"),
        os.path.join(self.build_folder, "lwow"),
        self.build_folder,
    ]
    lib_src = None
    for cand in candidates:
        if os.path.isdir(cand) and any(
            f.endswith(".a") or f.endswith(".so") for f in os.listdir(cand)
        ):
            lib_src = cand
            break
    if lib_src is None:
        raise ConanException("No built lwow library archive found in build folder")
    copy(self, "*.a", lib_src, os.path.join(self.package_folder, "lib"), keep_path=False)
    copy(self, "*.so", lib_src, os.path.join(self.package_folder, "lib"), keep_path=False)
    copy(self, "*.h", os.path.join(self.source_folder, "lwow", "src", "include"),
         os.path.join(self.package_folder, "include"), keep_path=True)
    copy(self, "lwow_opts.h", os.path.join(lib_src, "lib_inc"),
         os.path.join(self.package_folder, "include", "lwow"), keep_path=False)
```

关键点：
- 探测而非猜测，全 miss 显式 `ConanException`（不产空包）。
- 头文件从 `source_folder/<子目录>/src/include` 复制（子目录工程的头布局）。
- 生成的配置头（如 `lwow_opts.h`）在 CMake binary 目录的 `lib_inc/`，单独 copy 到 `include/lwow/`。

## 验证

- `conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=... --build=missing` → test_package `1/1 tests passed`
- W3 本地 CI 模拟：`build_and_test.sh` RC=0，L0 全 pass（含 L0d test() 有 self.run）
- 产物核对：`conan cache path lwow/4.0.0:*` 下 `lib/liblwow.a + liblwow_devices.a`、`include/lwow/*.h` 存在

## 适用边界

- **适用**：库定义在子目录、子目录是独立可 configure 的 CMake 工程、上游无 install 规则的 Conan 2 配方。
- **不适用/反例**：上游已有完整 install() 规则的库（绝大多数）→ 直接 `cmake.install()`；components 建模的包不适用 flat libs 探测；header-only 包（INTERFACE）无 .a 无需此规则。
- 若允许改上游，`fallback` 为在子目录 CMakeLists 补 `install(TARGETS ... ARCHIVE DESTINATION lib)` 最小补丁；但优先不动上游源码。

## 与既有知识的查重差异

- `similar_to`: E340（conan package() glob 定位 cargo 产物）——同为"package() 手动定位产物"，但 E340 是 basic_layout+cargo，本条目是 cmake_layout+CMake 子工程，且明确了 build_folder 已含 build/Release 的语义边界。
- `similar_to`: E225（cmake_layout 临时布局）——布局语义相关，但主题是 test_package 临时目录而非主包打包。
- 新增差异：`build_script_folder` 子目录 + cmake_layout build_folder 边界 + 候选探测三者的组合，无既有条目覆盖。
