# cxxopts

## 软件描述
cxxopts 是一个轻量级的 C++ 命令行选项解析库（header-only，单头文件），提供了简洁、类型安全的 CLI 参数解析能力。

## 功能概述
- **选项解析**：短/长选项、positional 参数（`cxxopts::Options`）
- **类型安全**：自动类型转换（int/double/string/vector 等）
- **帮助生成**：自动生成 help 文本
- **异常安全**：解析错误抛出 `cxxopts::OptionException`

## OHOS 适配

### 构建方式
- **header-only C++11/14**：无库编译——`package()` 拷贝 `include/cxxopts.hpp`（单头文件）到 include
- CMake 构建（`CXXOPTS_BUILD_TESTS=OFF` 打包；测试单独 `CXXOPTS_BUILD_TESTS=ON` 构建）

### 关键攻坚点
1. **header-only**：单头文件——aarch64 OHOS 直接可编译（无平台限制）
2. **上游测试实测**：Catch2 单元测试（test/ 自带 catch.hpp——无需网络下载）——`CXXOPTS_BUILD_TESTS=ON` 构建 + ctest 运行，回填真实通过率（rule 4）
3. **subprocess 绝对路径**：cmake/ctest 用 `/data/service/hnp/bin/` 绝对路径（OHOS posix_spawn 不按 PATH 搜索相对名实测）

### 与 Linux 的差异
- 无差异——纯头文件库，全平台行为一致

## 依赖关系
无外部依赖（header-only）。

## 版本记录
| 版本 | 状态 | 编译日期 | 备注 |
|------|------|---------|------|
| 3.3.1 | built | 2026-08-28 | header-only CMake 适配 |

## 参考资料
- 上游仓库: https://github.com/jarro2783/cxxopts
