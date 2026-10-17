# libsecp256k1

Optimized C library for EC operations on curve secp256k1, used by Bitcoin Core and other cryptocurrency projects.

## 功能概述

- 椭圆曲线密码学 (ECC) 操作
- secp256k1 曲线专用优化实现
- 支持 ECDSA 签名/验证
- 支持 ECDH 密钥交换
- 支持 Schnorr 签名 (taproot)
- 常量时间实现，防侧信道攻击

## OHOS 适配

- 使用 CMake 构建系统
- 强制静态链接 (R26)
- 无需外部依赖（内置 bignum 实现）

## 依赖关系

- 编译依赖：无（内置 bignum）
- 运行依赖：无

## 参考资料

- 官网：https://github.com/bitcoin-core/secp256k1
- 许可证：MIT