# aws-c-common 0.12.6 适配笔记

## 编译环境
- 构建系统: CMake
- 编译日期: 2026-07-15
- 编译器: clang/clang++ (15.0.4)
- 状态: built

## 编译步骤
1. 下载源码 aws-c-common-0.12.6.tar.gz (SHA256: 138822ecdcaff1d702f37d4751f245847d088592724921cc6bf61c232b198d6b)
2. CMake 配置: `-DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=OFF -DBUILD_TESTING=OFF`
3. `cmake --build build -j2` 编译
4. `make install DESTDIR=$TEST_PREFIX` 安装到 staging 目录

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 无 | | | |

## 注意事项
- 静态库模式 (BUILD_SHARED_LIBS=OFF)
- 无补丁文件，CMake 直接编译通过
- 是所有 AWS SDK for C 组件的核心基础依赖
- 产物: libaws-c-common.a + 头文件 aws/common/*.h + cmake 配置
- Conan 配方验证通过 (G1-G4, L2-L5 全部 PASS)
- 本地 CI 模拟通过 (setup.sh + build_and_test.sh)
---

**编译结束**: 2026-07-15 15:37
**最终状态**: built
