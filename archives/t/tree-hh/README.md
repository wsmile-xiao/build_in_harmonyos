# tree.hh

## 软件描述
tree.hh 是一个 header-only 的 C++ STL 风格树容器库，提供树形数据的插入、遍历、删除等操作（类似 STL container 的接口）。

## 功能概述
- **树容器**：`tree<T>`——STL 风格树（insert/erase/iterator）
- **树工具**：`tree_util.hh`——树操作辅助（kth_ancestor、subtree 等）
- **前序/后序遍历**：pre_order/sibling iterator

## OHOS 适配

### 构建方式
- **header-only**：无构建系统（上游 Makefile 仅用于打包/文档）——`package()` 拷贝 `src/` 头文件（tree.hh/tree_util.hh/xinlin.hh）到 include
- 编译需 `-std=c++14`

### 关键攻坚点
1. **header-only**：纯头文件——aarch64 OHOS 直接可编译（无平台限制）
2. **上游测试实测**：编译 `src/test_tree.cc` 运行并与 `test_tree.output` 对比（diff 判通过）——rule 4 实测回填；另有 test1~4.cc 测试程序
3. **subprocess 绝对路径**：clang++ 用 `/data/service/hnp/bin/clang++` 绝对路径（OHOS posix_spawn 不按 PATH 搜索相对名实测）

### 与 Linux 的差异
- 无差异——纯头文件库，全平台行为一致

## 依赖关系
无外部依赖（header-only）。

## 版本记录
| 版本 | 状态 | 编译日期 | 备注 |
|------|------|---------|------|
| 3.18 | built | 2026-08-28 | header-only 无构建系统适配 |

## 参考资料
- 上游仓库: https://github.com/kpeeters/tree.hh
