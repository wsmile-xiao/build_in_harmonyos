# ima-evm-utils 1.5 适配笔记

## 定位
- 上游 linux-integrity/ima-evm-utils v1.5，IMA/EVM 完整性度量工具套件（libimaevm 库 + evmctl 工具）
- 构建系统: autotools（configure.ac，**无预生成 configure**，需手动 autogen）
- 依赖: openssl/1.1.1w（LIBCRYPTO，PKG_CHECK_MODULES）

## 编译环境
- 构建系统: autotools（aclocal/libtoolize/autoheader/autoconf/automake 自举）
- 编译器: clang/clang++（OHOS aarch64）
- 状态: built（conan create 全流程通过，消费者 3 断言）

## 构建要点
- 手动 autogen（tarball 无 configure）：aclocal → libtoolize --force --copy --automake → autoheader → autoconf → automake --foreign --copy --add-missing
- 显式 `--build/--host=aarch64-unknown-linux-ohos`（config.guess 无法识别 HarmonyOS，0001 patch）
- `--disable-engine`：OHOS 无 OpenSSL engine 支持（configure 检测 ENGINE_init 自动降级，显式禁用更稳）
- **keyutils.h 硬性检查可选化**（0002 patch）：`AC_CHECK_HEADERS(keyutils.h, , [AC_MSG_ERROR(...)])` → 降级为 `AC_CHECK_HEADERS(keyutils.h)`（OHOS 无 libkeyutils，缺失仅影响 keyctl 相关功能，签名/验证核心用 libcrypto 不依赖 keyutils）
- 可选依赖自动缺省：tss2-esys/tss2-rc/ibmtss（TPM）、pandoc（文档）——OHOS 无，configure AC_CHECK_LIB 缺省不启用

## 测试
- 上游 tests/ 需内核 IMA/EVM 环境（evmctl 实际调用内核完整性子系统），离线无法运行 → 无自动化套件
- test_package 消费者 3 断言：imaevm.h 可包含 + libimaevm 链接 + evmctl --version 运行

## 遇到的问题与解决方案
| # | 问题 | 解决方案 |
|---|------|----------|
| 1 | config.guess 无法识别 HarmonyOS | 0001 patch：识别 aarch64:OHOS/HarmonyOS 为 linux-ohos |
| 2 | keyutils.h 硬性 AC_MSG_ERROR（OHOS 无 libkeyutils） | 0002 patch：降级为可选（AC_CHECK_HEADERS 不报错） |
| 3 | tarball 无预生成 configure | tool_requires automake/libtool + 手动 autogen |
| 4 | OHOS 无 OpenSSL engine | --disable-engine |

## 验证
- 本地 `conan create . --profile=ohos-aarch64`：`test_imaevm: OK (include/link/evmctl --version)`
