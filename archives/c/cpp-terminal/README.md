# cpp-terminal

## 软件描述
cpp-terminal 是一个 header-only 的 C++ 终端操作库，提供终端窗口、颜色、输入等能力（跨平台）。

## 功能概述
- **终端窗口**：`Term` 终端窗口管理（尺寸/光标/颜色）
- **终端输入**：按键/鼠标输入读取
- **终端输出**：颜色/样式输出（`Term::color`）

## OHOS 适配

### 构建方式
- **header-only**：无库编译——`package()` 拷贝 `cpp-terminal/` 头文件（terminal.h + terminal_base.h）到 include
- CMake 构建（`BUILD_TESTING=OFF` 打包；测试单独 `BUILD_TESTING=ON` 构建）

### 关键攻坚点
1. **header-only**：纯头文件——aarch64 OHOS 直接可编译
2. **上游测试实测**：doctest 单元测试（test_terminal.cpp 自带 doctest.h——无需网络下载）+ tests.sh（examples/colors/keys）——`BUILD_TESTING=ON` 构建 + ctest 运行，回填真实通过率（rule 4）
3. **subprocess 绝对路径**：cmake/ctest 用 `/data/service/hnp/bin/` 绝对路径（OHOS posix_spawn 不按 PATH 搜索相对名实测）

### 与 Linux 的差异
- 终端交互（键盘输入）需真实终端——OHOS 沙箱无 tty，键盘相关测试可能受限（如实记录）

## 依赖关系
无外部依赖（header-only）。

## 版本记录
| 版本 | 状态 | 编译日期 | 备注 |
|------|------|---------|------|
| 0.1.0 | built | 2026-08-28 | header-only CMake 适配 |

## 参考资料
- 上游仓库: https://github.com/jupyter-xeus/cpp-terminal
