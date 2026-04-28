# distcc 3.4 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-04-17
- 编译器: clang / clang++
- 状态: partial（编译完成，部分功能待验证）

## 编译步骤
1. 下载并解压 distcc 3.4 源码
2. 应用 5 个补丁（config.guess/config.sub 平台识别、configure 适配、stats.c/where.c 修复）
3. 执行 ./configure 配置
4. make -j 编译
5. make install 安装

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | HarmonyOS 平台无法识别 | config.guess/config.sub 缺少 HarmonyOS 检测 | 更新添加 aarch64:HarmonyOS 检测 |
| 2 | configure 脚本检测失败 | 交叉编译环境差异 | 适配 configure 脚本 |
| 3 | src/stats.c 编译错误 | 平台特定头文件缺失 | 适配平台相关代码 |
| 4 | src/where.c 编译错误 | 平台特定 API 不兼容 | 适配平台相关代码 |

## 依赖版本
- 无特殊编译依赖
