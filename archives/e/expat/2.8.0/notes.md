# expat 2.8.0 适配笔记

## 编译环境
- 构建系统: cmake（autotools configure 在 HarmonyOS 上卡住）
- 编译日期: 2026-04-26
- 编译器: clang / clang++
- 状态: success

## 编译步骤
1. 下载并解压 expat 2.8.0 源码
2. 修改 config.guess/config.sub（添加 HarmonyOS 支持）
3. autotools configure 卡在 "checking how to create a ustar tar archive..."
4. 切换到 CMake 构建
5. CMake 配置 + make 编译 + make install
6. 本地安装验证：xmlwf --version 正常
7. 创建预编译包（cpio.gz 格式，因 tar/pax inode 问题）

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | autotools configure 卡住 | 可能是 toybox sh 或 SELinux 限制 | 改用 CMake 构建 |
| 2 | tar/pax 无法创建 ustar 格式包 | inode 号太大超出 ustar 格式限制 | 使用 cpio 格式替代 |

## 依赖版本
- 无外部依赖

## 交付物
| 文件 | 大小 | 说明 |
|------|------|------|
| expat-2.8.0-ohos-aarch64.tar.gz | 410KB | cpio.gz 格式预编译包 |

## 注意事项
- autotools 在 HarmonyOS 上可能卡住，建议始终使用 CMake 构建
- 打包时注意 inode 号限制，可能需要使用 cpio 替代 tar
