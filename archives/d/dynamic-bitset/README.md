# dynamic_bitset

## 软件描述
dynamic_bitset 是一个 header-only 的 C++17 动态位集库，提供可动态调整大小的位数组（类似 `std::bitset` 但长度运行时可变）。

## 功能概述
- **动态位集**：`sul::dynamic_bitset`——位数组动态增长
- **位运算**：and/or/xor/not、移位、计数（count/any/none）
- **遍历**：按位迭代、find_first/find_next
- **性能**：可选 libpopcnt 加速计数（`DYNAMICBITSET_USE_LIBPOPCNT`）

## OHOS 适配

### 构建方式
- **header-only C++17**：无库编译——`package()` 拷贝 `include/sul/dynamic_bitset.hpp`（单头文件）到 include
- CMake 构建（`BUILD_TESTING=OFF` 打包；测试单独 `BUILD_TESTING=ON` 构建）

### 关键攻坚点
1. **header-only**：单头文件——aarch64 OHOS 直接可编译（无平台指令集限制）
2. **上游测试实测**：Catch2 单元测试（tests/ 依赖 Catch2/libpopcnt **子模块**——tarball 不含）——`requires catch2/2.13.10-r0`（ohpcd 已发布），从包缓存拷贝 catch2 头到测试位置；`BUILD_TESTING=ON` 构建 + ctest 运行，回填真实通过率（rule 4）
3. **subprocess 绝对路径**：cmake/ctest 用 `/data/service/hnp/bin/` 绝对路径（OHOS posix_spawn 不按 PATH 搜索相对名实测）

### 与 Linux 的差异
- 无差异——纯头文件库，全平台行为一致

## 依赖关系
| 依赖 | 版本 | 用途 |
|------|------|------|
| catch2 | 2.13.10-r0 | 上游测试框架（仅本机构建时，can_run 守卫） |

## 版本记录
| 版本 | 状态 | 编译日期 | 备注 |
|------|------|---------|------|
| 1.3.3 | built | 2026-08-28 | header-only CMake 适配 |

## 参考资料
- 上游仓库: https://github.com/pinam45/dynamic_bitset
