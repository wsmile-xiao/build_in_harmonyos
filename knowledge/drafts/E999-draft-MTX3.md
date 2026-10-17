# E999-draft-MTX3 — conanfile 的 generators 必须声明为类属性；只写在注释里不会有任何生成物

> **状态**：`draft: true`（路径 B 候选）
> **来源**：mtxclient 0.10.1 适配（PR #13832，commit `c47e3cd951`）
> **平台**：与平台无关（首次在 OHOS 真机 `conan create` 暴露）
> **关联**：E216（Conan/CMakeDeps 数据传播缺口同族）
> **非重复声明**：四范围查重对本机制零命中。

## 错误特征

配置阶段报找不到依赖的包配置文件，**报错位置在项目 CMakeLists 上**，因此第一眼像是依赖缺失或上游包名写错：

```
CMake Error at CMakeLists.txt:113 (find_package):
  By not providing "Findolm.cmake" in CMAKE_MODULE_PATH this project has asked
  CMake to find a package configuration file provided by "olm", but CMake did
  not find one.

    Could not find a package configuration file provided by "olm"
    (requested version 3.2.7) with any of the following names:

      olmConfig.cmake
      olm-config.cmake
```

此时 **依赖其实已正确发布并已解包**（`conan graph info` 显示 `binary: Cache`），
`find_package` 找不到配置纯属生成器没运行。

## 根因

Conan 依据 conanfile 的 **`generators` 类属性**（或 `generate()` 中显式实例化）决定运行哪些生成器。
把声明**只写进文档字符串或注释**时：

```python
"""...
* Both ``CMakeDeps`` and ``PkgConfigDeps`` are therefore generated: ...
"""                                       # ← 只是散文，Conan 不读

class FooConan(ConanFile):
    ...
    def generate(self):
        tc = CMakeToolchain(self)         # ← 只生成了工具链
        tc.generate()
```

Conan **不会报任何错**，但 generators 目录里只有：

```
conan_toolchain.cmake
CMakePresets.json
```

而不会有任何 `Xxx-config.cmake`、`XxxConfig.cmake`、`*.pc`。

### 判别动作（关键）

失败时**先看生成器目录到底产出了什么**，再判断是依赖问题还是生成器没跑：

```sh
ls <conan-build>/build/Release/generators
```

- 只有 `conan_toolchain.cmake` + `CMakePresets.json` → **生成器没跑**（本条）
- 有 `olm-config.cmake`、`re2.pc` 等但不全 → 另一类问题（如传递依赖数据缺口，E216）

## 触发条件

- 手写配方（非 `conan-init` 模板生成）时最容易漏；
- 或重构配方时把 `generators` 属性连带删掉/挪进注释；
- 需要 `CMakeDeps` / `PkgConfigDeps` / `MesonDeps` 等生成器的任何配方。

## 推荐方案

作为类属性声明（可读性最好，本库采用）：

```python
class MtxclientConan(ConanFile):
    # CMakeDeps supplies the find_package CONFIG files; PkgConfigDeps regenerates
    # the .pc files consumed by upstream's pkg_check_modules calls.
    generators = "CMakeDeps", "PkgConfigDeps"
```

或在 `generate()` 中显式实例化（更灵活，便于逐项设置属性）：

```python
from conan.tools.cmake import CMakeDeps
from conan.tools.gnu import PkgConfigDeps

def generate(self):
    CMakeDeps(self).generate()
    PkgConfigDeps(self).generate()
    tc = CMakeToolchain(self)
    ...
```

### 验证

`conan create` 的日志里会出现生成器自身的提示（存在这一行即说明生成器确实运行了）：

```
mtxclient/0.10.1: Generator 'CMakeDeps' calling 'generate()'
mtxclient/0.10.1: CMakeDeps necessary find_package() and targets for your CMakeLists.txt
    find_package(olm)
    target_link_libraries(... olm::olm nlohmann_json::nlohmann_json ...)
mtxclient/0.10.1: Generator 'PkgConfigDeps' calling 'generate()'
```

真机实测：补上该属性后 `find_package(olm)` 立即通过、configure 继续推进。

## 回退方案

若上游只用一种探测方式，可只声明对应生成器：

- 纯 `pkg_check_modules` → 只留 `PkgConfigDeps`
- 纯 `find_package(CONFIG)` → 只留 `CMakeDeps`

但必须先确认上游的探测方式：

```sh
grep -rn 'pkg_check_modules\|find_package' <src>/CMakeLists.txt
```

## ★ 禁止策略 ★

不要手工复制/软链 `.pc` 或 `*-config.cmake` 到生成器目录来"修好"它：这掩盖配方缺陷、
在其他执行机上不可复现，且 HMDFS 的符号链接本身不可靠（E050）。

## 备注

本条的教训是**「静默不执行」比报错更贵**：Conan 不会提示 `generators` 缺失，
失败现象又出现在项目 CMakeLists，很容易被误判成依赖问题而白白回头去查 W0。
因此诊断顺序应是：**先看生成器产出，再查依赖发布状态**。
