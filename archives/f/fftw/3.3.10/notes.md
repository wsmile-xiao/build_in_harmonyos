# fftw 3.3.10 适配笔记

## 编译环境
- 构建系统: cmake（autotools 失败后改用）
- 编译日期: 2026-04-26
- 编译器: clang/clang++
- 状态: partial（CMake 编译成功）

## 编译步骤
1. 下载源码 `http://www.fftw.org/fftw-3.3.10.tar.gz`
2. 更新 config.guess 和 config.sub 为最新版本
3. **Autotools 构建失败**，改用 CMake
4. CMake 配置: `cmake -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DCMAKE_BUILD_TYPE=Release -DCMAKE_POLICY_VERSION_MINIMUM=3.5 ..`
5. `make -j$(nproc)`
6. `make install`
7. 预编译包包含: libfftw3.so、头文件、pkg-config 文件、cmake 配置文件

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Autotools configure 失败 | config.guess/config.sub 无法识别 OHOS | 更新 config.guess/config.sub 补丁 |
| 2 | Autotools 仍然失败 | 即使更新后仍有兼容性问题 | 改用 CMake 构建 |
| 3 | CMake policy 警告 | CMake 版本策略不兼容 | 设置 -DCMAKE_POLICY_VERSION_MINIMUM=3.5 |

## 源码修改
| 文件 | 修改内容 | 是否已生成补丁 |
|------|----------|---------------|
| config.guess | 添加 OHOS 平台识别 | ✅ 0001-config.guess.patch |
| config.sub | 添加 OHOS 平台支持 | ✅ 0002-config.sub.patch |

## 依赖版本
无外部依赖

## 注意事项
- Autotools 构建失败，必须使用 CMake
- 需要设置 CMAKE_POLICY_VERSION_MINIMUM=3.5
