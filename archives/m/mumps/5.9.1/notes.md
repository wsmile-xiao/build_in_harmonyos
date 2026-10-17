# mumps 5.9.1 适配笔记

## 编译环境
- 构建系统: makefile（生成 Makefile.inc 驱动，无 configure）
- 编译日期: 2026-09-08
- 编译器: flang-ohos 20.1.0 (FC) + clang 15.0.4 (CC)
- 状态: built

## 编译步骤

1. 下载 MUMPS 5.9.1 源码（官方 mumps-solver.org / COIN-OR 镜像）
2. 生成 Makefile.inc：
   - FC/FL = flang-ohos 包 bin/flang
   - CC = /data/service/hnp/bin/clang
   - AR = llvm-ar cr（**必须带尾部空格**，上游 `$(AR)$@` 粘连用法）
   - LAPACK/LIBBLAS = -lopenblas（openblas/0.3.28）
   - OPTL 追加 `-resource-dir SDK/llvm/lib/clang/15.0.4 --sysroot SDK/sysroot -L SDK/llvm/lib/aarch64-linux-ohos`（链接可执行需 libclang_rt.builtins.a / libunwind.a）
   - ORDERINGSF = -Dpord（使用 MUMPS 自带 PORD 排序，禁用 metis/scotch 可选排序）
3. `make all` 构建 s/d/c/z 全部精度库 + PORD + libseq（串行 MPI 桩）
4. 上游测试：examples 目录 5 个测试程序（dsimpletest/ssimpletest/csimpletest/zsimpletest/c_example）全部运行通过

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `libseq` 编译报 AR 参数错误 | Makefile.inc AR 变量缺尾部空格，`$(AR)$@` 粘连成 `crlibmpiseq.a` | AR 值改为 `llvm-ar cr `（保留尾部空格） |
| 2 | `mumps_pord.c: space.h not found` | Makefile.inc 缺 IPORD include 路径 | 补充 `IPORD = -I$(topdir)/PORD/include/`，IORDERINGSC 含 $(IPORD) |
| 3 | examples 链接失败：libclang_rt.builtins.a/libunwind.a/-lm/-lc 找不到 | flang 默认 resource-dir（flang包/lib/clang/20）不存在，且未指定 sysroot | OPTL 追加 `-resource-dir SDK/llvm/lib/clang/15.0.4 --sysroot SDK/sysroot -L SDK/llvm/lib/aarch64-linux-ohos` |
| 4 | flang 运行报 libc++ relocation 错误 | LD_LIBRARY_PATH 未含 SDK llvm/lib 与 flang 包 lib | build 前设置 `LD_LIBRARY_PATH=SDK/llvm/lib:flang包/lib`，并清 HiShell 污染的 CFLAGS 等 env |
| 5 | conan-verify G2 失败：test_package 找不到 dmumps | conan copy 保留通配符相对路径，`"lib/*.a"` → `lib/lib/` 嵌套 | copy src 精确到源目录、dst 精确到目标目录（`*.a` + src=lib/） |
| 6 | test_package 链接缺 Fortran runtime 符号 | flang 编译的静态库需要 libFortranRuntime/Decimal/Common.a | package() 从 flang-ohos 包复制 3 个 runtime 静态库进包，package_info libs 声明 |

## 源码修改

无（未修改上游源码，仅生成构建配置文件 Makefile.inc）

## 依赖版本

- openblas/0.3.28（BLAS/LAPACK）
- flang-ohos/20.1.0（tool_requires，Fortran 编译器）

## 验证结果

```bash
# 上游测试（examples 全量，5/5 通过）
./dsimpletest < input_simpletest_real   # 解 [1,2,3,4,5] ✓
./ssimpletest < input_simpletest_real   # ✓
./csimpletest < input_simpletest_cmplx  # ✓
./zsimpletest < input_simpletest_cmplx  # ✓
./c_example < input_simpletest_real     # 解 [1,2] ✓

# conan-verify 8 道门禁
ohc-run.py conan-verify mumps 5.9.1     # G0-G4 全 PASS
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方（Makefile 构建，flang-ohos + openblas） |
| conandata.yml | 源码声明（官方 URL + sha256） |
| test_package/ | 消费者测试（真实调用 dmumps_c 求解验证） |
| lib/（包内） | libsmumps/libdmumps/libcmumps/libzmumps/libmumps_common/libpord/libmpiseq 静态库 + Fortran runtime |

## 注意事项

- MUMPS 是 IPOPT 的核心稀疏线性求解器依赖（IPOPT configure 检测 coinmumps pkg-config，链接 libdmumps 等）
- 串行模式（libseq 桩）无需真 MPI，适合 OHOS 设备
- 全部静态库（.a），consumer 链接顺序：求解器 → common → pord → mpiseq → Fortran runtime
---

**编译结束**: 2026-09-08 17:50
**最终状态**: built
