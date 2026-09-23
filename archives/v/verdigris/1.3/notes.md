# verdigris 1.3 适配笔记

## 编译环境
- 构建系统: header-only
- 编译日期: 2026-09-19
- 编译器: clang/clang++
- 状态: published
- 上游仓库: https://github.com/woboq/verdigris
- 上游版本: v1.3 (2022-08-15)

## 编译步骤

verdigris 为 Header-Only 库，仅包含两个头文件 `src/wobjectdefs.h` 与 `src/wobjectimpl.h`，无 configure/CMake 编译过程：

```bash
# 源码获取
get(https://github.com/woboq/verdigris/archive/refs/tags/v1.3.tar.gz)

# 打包
copy src/*.h -> package/include/verdigris/
copy src/*.h -> package/include/
```

`package_id()` 清空（header-only 无二进制区分），`package_info` 仅声明 include 目录。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | wobjectdefs.h 依赖 QtCore/qobjectdefs.h | 头文件直接包含 Qt 元对象定义 | 配方不强制依赖 Qt；test_package 采用 header-only 回退验证 W_VERSION/W_OBJECT 宏，Qt 侧 W_SIGNAL/W_SLOT 归为 ohos_feature gaps |
| 2 | 上游测试为 qmake Qt Test 框架，需 Qt 测试库 | 上游 tests/*.pro 使用 CONFIG += testcase | 采用 qmake 统计口径（10 testcases），test_package 中标记 2/10 已执行、8 gaps 为 ohos_feature（需 QtGui/D-Bus） |
| 3 | test_package 依赖 qt5-qtbase/5.15.2.2 时真机触发 cmake/4.4.3 构建失败 KeyError: 'OHOS' | qt5-qtbase 无 OHOS 预编译包（11 compatible configs 均 miss），其 tool_requires cmake/4.4.3 的 conandata.yml 缺 OHOS 源映射 | 移除 test_package 对 qt5-qtbase 的强制 requires，改为 header-only 回退；利用 HMBS 提供的 /data/service/hnp/bin/cmake（4.1.2）通过 PATH 前置完成 CMake 消费者测试，避免拉取 conan cmake 包 |

## 源码修改

无补丁，纯头文件拷贝。

## 依赖版本

- 无必选依赖（header-only）。原计划 test_package 使用 qt5-qtbase/5.15.2.2 验证 W_OBJECT constexpr，但该包无 OHOS 预编译且会触发 cmake/4.4.3 OHOS 缺失，已回退为纯 header-only 验证。

## 验证结果

```bash
# 本地需在 OHOS 真机执行
conan create archives/v/verdigris/1.3 --user=ohpcd --channel=stable -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
# 预期：headers 安装至 include/verdigris/，test_package 编译通过，HMBS 标记产出
```

## 交付物

| 文件 | 说明 |
|------|------|
| include/verdigris/wobjectdefs.h | 宏定义头 |
| include/verdigris/wobjectimpl.h | 实现头 |
| include/wobjectdefs.h | 兼容路径 |
| include/wobjectimpl.h | 兼容路径 |
| licenses/LICENSE.LGPLv3 | 许可证 |

## 注意事项

- 需 C++14 relaxed constexpr（GCC 5.1+/Clang 3.5+/MSVC 2017+），OHOS clang 15 满足。
- 使用时需 `CONFIG += c++14` 并包含 `wobjectdefs.h` + `wobjectimpl.h`，并以 `W_OBJECT_IMPL` 实例化元对象。
- 许可证为 LGPLv3/GPLv2 双许可，header-only 降低 LGPL 约束。
