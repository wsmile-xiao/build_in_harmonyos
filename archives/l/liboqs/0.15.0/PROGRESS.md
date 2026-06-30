# liboqs 0.15.0 — 编译进度

> 档案创建时间: 2026-04-29
> 最后更新: 2026-04-29
> 状态: ✅ built

## 一、基本信息
| 项目 | 值 |
|------|-----|
| 软件 | liboqs (Open Quantum Safe) |
| 版本 | 0.15.0 |
| 构建系统 | CMake |
| 编译器 | clang |
| 源码路径 | https://github.com/open-quantum-safe/liboqs |

## 二、编译阶段

### Phase 1: 环境准备 ✅
- [x] ohc-run.py init-build 完成
- [x] OpenSSL 1.1.1w 依赖安装

### Phase 2: 编译 ✅
- [x] CMake 配置完成
- [x] make 编译完成（100%）
- [x] make install DESTDIR 完成

### Phase 3: 测试验证 ✅
- [x] test_aes: 通过
- [x] example_kem (ML-KEM-768): 通过
- [x] example_sig (ML-DSA-65): 通过

### Phase 4: 预编译包制作 ✅
- [x] 预编译包生成: liboqs-0.15.0-ohos-aarch64.tar.gz (7.29MB)

## 三、关键修复

| 问题 | 解决方案 |
|------|---------|
| CMake 不识别 HarmonyOS | 设置 CMAKE_SYSTEM_PROCESSOR=aarch64 |
| 架构不支持警告 | OQS_PERMIT_UNSUPPORTED_ARCHITECTURE=ON |

## 四、支持的算法

**密钥封装机制 (KEM)**:
- ML-KEM (Kyber): 512, 768, 1024
- BIKE, Classic McEliece, FrodoKEM, NTRU

**数字签名算法**:
- ML-DSA (Dilithium): 44, 65, 87
- Falcon, SPHINCS+, Mayo, CROSS

## 五、产物
- liboqs.a (6.96MB) - 静态库
- 头文件: oqs/*.h (27个)
- CMake 配置文件