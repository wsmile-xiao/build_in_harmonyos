# frozen

## 软件描述
frozen 是一个 header-only 的 C++14 编译期（constexpr）容器库，提供 map/set/unordered_map/unordered_set/string 等可在编译期构造的容器。

## 功能概述
- **编译期容器**：`frozen::map`、`frozen::set`、`frozen::unordered_map`、`frozen::unordered_set`（constexpr 构造）
- **编译期算法**：`frozen::algorithm`（sort/unique 等）
- **编译期字符串**：`frozen::string`、`frozen::basic_string`

## OHOS 适配

### 构建方式
- **header-only C++14**：无库编译——`package()` 拷贝 `include/frozen/` 头文件目录到 include
- CMake 构建（`FROZEN_BUILD_TEST=OFF` 打包；测试单独 `FROZEN_BUILD_TEST=ON` 构建）

### 关键攻坚点
1. **header-only**：纯头文件——aarch64 OHOS 直接可编译（无平台指令集限制）
2. **上游测试实测**：Catch2 单元测试（tests/ 自带 catch.hpp——无需网络下载）——`FROZEN_BUILD_TEST=ON` 构建 + ctest 运行，回填真实通过率（rule 4）
3. **subprocess 绝对路径**：cmake/ctest 用 `/data/service/hnp/bin/` 绝对路径（OHOS posix_spawn 不按 PATH 搜索相对名实测）

### 与 Linux 的差异
- 无差异——纯头文件库，全平台行为一致

## 依赖关系
无外部依赖（header-only）。

## 版本记录
| 版本 | 状态 | 编译日期 | 备注 |
|------|------|---------|------|
| 1.2.0 | built | 2026-08-28 | header-only CMake 适配 |

## 参考资料
- 上游仓库: https://github.com/serge-sans-paille/frozen
