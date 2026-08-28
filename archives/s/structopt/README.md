# structopt

## 软件描述
structopt 是一个 header-only 的 C++17 命令行解析库，通过结构体反射式声明解析命令行参数——定义结构体字段即可自动生成 CLI 解析。

## 功能概述
- **结构体解析**：`structopt::app` 解析到 C++ 结构体（字段名即选项名）
- **类型支持**：基本类型/STL 容器/枚举/数组等
- **自动生成**：帮助文本、参数校验自动生成
- **子命令**：嵌套结构体子命令

## OHOS 适配

### 构建方式
- **header-only C++17**：无库编译——`package()` 拷贝 `include/structopt/` 头文件目录到 include
- CMake 构建（`STRUCTOPT_TESTS=OFF` 打包；测试单独 `STRUCTOPT_TESTS=ON` 构建）

### 关键攻坚点
1. **header-only**：纯头文件——aarch64 OHOS 直接可编译（无平台指令集限制）
2. **上游测试实测**：doctest 单元测试（tests/ 自带 doctest.hpp——无需网络下载）——`STRUCTOPT_TESTS=ON` 构建 + ctest 运行，回填真实通过率（rule 4）
3. **subprocess 绝对路径**：cmake/ctest 用 `/data/service/hnp/bin/` 绝对路径（OHOS posix_spawn 不按 PATH 搜索相对名实测）

### 与 Linux 的差异
- 无差异——纯头文件库，全平台行为一致

## 依赖关系
无外部依赖（header-only）。

## 版本记录
| 版本 | 状态 | 编译日期 | 备注 |
|------|------|---------|------|
| 0.1.3 | built | 2026-08-28 | header-only CMake 适配 |

## 参考资料
- 上游仓库: https://github.com/p-ranav/structopt
