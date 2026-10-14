# DRAFT-rocm-cmake-0.4.0-cmake4-policy-floor-and-git-metadata-tests

> 状态：草稿（来自 rocm-cmake 0.4.0 适配，上游 tag rocm-4.2.0）
> 类别：cmake / toolchain / testing / git / ohos-platform

本篇记录 rocm-cmake 0.4.0 在 OHOS 上运行上游 CTest 套件（19 用例）时暴露的**两类环境/
平台假设**，二者合计导致 4 个用例失败（另 2 个为无版本化软链，见同目录
`DRAFT-rocm-cmake-0.4.0-ohos-no-versioned-so-symlink`）。

## 一、CMake 4.x 策略下限：必须"双通道"下发

### 现象
CMake 4.1.2 对 `cmake_minimum_required(VERSION 3.5/3.6)` 在 `-Werror=dev` 下报
Deprecation Error（"Compatibility with CMake < 3.5 has been removed"）。rocm-cmake 0.4.0
的上游测试子工程声明 3.5/3.6，因此直接 configure 即失败。

### 根因
CMake 4.x 移除了对 `<3.5` 的兼容策略。`CMAKE_POLICY_VERSION_MINIMUM` 必须在
`cmake_minimum_required()` 执行**之前**生效：

- `tc.variables[...]` 写入 `conan_toolchain.cmake`，该文件在项目 CMakeLists 的
  `cmake_minimum_required` **之后**才被 include → **无效**。
- `tc.cache_variables[...]` 走 `-D` 命令行参数，在任何 CMakeLists 解析之前生效 → **有效**。

关键在于：rocm-cmake 的 `test/test.cmake` 会对**每个用例再跑一次 configure**（子工程），
这些嵌套 configure **不会**继承主工程的 `-D` 缓存变量，只会继承**环境变量**。因此策略
下限必须**双通道**：

1. 主工程：`generate()` 中 `tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.10"`；
2. 嵌套 configure：`build()` 中用 `Environment` 定义
   `CMAKE_POLICY_VERSION_MINIMUM=3.10`，包住 `cmake.ctest(...)`。

（此点与 DRAFT-E321 "CMake 4.x 拒绝 <3.5 的 cmake_minimum_required" 互补：E321 给出
`cache_variables` 这一通道；本条补充**嵌套 configure 需环境变量通道**，否则测试套件
内层子工程仍会硬报错。）

### 方案
```python
def generate(self):
    tc = CMakeToolchain(self)
    tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.10"
    tc.generate()

def build(self):
    env = Environment()
    env.define("CMAKE_POLICY_VERSION_MINIMUM", "3.10")
    with env.vars(self).apply():
        cmake = CMake(self); cmake.configure(); cmake.build()
        cmake.ctest(cli_args=["--output-on-failure", "-E", "..."])
```

## 二、上游 version-* 用例的 git 元数据假设

### 现象
`pass-version-norepo` / `pass-version-parent` 失败：期望值 0 与 `PROJECT_VERSION_TWEAK`
空值不等 / 宏参数缺失报错。

### 根因
上游版本测试框架假设测试树内 git 元数据可解析。在**解压的 tarball（非 git 树）**中：

- `git describe` 失败 → `PROJECT_VERSION_TWEAK` 为空；
- 且取值口径不一致：`ROCMSetupVersion` 用 `git describe --match [0-9]*`，而测试框架用
  `--always`，二者在不同仓库状态下给出不同结果。

配方注入 `GIT_AUTHOR_NAME/EMAIL`、`GIT_COMMITTER_NAME/EMAIL` 可解决"git 无身份、
无法操作"的问题（且符合 R33：经 Conan `Environment` 传参，不裸用 shell 变量），但
**无法凭空造出 git tag**，依赖 tag 的用例断言在 tarball 环境下从根本上不成立。

### 方案
无法满足 git tag 假设的用例用 `ctest -E` **显式排除**并在 MANIFEST.yml / notes.md 逐条
声明豁免；**不修改上游测试文件**。git 身份注入对 `rocm_setup_version()` 主工程调用与
其余可运行用例仍然必要，保留。

## 验证
- rocm-cmake 0.4.0，OHOS PC，CMake 4.1.2 / git 2.45.2：双通道策略下限 + git 身份注入后，
  上游 19 用例 **15 通过**，`pass-version-norepo` / `pass-version-parent` 连同 2 个 SOVERSION
  用例（见另一草稿）共 4 项显式豁免。
- test_package 消费者端到端 8 项断言全通过。

## 关联交付
- `archives/r/rocm-cmake/0.4.0/conanfile.py`（generate/build 双通道实现）
