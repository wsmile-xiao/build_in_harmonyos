# inipp

## 软件描述
inipp 是一个最小化的 header-only C++11 INI 解析库，提供简单、快速的 INI 文件读写能力。

## 功能概述
- **INI 解析**：解析 INI 文件到嵌套 map（`inipp::Ini<char>`）
- **Section/Key**：section 与 key-value 读取（`extract()` 类型转换）
- **简单 API**：`parse()` / `generate()` / `interpolate()` 等

## OHOS 适配

### 构建方式
- **header-only C++11**：无库编译——`package()` 拷贝 `inipp/inipp.h`（单头文件）到 include
- CMake 构建（`BUILD_TESTING=OFF` 打包；测试单独 `BUILD_TESTING=ON` 构建）

### 关键攻坚点
1. **header-only**：单头文件——aarch64 OHOS 直接可编译（无平台限制）
2. **上游测试实测**：unittest/（headertest + unittest 二进制 + test*.ini/test*.output 样本——CMake 自动拷贝到 build 目录）——`BUILD_TESTING=ON` 构建 + ctest 运行，回填真实通过率（rule 4）
3. **subprocess 绝对路径**：cmake/ctest 用 `/data/service/hnp/bin/` 绝对路径（OHOS posix_spawn 不按 PATH 搜索相对名实测）

### 与 Linux 的差异
- 无差异——纯头文件库，全平台行为一致

## 依赖关系
无外部依赖（header-only）。

## 版本记录
| 版本 | 状态 | 编译日期 | 备注 |
|------|------|---------|------|
| 1.0.13 | built | 2026-08-28 | header-only CMake 适配 |

## 参考资料
- 上游仓库: https://github.com/mcmtroffaes/inipp
