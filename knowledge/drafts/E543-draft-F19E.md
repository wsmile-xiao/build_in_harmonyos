# E543: ECM 6.26 KDEInstallDirs6 configure 期 qtpaths 运行失败（沙箱 libc++ 遮蔽）

> 草稿状态：pending-editor-review（最终编号由主编确认）
> 交付实例：kpackage 6.26.0（PR #8505，CI #40757 PASSED）

## 错误特征

在 OHOS 上构建使用 ECM >= 6.26 的 KDE Frameworks 6 库（或消费 KF6 包导出
`*Macros.cmake` 的下游包）时，`cmake.configure()` 阶段直接 FATAL_ERROR：

```
CMake Error at .../ECM/kde-modules/KDEInstallDirs6.cmake:210 (ecm_query_qt)
  .../ECM/modules/ECMQueryQt.cmake:98 (message):
  Qt6 qtpaths call failed: 127
```

日志细节（configure 输出）：

```
Error loading shared library libc++_shared.so:
  (needed by .../qtbase/6.11.1/p/bin/qtpaths)
Error loading shared library libc++_shared.so:
  (needed by .../qtbase/6.11.1/p/lib/libQt6Core.so.6.11.1)
Error relocating .../qtpaths: _ZdlPv: symbol not found
```

## 根因

ECM 6.26 的 `KDEInstallDirs6.cmake` 在 **configure 阶段**通过
`execute_process` 运行 qtbase 包导出的 `qtpaths` 二进制
（`ecm_query_qt -> QT_INSTALL_PREFIX`）。

- `qtpaths` 是 musl OHOS ELF，动态链接 `libc++_shared.so`；
- 沙箱默认 `LD_LIBRARY_PATH` 中 `/data/storage/el1/bundle/libs/arm64`
  下有一个**不兼容的** `libc++_shared.so`，遮蔽了 `/system/lib64` 下的
  兼容版本；
- 动态加载器加载失败 → `qtpaths` exit 127 → cmake FATAL_ERROR。

两个触发面：
1. **主配方 configure**：KF6 库自身的 CMakeLists include KDEInstallDirs；
2. **test_package configure**：消费 KF6 包导出的 `*Macros.cmake`
   （如 `KF6PackageMacros.cmake`）同样会 include KDEInstallDirs——
   下游消费者的 conanfile 也必须注入同样环境。

## 解法（推荐）

在 conanfile（主配方 + test_package）的构建/测试环境里向
`LD_LIBRARY_PATH` **前置**注入兼容库目录：

```python
def _cmake_build_env(self):
    build_env = Environment()
    if self.settings.os == "OHOS":
        for llvm_lib in sorted(glob.glob(
                "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/lib")):
            build_env.prepend_path("LD_LIBRARY_PATH", llvm_lib)
        build_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
    for dep in self.dependencies.values():
        if dep and dep.package_folder:
            build_env.prepend_path("LD_LIBRARY_PATH",
                                   os.path.join(dep.package_folder, "lib"))
    return build_env

def build(self):
    cmake = CMake(self)
    with self._cmake_build_env().vars(self).apply():
        cmake.configure()
        cmake.build()
```

要点：
- `prepend`（不是 append）——被遮蔽场景必须让兼容版本排在前面；
- configure、build、ctest 测试运行都要用同一环境（`.vars(self).apply()`
  包住全部步骤）；
- ctest 的测试二进制（链接了 KF6/Qt 动态库）同样需要 libc++，测试环境
  复用同一注入。

## 回退方案

若 `/system/lib64` 注入不可用（精简镜像等）：
- 把 qtbase 包自身 lib 目录前置（若其打包携带了链接时使用的
  libc++_shared.so 副本）；
- 或仅当宏模块非必需时 `CMAKE_DISABLE_FIND_PACKAGE` 掉拉入
  KDEInstallDirs6 的模块（KF 安装布局依赖它，一般不可禁）。

## 红线

- **禁止**把任意 `libc++_shared.so` 拷入 `/system/lib64` 或 `/lib64`
  覆盖系统库——破坏系统 ABI。

## 实证记录

| 包 | 版本 | 结果 |
|----|------|------|
| kconfig | 6.26.0 | 先例配方（archives/k/kconfig/6.26.0，`_cmake_build_env`） |
| bluez-qt | 6.28.0 | 同款注入先例 |
| kpackage | 6.26.0 | 本条目交付实例，conan create rc=0，上游 CTest 8/8 + test_package 2/2，CI #40757 PASSED |

- 验证命令：`conan create archives/k/kpackage/6.26.0 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=default --build=missing`
- 关联 PR：!8505（commit 3ef9e275b8）
- 草稿作者：2404_87638649
