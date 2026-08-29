# rapidcsv

## 软件描述
rapidcsv 是一个 header-only 的 C++11 CSV 解析库，提供快速、简单的 CSV 文件读写能力。

## 功能概述
- **CSV 解析**：从文件/字符串读取 CSV 数据（`rapidcsv::Document`）
- **类型转换**：自动类型转换（int/double/string 等，`GetCell<T>()`）
- **行列操作**：按行/列/单元格读写
- **选项控制**：分隔符、引号、行号等配置（`SeparatorParams`/`LineReaderParams`）

## OHOS 适配

### 构建方式
- **header-only C++11**：无库编译——`package()` 拷贝 `src/rapidcsv.h`（单头文件）到 include
- CMake 构建（`RAPIDCSV_BUILD_TESTS=OFF` 打包；测试单独 `RAPIDCSV_BUILD_TESTS=ON` 构建）

### 关键攻坚点
1. **header-only**：单头文件——aarch64 OHOS 直接可编译（无平台限制）
2. **上游测试实测**：自定义 unittest 框架（tests/unittest.h + test00X.cpp + CSV 样本）——`RAPIDCSV_BUILD_TESTS=ON` 构建 + ctest 运行，回填真实通过率（rule 4）
3. **subprocess 绝对路径**：cmake/ctest 用 `/data/service/hnp/bin/` 绝对路径（OHOS posix_spawn 不按 PATH 搜索相对名实测）

### 与 Linux 的差异
- 无差异——纯头文件库，全平台行为一致

## 依赖关系
无外部依赖（header-only）。

## 版本记录
| 版本 | 状态 | 编译日期 | 备注 |
|------|------|---------|------|
| 9.07 | built | 2026-08-28 | header-only CMake 适配 |

## 参考资料
- 上游仓库: https://github.com/d99kris/rapidcsv
