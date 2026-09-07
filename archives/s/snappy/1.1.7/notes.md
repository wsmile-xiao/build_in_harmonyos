# snappy 1.1.7 — 编译进度与排障记录

> 档案创建时间：2026-09-03
> 当前状态：✅ success（conan create 主包 + test_package 全通过）

## 一、基本信息
| 项 | 值 |
|----|----|
| 软件 | snappy |
| 版本 | 1.1.7 |
| 状态 | ✅ success |
| 构建系统 | CMake（Ninja generator）|
| 源码 | https://github.com/google/snappy/archive/refs/tags/1.1.7.tar.gz |
| 产物 | libsnappy.a + include + lib/cmake/Snappy |

## 二、排障记录（对话断点续传）
### 障碍 1：CMake 4.x 拒绝 `<3.5` cmake_minimum_required
- 现象：`CMake Error at CMakeLists.txt:1 (cmake_minimum_required): Compatibility with CMake < 3.5 has been removed`
- 根因：snappy 1.1.7 声明 `cmake_minimum_required(VERSION 3.1)`；CMake 4.1.2 移除该兼容（知识库 E103/E187/E447）。
- 修复：conanfile 用 `tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"`（**注意**：用 `tc.variables` 写 toolchain 文件不生效，必须 cache_variables 以 `-D` 传入，见草稿 DRAFT-E321）。

### 障碍 2：make 硬编码 `SHELL=/bin/sh` 被 hmmac 拒绝
- 现象：`make[1]: /bin/sh: Permission denied`（CMake try-compile 失败，`Check for working C compiler ... broken`）。
- 根因：OHOS OpenDesk 沙盒 hmmac 策略拒绝执行 `/bin/sh`，Unix Makefiles generator 硬编码 `SHELL=/bin/sh`（知识库 E346）。
- 修复：改用 **Ninja generator**（`tools.cmake.cmaketoolchain:generator=Ninja` + `CMAKE_MAKE_PROGRAM=/data/service/hnp/bin/ninja`），主包与 test_package 均需设置。

### 障碍 3：test_package CMakeDeps 重复
- 现象：`CMakeDeps is declared in the generators attribute, but was instantiated in the generate() method too`
- 修复：移除 test_package conanfile 的 `generators="CMakeDeps","CMakeToolchain"`，改在自定义 `generate()` 中显式调用。

## 三、测试
- test_package 消费者冒烟测试：`Snappy round-trip OK: compressed 53 -> 55 bytes`（1/1 PASS）。

## 四、状态
- `conan create archives/s/snappy/1.1.7 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64`：✅ 全通过。

## 五、结束记录
- **最终状态**: success
- **结束时间**: 2026-09-03
