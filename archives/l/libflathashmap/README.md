# libflathashmap

libflathashmap packages the `skarupke/flat_hash_map` snapshot used by Debian as a collection of fast, header-only C++ hash maps and hash sets.

## 功能概述

- `ska::flat_hash_map` 与 `ska::flat_hash_set`：开放寻址的扁平哈希容器。
- `ska::bytell_hash_map` 与 `ska::bytell_hash_set`：以字节元数据组织的扁平哈希容器。
- `ska::unordered_map` 与 `ska::unordered_set`：链式桶哈希容器。
- 提供接近标准无序容器的插入、查找、删除、迭代、容量管理与分配器接口。

## OHOS 适配

该库没有二进制产物，以 Conan header-library 形式安装三个公开头文件。HarmonyOS PC 消费者使用 clang 15、libc++、C++14 与 aarch64 ABI 编译。适配补全了 `bytell_hash_map.hpp` 对 `<limits>` 的直接依赖，以确保每个公开头文件均可独立包含。

## 依赖关系

无第三方编译或运行依赖，仅使用 C++ 标准库。

## 参考资料

- 上游仓库：https://github.com/skarupke/flat_hash_map
- 上游提交：https://github.com/skarupke/flat_hash_map/commit/2c4687431f978f02a3780e24b8b701d22aa32d9c
