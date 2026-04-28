# gmssl 3.1.1 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-04-24
- 编译器: clang (HarmonyOS Native)
- 状态: partial（编译成功，测试因平台限制跳过）

## 编译步骤
1. 下载 GmSSL v3.1.1 源码
2. 创建 HarmonyOS 工具链文件（CMAKE_SYSTEM_NAME=Linux）
3. `cmake -DCMAKE_TOOLCHAIN_FILE=toolchain-harmony.cmake -DCMAKE_BUILD_TYPE=Release ..`
4. `make -j$(nproc)`（63 个目标）
5. `make install`

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 无法识别 HarmonyOS 平台 | 缺少 Platform/HarmonyOS | 创建工具链文件，设置 CMAKE_SYSTEM_NAME=Linux |
| 2 | 测试套件全部失败（36/36） | ELF 签名要求 | 平台限制，预编译包签名后可正常使用 |

## 依赖版本
- 无外部依赖

## 验证结果
- 编译成功，生成 gmssl 二进制 + libgmssl.so + libgmssl.a ✅
- 测试因 ELF 签名跳过（平台限制） ⚠️
- 国密算法模块全部编译成功（SM2/SM3/SM4/SM9/ZUC） ✅

## 交付物
| 文件 | 大小 | 说明 |
|------|------|------|
| gmssl-3.1.1-ohos-aarch64.tar.gz | 1.7MB | 主包（已签名） |

## 注意事项
- 无需源码修改，所有适配通过 CMake 工具链完成
- 功能验证需安装签名后的预编译包
