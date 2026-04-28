# dar 2.8.1 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-04-24
- 编译器: clang / clang++
- 状态: success

## 编译步骤
1. 下载并解压 dar 2.8.1 源码
2. 应用 15 个补丁（config.guess/config.sub 平台识别、po 规则调整、源文件适配）
3. 执行 ./configure 配置
4. make -j 编译
5. make install 安装
6. 独立目录安装验证通过
7. 预编译包制作完成（含主包和 debug 包）

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | HarmonyOS 平台无法识别 | config.guess/config.sub 缺少 HarmonyOS 检测 | 更新 config.guess/config.sub 添加 aarch64:HarmonyOS 检测 |
| 2 | po/Makefile.in 编译规则不兼容 | 交叉编译环境差异 | 调整 Makefile.in 规则 |
| 3 | 多个源文件编译错误 | 平台特定 API 不兼容 | 逐一修复 check-*.cpp 和 dar_suite 中的文件 |

## 依赖版本
- zlib
- bzip2
- openssl

## 交付物
| 文件 | 大小 | 说明 |
|------|------|------|
| dar-2.8.1-ohos-aarch64.tar.gz | 14635KB | 主包 |
| dar-2.8.1-ohos-aarch64-debug.tar.gz | 1722KB | debug 包 |
