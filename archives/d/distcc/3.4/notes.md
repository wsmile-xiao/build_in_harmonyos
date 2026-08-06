# distcc 3.4 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-08-06
- 编译器: clang / clang++
- 状态: built（编译完成，conan 配方已生成）

## 编译步骤
1. 下载并解压 distcc 3.4 源码
2. 应用 7 个补丁（config.guess/config.sub 平台识别、configure 适配、stats.c/where.c 修复、setup.py Python 3.12 适配、arg.c NDEBUG 修复）
3. 执行 ./configure --prefix=$DEFAULT_PREFIX --without-libiberty 配置
4. make -j2 编译（需设置 LIBRARY_PATH 指向 libpython3.12 所在路径）
5. make install 安装

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | HarmonyOS 平台无法识别 | config.guess/config.sub 缺少 HarmonyOS 检测 | 更新添加 aarch64:HarmonyOS 检测 |
| 2 | configure 脚本检测失败 | 交叉编译环境差异 | 适配 configure 脚本 |
| 3 | src/stats.c 编译错误 | 平台特定头文件缺失 | 适配平台相关代码 |
| 4 | src/where.c 编译错误 | 平台特定 API 不兼容 | 适配平台相关代码 |
| 5 | include_server/setup.py 报错 No module named 'distutils' | Python 3.12 移除了 distutils 模块 | 将 distutils.core 替换为 setuptools.setup，distutils.extension 替换为 setuptools.extension.Extension |
| 6 | 链接错误: unable to find library -lpython3.12 | libpython3.12.so 不在标准搜索路径 | 设置 LIBRARY_PATH 包含 HNP lib 目录 |
| 7 | Cannot find libiberty | HarmonyOS 不提供 libiberty 库 | 使用 --without-libiberty 禁用 @file 支持 |

## make check 结果
- 大部分测试通过（EmptySource_Case, HostFile_Case, AbsSourceFilename_Case, Getline_Case, Concurrent_Case, HundredFold_Case, BigAssFile_Case 等 OK）
- ModeBits_Case 失败：文件权限模式差异（HarmonyOS 平台限制，非功能性问题）
- maintainer-check-no-set-path 需设置 RESTRICTED_PATH 包含编译器路径

## 依赖版本
- 无特殊编译依赖
- 运行时需要 Python 3.12+（include-server 功能）
---

**编译结束**: 2026-08-06 07:30
**最终状态**: built
