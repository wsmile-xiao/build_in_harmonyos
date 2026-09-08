# smashtable

## 简介
smashtable（SmashTable）是 Ash Vardanian 的 header-only C++20 关联容器库，
提供带 DBMS 风格事务的哈希表、AVL/权重平衡树、单调存储、快照与分区（sharded）
线程安全包装。容器共享同一套 upsert/find/erase/transaction API，并附带
Python 绑定（本次适配不涉及）。

## OHOS 适配
- **构建系统**: CMake（header-only INTERFACE 目标，`find_package(smashtable)`）
- **C++ 标准**: C++20（`cxx_std_20`）
- **依赖**: 无第三方依赖
- **补丁**: 3 个可移植性补丁（`std::atomic_ref` fallback、P0634 `typename`、
  测试框架 `<format>` fallback），全部由标准特性宏/符合标准的写法守卫

## 依赖
无
