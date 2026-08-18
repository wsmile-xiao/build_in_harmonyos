# Vampire — HarmonyOS 编译记录

## 概述

Vampire 是一款高性能一阶逻辑定理证明器，由英国曼彻斯特大学开发。它支持 TPTP 和 SMT-LIB 2 输入格式，内嵌 CaDiCaL 2.1.3 SAT 求解器。

**编译状态**: ✅ 成功（编译通过，功能验证通过）

## 编译环境

| 项目 | 值 |
|------|-----|
| 系统 | HarmonyOS aarch64 |
| 编译器 | Clang 15.0.4 |
| 构建系统 | CMake (Release, BUILD_SHARED_LIBS=OFF) |
| 依赖 | 无（内嵌 CaDiCaL 2.1.3、Minisat） |

## 编译步骤

```bash
# 1. 初始化
python3 $SKILL_ROOT/scripts/ohc-run.py init-build vampire 5.0.1
source .build-context-vampire-5.0.1

# 2. CMake 配置
cd $BUILD_SRC_DIR
mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DBUILD_SHARED_LIBS=OFF

# 3. 编译（约 944 秒）
make -j1

# 4. 安装
make install DESTDIR=$TEST_PREFIX
```

## 验证结果

| 测试项 | 结果 |
|--------|------|
| vampire --version | ✅ Vampire 5.0.1 (Release build) + CaDiCaL 2.1.3 |
| 二进制格式 | ✅ ELF 64-bit ARM aarch64, static |
| 定理证明: p(X)=>p(X) | ✅ SZS Theorem, 0.001s |
| 定理证明: 苏格拉底三段论 | ✅ SZS Theorem, 0.002s |
| Conan 验证 (8道门禁) | ✅ 全部 PASS |

## 版本列表

| 版本 | 状态 | 日期 |
|------|------|------|
| 5.0.1 | published | 2026-06-29 |
