# E547 — 上游 LAPACK BUILD_INDEX64 + CBLAS 组合断裂的识别与三段修复模式

## 错误特征

按上游 `BUILD_INDEX64=ON` 等价语义构建 CBLAS64（C 端 `-DWeirdNEC -DCBLAS_API64 -DLAPACK_ILP64 -DHAVE_LAPACK_CONFIG_H` + Fortran `-fdefault-integer-8`）时依次暴露三种错误：

1. 链接期：`ld.lld: error: undefined symbol: srotg_64_`（cblas_srotg.o 引用带 `_64_` 后缀的 Fortran 符号）
2. 测试链接期：`ld.lld: error: undefined symbol: cblas_sasum`（无 `_64` 后缀，测试 C 辅助文件调用点未改名）
3. 测试运行期：`XERBLA WAS CALLED WITH SRNAME = <cblas_zher2k垃圾> INSTEAD OF <cblas_zher2k>`（zher2k/zsyr2k/gemmtr 的 error-exits FAIL）

## 触发条件

- 构建系统: 上游 make（CBLAS/Makefile + BLAS/SRC/Makefile，include 顶层 make.inc）或 CMake `BUILD_INDEX64=ON` + `BUILD_CBLAS=ON`
- 阶段: make 链接（缺陷 1）、测试构建（缺陷 2）、测试运行 error-exits（缺陷 3）
- 上游: lapack 3.12.x（INDEX64 支持只覆盖 Fortran 库路径，CBLAS 的 C 端从未在该组合下被测试）

## 根因分析

三处均为上游代码缺陷，非平台差异：

1. `cblas_f77.h` 的 `F77_GLOBAL_SUFFIX` 无条件经 `API_SUFFIX` 给 Fortran 符号加 `_64` 后缀（C 端期望 `srotg_64_`），而 Fortran 侧 `-fdefault-integer-8` 恒产出无后缀符号（`srotg_`）；带 `_64` 后缀的 ILP64 符号是 OpenBLAS `INTERFACE64` 等实现的私有惯例，参考 BLAS 没有——同一次构建的 blas64 与 cblas64 必然无法互链。
2. `CBLAS/testing/*.c` 调用点为字面无后缀名，`cblas_test.h` 无 API_SUFFIX 适配，64 位库导出 `cblas_xxx_64`，测试驱动必然 undefined symbol。
3. `c_xerbla.c` 的 `F77_xerbla` 用 14 元素栈数组构造 `"cblas_"+srname`：装不下 7 字符名（3.12 新增 ZGEMMTR 的 XERBLA SRNAME 恰为 'ZGEMMTR'，见 zgemmtr.f:275），且复制循环 `i<7` 对 6 字符名（ZHER2K/ZSYR2K）越界读 `srname[6]` 并覆盖 NUL 终止符；SRNAME 的 strcmp 回环校验依赖栈布局运气——32 位 OpenBLAS 路径靠栈上恰好为零侥幸通过，参考 BLAS 路径必失败。

## 解决方案

### 推荐方案（三段，均无平台条件编译，R8 合规）

1. `cblas_f77.h` 给 `F77_GLOBAL_SUFFIX` 加 `#ifndef` 门，配方以 `-D'F77_GLOBAL_SUFFIX(a,b)=F77_GLOBAL(a,b)'` 恒等直通：Fortran 符号全程无后缀，`cblas.h` 的 `cblas_*_64` 公开 API 命名（API_SUFFIX）不受影响；对 32 位构建为 no-op。
2. 测试 C 辅助文件调用点统一 `cblas_xxx(` → `cblas_xxx_64(`。注意：设备端 toybox sed 不支持 GNU `\b` 且静默不替换（用字符类边界并 grep 复核替换计数）；名字组必须含下划线（`[a-z0-9_]+`），否则漏 `cblas_cdotc_sub` 类名字。
3. `c_xerbla.c`：数组扩至 15 元素、复制循环以 Fortran 传入的 `srname_len` 隐藏参数界定上界（消除越界读）、循环后显式补 NUL。

补充工程要点：ILP64 参考实现用 `flang -fdefault-integer-8` 构建，生效性以 `iso_fortran_env` 的 `storage_size(1)` 探针实测（flang 20.1 输出 64）；flang 编译/链接 Fortran 主程序需完整形态 `--target=aarch64-linux-ohos --sysroot=<SDK> -resource-dir=<SDK clang resdir>` + `-lFortranRuntime -lFortranDecimal`。不要用 `objcopy --redefine-syms` 给 BLAS64 符号改名——测试主程序（Fortran）仍按无后缀名调用，改名后反向失配。

### 禁止做法

- ❌ 平台条件编译守卫（R8）
- ❌ 用 objcopy 改名 Fortran 符号迁就 C 端 mangling（测试主程序同名调用会反向失配）
- ❌ 只修 SRNAME 比对不修越界读（栈布局差异在任何目标平台都可能复发）

## 验证

```bash
# ILP64 flag 生效探针
flang -fdefault-integer-8 -o probe probe.f   # probe: print *, storage_size(1) → 64
# 全套上游测试（12 驱动）
make -C CBLAS/testing run && grep -c "END OF TESTS" *test2.out *test3.out  # 各 1
grep -cE -- "----- PASS -----|PASSED THE" *test*.out   # 合计 PASS=340 FAIL=0
```

实证：cblas64/3.12.1（OpenHarmonyPCDeveloper/build_in_harmonyos !8574，HEAD 3c65eddf）340 PASS / 0 FAIL；三段修复见 `archives/c/cblas64/3.12.1/patches/000{1,2,3}-*.patch`。

## 关联条目

- 相关: E323（conan-verify 镜像回滚——同一任务的另一缺陷面）
