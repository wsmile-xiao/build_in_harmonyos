# libequihash

Equihash 是一种基于广义生日难题的非对称内存困难型工作量证明算法（Alex Biryukov / Dmitry Khovratovich 设计，Zcash 采用）。
本仓库适配的是 Stefan Marsiske 维护的生产向分支（`stef/equihash`），在原始实现基础上清理了基准与调试输出，
封装为库并提供 C API 与 Python 绑定。

## 功能概述

- 内存困难型 PoW 求解（参数 N/K 可调时间与内存复杂度）
- 快速验证：验证仅需 2^K 次哈希与异或
- 公开 C API（`equihash.h`）：
  - `solsize(n, k)` — 计算给定参数下解（含 nonce）的字节数
  - `solve(n, k, seed, seed_len, csol, csol_len)` — 求解，成功返回 1
  - `verify(n, k, seed, seed_len, sol, sol_len)` — 验证，成立返回 1
- 底层哈希使用 libsodium 的 `crypto_generichash`（Blake2b）

## OHOS 适配要点

- **构建系统**: 纯 Makefile（无 configure 脚本）
- **依赖**: 唯一外部依赖 `libsodium/1.0.22`（conan requires，非系统预编译包）
- **产物**: `lib/libequihash.a`（默认静态）或 `lib/libequihash.so`（`shared=True`，附 `libequihash.so.0` 程序链接名）+ `include/equihash.h`
- **补丁**: 仅一处可移植性补丁（`ar` 硬编码改为 `$(AR)` 变量），无平台宏
- **测试**: 上游无测试套件；test_package 用小参数（N=24/K=3）真实调用 `solsize`/`solve`/`verify` 共 4 项断言，
  含合法解接受与篡改解拒绝的正反向验证
- **许可证**: CC0-1.0
