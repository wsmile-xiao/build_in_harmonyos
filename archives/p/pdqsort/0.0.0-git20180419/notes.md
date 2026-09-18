# pdqsort 0.0.0-git20180419 适配笔记

## 编译环境
- 构建系统: **无**（单头文件库，`pdqsort.h`）
- 编译日期: 2026-09-18
- 编译器: OHOS clang / clang++（Conan profile `ohos-aarch64`，`compiler.cppstd=17`）
- 状态: built

## 版本与源码
- 平台版本 `0.0.0-git20180419` = Debian 快照 `0.0.0+git20180419`（对应上游 2018-04-19 的
  `orlp/pdqsort` 提交）；Conan 版本不允许 `+`，故归档目录用 `-git<date>` 形式。
- 源码：`https://deb.debian.org/debian/pool/main/p/pdqsort/pdqsort_0.0.0+git20180419.orig.tar.gz`
  sha256 `6accfd63aecbe0c01f93e68a17eedb96d3eda5fdd35e47e72727457717213201`
- 备选：上游 `https://codeload.github.com/orlp/pdqsort/tar.gz/refs/heads/master`（master 会漂移，
  故以 Debian 快照为准）

## 产物
- `include/pdqsort.h`（544 行单文件）
- `licenses/license.txt`
- 无编译产物（`package_id()` 已清空二进制设置，一个包服务所有配置）

## 上游内容
```
pdqsort.h      # 单头文件：pdqsort / pdqsort / _branchless（含比较器重载）
bench/         # 基准程序（timsort.h 等），不打包
license.txt readme.md
```
上游**没有构建系统、没有测试**（无 CMakeLists/Makefile/tests），因此：
- 配方 `build()` 留空（不伪造编译）；
- R51 上游步骤如实申报 `not_applicable`；
- 功能验证全部由 `test_package` 的 CMake 消费者程序承担。

## 消费者测试（8 项断言）

`test_package/test_pdqsort.cpp` 链接安装后的头文件，覆盖：

| 断言 | 说明 |
|------|------|
| 1-2 | 整数数组排序结果与 `std::sort` 完全一致且有序 |
| 3 | 自定义比较器（`std::greater`）降序 |
| 4 | `pdqsort_branchless` 2000 元素 |
| 5 | 20000 个 LCG 伪随机整数与 `std::sort` 逐元素相同 |
| 6 | 5000 个相同元素（pattern-defeating 场景） |
| 7 | 已排序 / 逆序输入 |
| 8 | `std::string` 与空/单元素区间 |

## 验证结果

```sh
conan create archives/p/pdqsort/0.0.0-git20180419 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
# rc=0；ctest 1/1；消费者 8/8 断言
```
