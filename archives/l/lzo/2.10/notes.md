# lzo 2.10 适配笔记

## 编译环境
- 构建系统: autotools
- 编译器: clang
- 状态: published

## 编译步骤
标准 autotools 构建，需更新 config.guess/config.sub 以支持 HarmonyOS 平台检测。

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 不识别 HarmonyOS | GNU config 缺少 __OHOS__ 检测 | 补丁更新 config.guess/config.sub |

## 源码修改
| 文件 | 修改内容 | 是否已生成补丁 |
|------|----------|---------------|
| config.guess | 添加 HarmonyOS 检测 | ✅ |
| config.sub | 添加 ohos 支持 | ✅ |

## lzo2 static-build variant
lzo2 was same upstream 2.10, built as static-only (--enable-static --disable-shared).
Provides liblzo2.a for dependent projects.
