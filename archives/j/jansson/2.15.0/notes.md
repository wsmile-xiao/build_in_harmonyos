# jansson 2.15.0 适配笔记

## 编译环境
- 构建系统: cmake（因缺少 automake 无法生成 configure 脚本）
- 编译日期: 2026-04-21
- 编译器: clang (LLVM)
- 状态: partial

## 编译步骤
1. 下载源码：https://github.com/akheron/jansson/archive/refs/tags/v2.15.0.tar.gz
2. 因缺少 automake 无法使用 autotools，切换到 CMake
3. 配置：`cmake .. -DCMAKE_INSTALL_PREFIX=$HOME/usr/local -DCMAKE_BUILD_TYPE=Release`
4. 编译：`make -j$(nproc)`
5. 测试：全部 215 个测试通过（100%）
6. 安装：`make install`

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 无法生成 configure 脚本 | 缺少 automake | 使用 CMake 构建 |

## 依赖版本
- cmake
- clang

## 验证结果
- 215 个测试全部通过（100%）
- 无平台兼容性问题

## 交付物
| 文件 | 大小 | 说明 |
|------|------|------|
| jansson-2.15.0-ohos-aarch64.tar.gz | 191.5KB | 预编译包 |
