# isa-l_crypto 2.26 适配笔记

## 编译环境
- 构建系统: CMake
- 编译日期: 2026-08-06
- 编译器: clang 15.0.4 (LLVM)
- 状态: built (Conan 配方已验证, 待 PR 合入后发布)

## 编译步骤
1. 下载源码：https://api.github.com/repos/intel/isa-l_crypto/tarball/refs/tags/v2.26
2. 应用补丁：`patches/0001-aes-aarch64-gcm_common.S.patch`
3. 配置：
   ```
   cmake .. -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=ON \
     -DBUILD_TESTS=OFF -DBUILD_PERF=OFF \
     -DSAFE_DATA=ON -DSAFE_PARAM=ON \
     -DCMAKE_C_FLAGS="-fno-integrated-as"
   ```
4. 编译：`cmake --build . -j1`
5. 安装：`DESTDIR=$STAGING cmake --install .`

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SVE 汇编编译失败 | clang 集成汇编器不支持 `.req` 寄存器别名语法 | 通过 `CMAKE_C_FLAGS=-fno-integrated-as` 使用外部 GNU 汇编器 (as 2.45) |
| 2 | AES GCM 汇编编译失败 | `gcm_common.S` 中 `FN_NAME` 宏使用 `####` (双 `##`) GNU CPP 扩展，clang 预处理器不支持 | 修改 `####post` 为 `##post`，产生相同的符号名称 |
| 3 | aarch64 无 x86 SIMD | ISA-L 针对 x86 SIMD 设计，aarch64 使用 ASIMD/SVE/SVE2 | 无需修改，CMake 自动检测 aarch64 架构并使用对应汇编 |

## 关键修复补丁
### 0001-aes-aarch64-gcm_common.S.patch
- 文件: `aes/aarch64/gcm_common.S`
- 修改: `#define FN_NAME(fn,mode,post) aes_gcm_##fn##_##mode####post##aes` → `...##mode##post##aes`
- 原因: `####` (两个连续 `##` 操作符) 是 GNU CPP 扩展，clang 预处理器无法正确处理
- 安全性: `##` 产生与 GNU CPP `####` 完全相同的符号名称（如 `aes_gcm_enc_128_finalize_aes`）

## 依赖版本
- cmake 4.1.2
- clang 15.0.4
- GNU binutils (as) 2.45

## 验证结果
编译成功。libisal_crypto.so.2.25.0 (4.3MB, arm64 ELF)。
SONAME: libisal_crypto.so.2。仅链接 libc.so。

## 交付物
| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方 |
| conandata.yml | 源码 + 补丁声明 |
| test_package/ | MD5 API 消费者测试 |
| patches/0001-aes-aarch64-gcm_common.S.patch | 预处理器兼容性修复 |

## 注意事项
- aarch64 版本包含 ASIMD、SVE、SVE2 三种优化路径，通过 multibinary dispatcher 运行时选择
- 需要 `-fno-integrated-as` 标志以支持 SVE 汇编的 `.req` 寄存器别名语法
- v2.26 tag 名称不带 .0 后缀，但 CMake project version 为 2.26.0
---

**编译结束**: 2026-08-10 05:21
**最终状态**: built
