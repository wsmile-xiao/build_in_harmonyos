# iperf3 3.18 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-04-27
- 编译器: clang (LLVM)
- 状态: partial

## 编译步骤
标准 autotools 流程：configure → make → make install。

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 平台识别 | config.guess/config.sub 不识别 HarmonyOS | 标准 autotools 补丁 |
| 2 | pthread stubs 缺失 | 平台差异 | 补丁修复 |

## 验证结果
编译成功，打包大小 234.6KB。6 个补丁。

## 交付物
| 文件 | 大小 | 说明 |
|------|------|------|
| iperf3-3.18-ohos-aarch64.tar.gz | 234.6KB | 预编译包 |

## 注意事项
- 6 个补丁涉及：CMakeLists.txt、pthread_stubs.c、config.guess、config.sub、iperf_config.h、version.h
