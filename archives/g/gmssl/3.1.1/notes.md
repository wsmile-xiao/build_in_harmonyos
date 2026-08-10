# gmssl 3.1.1 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-08-06
- 编译器: clang 15.0.4 (HarmonyOS Native)
- 状态: built (Conan 配方验证通过，待 CI upload)

## 编译步骤
1. 下载 GmSSL v3.1.1 源码 (GitHub archive URL)
2. `cmake -DCMAKE_C_COMPILER=clang -DCMAKE_C_FLAGS="-fPIC -O2" -DCMAKE_INSTALL_PREFIX=$PREFIX -DCMAKE_BUILD_TYPE=Release -DCMAKE_SYSTEM_NAME=Linux ..`
3. `make -j4`（63+ 个目标）
4. `make install DESTDIR=$TEST_PREFIX`

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 无法识别 HarmonyOS 平台 | 缺少 Platform/HarmonyOS | Conan OHOS profile 自动映射 CMAKE_SYSTEM_NAME=HarmonyOS，CMakeToolchain 处理 |
| 2 | conan get() 下载失败 (BadZipFile) | GitHub API URL 返回 302 重定向 | 使用 GitHub archive URL: https://github.com/guanzhi/GmSSL/archive/refs/tags/v3.1.1.tar.gz |
| 3 | getentropy 平台检测 | OHOS 支持 getentropy | check_symbol_exists 正确检测到 getentropy，使用 rand_unix.c |

## 依赖版本
- 无外部依赖

## 验证结果
- 编译成功，生成 gmssl 二进制 + libgmssl.so + libgmssl.so.3 + libgmssl.so.3.1 ✅
- 36/36 测试全部通过 ✅
- 国密算法模块全部编译成功（SM2/SM3/SM4/SM9/ZUC） ✅
- Conan 配方验证通过 (G0-G4 + L2/L4/L5) ✅

## 交付物
| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方 |
| conandata.yml | 源码 + SHA256 |
| test_package/ | Conan L1 测试 (SM3 digest 验证) |
| commands.json | 命令行工具声明 (gmssl 二进制) |

## 注意事项
- 无需源码修改，所有适配通过 Conan OHOS profile + CMakeToolchain 完成
- gmssl 非 system 同名库，默认动态链接 (shared=True)
- 构建产物包含可执行文件 (gmssl)，已声明 commands.json
---

**编译结束**: 2026-08-06 14:37
**最终状态**: built
