# aws-c-common 0.12.6 适配笔记

## 编译环境
- 构建系统: CMake
- 编译日期: 2026-04-24
- 编译器: clang/clang++
- 状态: partial（编译完成但部分流程可能未走完）

## 编译步骤
1. 下载源码 aws-c-common-0.12.6.tar.gz
2. CMake 配置: `-DCMAKE_INSTALL_PREFIX=$HOME/usr/local -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=OFF -DBUILD_TESTING=OFF`
3. `cmake --build build -j$(nproc)` 编译
4. DESTDIR 模式安装

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| （无具体问题记录） | | | |

## 注意事项
- 状态为 partial，可能需要后续完成完整打包流程
- 无补丁文件，CMake 直接编译通过
- 是所有 AWS SDK for C 组件的核心基础依赖
- 产物: libaws-c-common.a + 头文件 aws/common/*.h + cmake 配置
