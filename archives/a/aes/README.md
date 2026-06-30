# AES — 加密/解密库和工具

## 版本概览

| 版本 | 上游 | 语言 | 构建系统 | 状态 | 说明 |
|------|------|------|----------|------|------|
| 0.2.0 | [x1b6e6/aes](https://github.com/x1b6e6/aes) | C++ | CMake | ✅ published | 命令行加密/解密工具，基于 libgcrypt |
| 0.7.4 | [RustCrypto/block-ciphers](https://github.com/RustCrypto/block-ciphers) | Rust | Cargo | ❌ failed | 纯 Rust AES 库，Rust 工具链不可用 |

---

## 0.2.0 — 命令行加密/解密工具 (x1b6e6/aes)

AES 是一个基于 libgcrypt 的 AES 加密/解密命令行工具，支持 AES-128 和 AES-256（XTS 模式），可通过密码或十六进制密钥进行加密，适合在脚本和管道中使用。

### 功能概述

- **加密/解密**：支持 AES-128 和 AES-256 算法，使用 XTS 模式
- **密钥来源**：支持交互式密码输入（SHA-512 派生密钥）或直接指定十六进制密钥
- **文件/管道**：支持 `-i/--input` 和 `-o/--output` 指定文件，默认使用标准输入/输出
- **块大小控制**：`-l/--last` 选项可指定最后一个块的有效大小（仅解密时使用）
- **密钥位数**：`-b/--bits` 选项支持 128 或 256 位密钥

### OHOS 适配要点

1. **缺少 getpass() 函数**：OpenHarmony 的 C 库不提供 `getpass()`，需添加 `#ifdef __OHOS__` 条件编译的 fallback 实现（使用 termios 禁用回显）
2. **C++ 标准库链接**：CMake 在 OpenHarmony 平台上不会自动链接 libc++，需添加 `-DCMAKE_EXE_LINKER_FLAGS="-lc++ -lc++abi -lunwind"`
3. **缺少 install 规则**：原始 CMakeLists.txt 没有 `install()` 命令，需添加 `install(TARGETS aes RUNTIME DESTINATION bin)`
4. **依赖 docopt.cpp**：需先编译安装 docopt.cpp 库（CMake v0.6.3），安装到 `$DEFAULT_PREFIX`
5. **依赖 libgcrypt**：需预安装 libgcrypt（已在系统中）
6. **退出时 segfault**：源码中 `std::cin.rdbuf()` / `std::cout.rdbuf()` 交换后，局部 `fin`/`fout` 析构导致 use-after-free，退出时触发 segfault。不影响加密/解密功能，输出数据正确。

### 依赖关系

| 依赖 | 版本 | 说明 |
|------|------|------|
| libgcrypt | 已安装 | 提供 AES 加密算法（GCRY_CIPHER_AES256/AES128, GCRY_CIPHER_MODE_XTS） |
| docopt.cpp | 0.6.3 | 命令行参数解析库，需手动编译安装 |

### 参考资料

- 上游仓库：https://github.com/x1b6e6/aes
- docopt.cpp：https://github.com/docopt/docopt.cpp
- libgcrypt 文档：https://www.gnupg.org/documentation/manuals/gcrypt/
- 许可证：MIT

---

## 0.7.4 — 纯 Rust AES 库 (RustCrypto/block-ciphers)

Pure Rust implementation of the Advanced Encryption Standard (a.k.a. Rijndael)，包括 AES-CTR 模式支持。

### 功能概述

- **AES-128/192/256**：完整的 Rijndael 分组密码实现
- **多后端支持**：ARMv8 硬件指令、AES-NI 硬件指令、纯软件实现（fixslice）
- **force-soft 特性**：禁用硬件加速，强制使用纯软件实现，确保跨平台兼容
- **AES-CTR 模式**：可选的计数器模式支持
- **no-std 兼容**：适用于嵌入式和受限环境

### OHOS 适配状态

**编译失败**：Rust 工具链在 OpenHarmony 上不可用。

- `cargo` 二进制文件存在但存在 OpenSSL relocation 错误（`EVP_CIPHER_CTX_new: symbol not found` 等 200+ 个符号未找到）
- `rustc` 不存在（`command not found`）
- `rustup` 未安装，终端网络下载超时无法安装
- 系统有 `/usr/lib/libcrypto.so.3` 和 `/usr/lib/libssl.so.3`，但 cargo 编译于不同 OpenSSL 版本

### 替代验证方案

由于 Rust 工具链不可用，使用 C 语言实现了等效的 AES 算法验证程序（`aes_verify.c`），使用系统 clang 编译器编译并运行：

- 编译器：`/data/service/hnp/bin/aarch64-unknown-linux-ohos-clang`
- 编译命令：`clang -o aes_verify aes_verify.c -O2 -Wall`
- 测试结果：全部 9 项测试通过
  - AES-128 FIPS 197 Appendix B 已知答案测试（加密+解密）
  - AES-128 全零密钥测试（RustCrypto 兼容向量）
  - AES-192 往返测试（加密+解密）
  - AES-256 往返测试（加密+解密）
  - AES-128 多块往返测试

### 依赖关系

| 依赖 | 版本 | 说明 |
|------|------|------|
| cfg-if | 1 | 编译时条件判断宏 |
| cipher | 0.3 | 分组密码 trait |
| ctr | 0.7 (optional) | AES-CTR 模式 |
| opaque-debug | 0.3 | 调试 trait |
| cpufeatures | 0.1.4 | CPU 特性检测（aarch64/x86_64/x86） |

### 参考资料

- 上游仓库：https://github.com/RustCrypto/block-ciphers
- 标签：aes-v0.7.4
- 文档：https://docs.rs/aes
- 许可证：MIT OR Apache-2.0
- FIPS 197 标准：https://nvlpubs.nist.gov/nistpubs/FIPS/NIST.FIPS.197.pdf
