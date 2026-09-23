# E429: KDE ECM configure 阶段 qtpaths 宿主工具缺 OHOS libc++ 运行时（exit 127）

## 现象

conan create KDE Frameworks 6 包时，cmake.configure() 阶段报：

```
CMake Error at .../share/ECM/modules/ECMQueryQt.cmake:98 (message):
  Qt6 qtpaths call failed: 127
Call Stack (most recent call first):
  .../KDEInstallDirs6.cmake:210 (ecm_query_qt)
  CMakeLists.txt:14 (include)
```

日志中伴随大量：

```
Error loading shared library libc++_shared.so: (needed by .../qtbase/p/bin/qtpaths)
Error relocating .../libQt6Core.so.6.11.1: _Unwind_Resume: symbol not found
Error relocating ...: __cxa_begin_catch: symbol not found
```

## 根因

1. KDE Frameworks 的 `KDEInstallDirs6.cmake` 在 **configure 阶段**（非构建/测试阶段）通过
   `ECMQueryQt.cmake` 的 `ecm_query_qt()` 执行 qtbase 包内的 `qtpaths`。
2. `qtpaths` 是 OHOS 原生二进制，动态链接 `libc++_shared.so` / `libunwind.so`。
3. qtbase 的 conan 包 **不携带** 这些运行库（它们在 OHOS SDK 的
   `llvm/lib/aarch64-linux-ohos/` 下）。
4. conan `build()` 的默认环境没有把 SDK lib 目录放进 `LD_LIBRARY_PATH` →
   动态链接器找不到 libc++_shared.so → qtpaths exit 127。

历史注意：attica 6.18.0 当年在远程 runner 上构建成功（该 runner 环境 LD_LIBRARY_PATH
自带 SDK lib），本机/CI 直接构建才暴露。

## 修复

conanfile.py `build()` 中用 `Environment` 包装 configure：

```python
def build(self):
    apply_conandata_patches(self)
    cmake = CMake(self)
    with self._library_runtime_env().vars(self).apply():
        cmake.configure()
    with self._library_runtime_env().vars(self).apply():
        cmake.build()
    self._run_upstream_tests()

@staticmethod
def _ohos_sdk_lib_dirs():
    candidates = [
        "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib/aarch64-linux-ohos",
    ]
    candidates.extend(glob.glob(
        "/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/lib/aarch64-linux-ohos"))
    return [c for c in candidates if os.path.isdir(c)]
```

`_library_runtime_env()` 把 SDK 目录 + 各依赖包 lib 目录 + 构建目录 bin/lib 都
PREPEND 进 LD_LIBRARY_PATH（R33：路径来自配方逻辑，不裸用 shell env）。

## 验证

attica 6.14.0：修复前 `Qt6 qtpaths call failed: 127`；修复后 configure 通过，
完整构建 + 上游 CTest 2/2 + test_package 1/1 全绿。

## 关联

- 关联软件：attica、所有 KDE Frameworks 6 系（karchive/kconfig/kitemviews 等
  在远程 runner 构建的同族包在本机重建时同样可能命中）
- 关联规则：R33（禁止裸 shell 环境变量）
- 验证配方：`archives/a/attica/6.14.0/conanfile.py`
