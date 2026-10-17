# coinor-ipopt 3.14.19 适配笔记

## 编译环境
- 构建系统: autotools（configure + make）
- 编译日期: 2026-09-08
- 编译器: clang 15.0.4（/data/service/hnp/bin/clang、clang++）
- 状态: built

## 依赖
- mumps/5.9.1（稀疏对称线性求解器，核心功能硬依赖；本仓新适配依赖项）
- openblas/0.3.28（BLAS/LAPACK，configure 硬依赖）

## 编译步骤

1. 源码：https://github.com/coin-or/Ipopt/archive/refs/tags/releases/3.14.19.tar.gz
2. 平台适配（3 个补丁）：
   - config.guess：aarch64:HarmonyOS → aarch64-unknown-linux-ohos
   - config.sub：支持 linux-ohos triplet（basic_os 识别 / OS 列表 / kernel-os 验证）
   - configure：tmp 目录创建改 mkdir（HMDFS 上 mktemp 0700 目录不可写）
3. configure 关键参数：
   - `--with-lapack-lflags=-L<openblas>/lib -lopenblas`
   - PKG_CONFIG_PATH 指向生成的 coinmumps.pc（configure 经 `AC_COIN_CHK_PKG(Mumps,...)` 检测 MUMPS）
4. make -j1 → make install

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.sub 不识别 aarch64-unknown-linux-ohos | 上游 config.sub 无 OHOS | 补丁支持 linux-ohos（basic_os/OS 列表/kernel-os 验证三处） |
| 2 | config.status 创建临时目录失败 | HMDFS 上 mktemp 0700 目录不可写（E046） | configure 补丁：tmp 目录改用 mkdir |
| 3 | 链接缺 builtins 符号（__udivti3 等） | 共享库内 128 位运算需 compiler-rt builtins，clang 默认不带 | LDFLAGS 加 `-L SDK/clang/15.0.4/lib/aarch64-linux-ohos -lclang_rt.builtins` |
| 4 | MUMPS 检测失败 / mumps_compat.h 找不到 | coinmumps.pc 中 `$${prefix}` 双美元未展开 | conanfile generate() 生成单美元 `${prefix}` 的 coinmumps.pc |
| 5 | test_package 运行时 libc++ 符号缺失 | runenv LD_LIBRARY_PATH 中父环境带空格 `/system/lib64` 被跳过，bundle 目录先命中不匹配 libc++ | package_info 用 `prepend_path` 把干净 `/system/lib64` 置前（实测验证） |
| 6 | test.cpp QuadNLP 抽象类 | 误写 `get_final_solution`，应为 `finalize_solution` 纯虚方法 | 修正签名（SolverReturn + IpoptData/IpoptCalculatedQuantities） |

## 源码修改

3 个平台补丁（patches/0001-config.guess.patch、0002-config.sub.patch、0003-configure.patch），其余为配方生成配置。

## 依赖版本

- mumps/5.9.1（制品仓已发布）
- openblas/0.3.28（制品仓已发布）

## 验证结果

```bash
# 上游测试（test/run_unitTests，6/6 通过）
./hs071_cpp       # PASS
./hs071_c         # PASS
./emptynlp        # PASS
./getcurr         # PASS
./parametric_cpp  # PASS（sIPOPT）
./redhess_cpp     # PASS（sIPOPT）
# hs071_f SKIP（COIN_HAS_F77 平台限定，OHOS 无 F77）

# conan-verify 8 道门禁
ohc-run.py conan-verify coinor-ipopt 3.14.19   # G0-G4 + L2/L4/L5 全 PASS
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方（autotools，mumps + openblas 依赖） |
| conandata.yml | 源码声明（官方 URL + sha256 + 3 补丁） |
| patches/ | config.guess / config.sub / configure 平台补丁 |
| test_package/ | 消费者测试（真实调用 IpoptApplicationFactory + OptimizeTNLP 求解二次问题） |

## 注意事项

- IPOPT 稀疏线性求解器为**核心功能硬依赖**（源码实证：无求解器时 defaultsolver 回退 custom=NULL，上游测试全失败）
- 运行期 libipopt.so 依赖系统 libc++_shared.so，须将干净 `/system/lib64` 排在 LD_LIBRARY_PATH 最前
---

**编译结束**: 2026-09-10 14:42
**最终状态**: built
