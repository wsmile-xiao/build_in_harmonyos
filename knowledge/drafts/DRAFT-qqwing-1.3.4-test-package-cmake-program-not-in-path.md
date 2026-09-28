# DRAFT-qqwing-1.3.4-test-package-cmake-program-not-in-path：test_package 用 CMake 构建时 cmake 不在 PATH

> Contributor: qqwing-1.3.4 适配 | Status: Draft | Updated: 2026-09-20
> Source: archives/q/qqwing/1.3.4

## 现象

qqwing 1.3.4 主包用 autotools 构建成功（conan create 通过），但进入 test_package 阶段后失败：

```
qqwing/1.3.4 (test package): Running CMake.configure()
qqwing/1.3.4 (test package): RUN: cmake -G "Unix Makefiles" ...
/system/bin/sh: cmake: inaccessible or not found
ERROR: qqwing/1.3.4 (test package): Error in build() method, line 21
	cmake.configure()
ConanException: Error 127 while executing
```

## 根因

- OHOS 真机 shadow CI 的登录/runner `PATH` 不含 `/data/service/hnp/bin`（cmake 实际所在目录，
  与 clang/ld/ar/ranlib 同目录）。
- 主包 autotools 能拿到工具链，是因为 profile 里 `tools.build:compiler_executables` 给了
  clang 的绝对路径，加上配方里命令内 `export LD/AR/RANLIB` 的完整路径。
- 但 `test_package/conanfile.py` 用 `generators = "CMakeDeps", "CMakeToolchain"`，
  Conan 的 CMake helper 默认以 `"cmake"`（靠 PATH 查找）作为 cmake_program，
  PATH 里没有 → `Error 127`。

## 边界

- 仅 test_package 用 CMake、且真机 PATH 不含 cmake 时命中。
- 主包若也用 CMake，同样会命中（只是本例主包是 autotools）。

## 方案（最小修复）

在 `test_package/conanfile.py` 的 `build()` 里，调用 CMake 之前显式指定 cmake 路径：

```python
def build(self):
    self.conf.define("tools.cmake:cmake_program", "/data/service/hnp/bin/cmake")
    cmake = CMake(self)
    cmake.configure()
    cmake.build()
```

- 也可回退为在 `generate()` 里 `Environment.prepend_path("PATH", "/data/service/hnp/bin")`，
  但**不要**用 `Environment.save_script("conanbuild")` 覆盖聚合环境（见姊妹草稿
  `DRAFT-qqwing-1.3.4-conanbuild-recursive-source-printenv-e2big`）。

## 验证

- 修前：test_package `cmake.configure()` Error 127（`cmake: inaccessible or not found`）。
- 修后：cmake 用完整路径配置/构建，test_qqwing 编译链接运行通过，test_package 全绿。

## 查重结论

- knowledge/graph、knowledge/drafts 中无 `cmake_program` / `tools.cmake:cmake_program` 等价条目。
  - E296 是 Meson 交叉文件里 ar/ranlib 路径；E328 是 Cargo 原生子构建的 ranlib 包装器，
    均非「test_package 的 CMake helper 找不到 cmake」这一场景。
- 本条目为新增。
