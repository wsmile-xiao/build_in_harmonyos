# wyhash 0-2.gbp234f0c6 适配笔记

## 编译环境
- 构建系统: 无（header-only / custom）
- 编译日期: 2026-09-15
- 编译器: OHOS clang（Conan profile `ohos-aarch64`，compiler.version=15）
- 状态: built

## 版本与源码
- 任务版本 `0-2.gbp234f0c6` 对应上游 `wangyi-fudan/wyhash` 提交 `234f0c6`
  （"Merge pull request #74 … Add copyright header"）。
- 源码通过 commit 归档获取：
  `https://github.com/wangyi-fudan/wyhash/archive/234f0c6.tar.gz`
  sha256 `c7a02ec93f457651b447d92af620a937580ffdb52496f8976c849827f575eeb7`。
- **不能使用上游 master**：master 已是 "final version 4.2"，算法与提交 `234f0c6`
  不兼容，哈希结果不同。

## 编译步骤

wyhash 是纯头文件库，无 configure/make 产物步骤：

1. `get()` 解压源码到 source 目录。
2. `package()` 复制根目录三个公共头文件 `*.h`（`wyhash.h`、`wyhash32.h`、
   `o1hash.h`）到 `include/`，`LICENSE` 到 `licenses/`。
   `old_versions/*.h` 是历史变体，不打包（不在根目录 glob 命中范围内）。
3. `package_id()` 用 `self.info.clear()`，因为头文件内容不随设置变化。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游 master 与任务版本结果不一致 | master 已升级为 final-4 算法 | conandata.yml 锁定 commit `234f0c6` 并校验 sha256 |
| 2 | 上游测试 `test_vector.cpp` 只打印、无退出码断言 | 上游无 ctest/assert 测试框架 | 记录官方 stdout 基线，在 test_package 中逐字节比对 |
| 3 | OHOS 下 CMake 缺少 Platform/HarmonyOS.cmake | 平台文件未内置 | test_package 中设置 `CMAKE_SYSTEM_NAME=Linux` + `CMAKE_SYSTEM_PROCESSOR=aarch64` |

## 源码修改

无补丁（`patches/` 为空）。

## 依赖版本

无外部依赖；仅使用 C 标准库头文件。

## 验证结果

```bash
# 消费者测试（安装后的 CMake target）
./test_wyhash
# -> wyhash consumer test PASS (22 checks)

# 上游官方测试（test_vector.cpp 输出与基线逐字节比对）
./upstream_test_vector
# -> 7 行 wyhash(...) == 提交的基线
```

`conan create wyhash/0-2.gbp234f0c6` 退出码 0。

## 注意事项

- 头文件库：下游只需 include 路径，CMake 目标为 `wyhash::wyhash`。
- 哈希值依赖算法版本，引用本包时应固定版本号。
