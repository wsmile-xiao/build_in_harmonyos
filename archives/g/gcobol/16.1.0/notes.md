# gcobol 16.1.0 适配笔记（HarmonyOS PC · GCOBOL 前端 = GCC 16 COBOL 编译器）

## 状态：真机完整构建 + 上游 cobol.dg 全量 463/464 通过（FAIL 0）

真机上已完成 `make all-gcc`（产出 `cobol1`/`gcobol`/`cc1`）、
`all-target-libgcc`、手动 clang++ 构建 `libgcobol`，并用 gcobol 驱动
完整走通 COBOL 程序「编译 → 链接 → 签名 → 运行」，`COMPUTE 10**2` 输出
`0000000100`（= 100）。上游 `gcc/testsuite/cobol.dg/` 464 项逐项真实
编译+链接+签名+运行：PASS 450 + XFAIL 13 + FAIL 0 + SKIP 1（`-static`
环境限制）。所有适配点已集成进 `conanfile.py`。

## 一、上游与性质

- 上游：GCC 16 的 COBOL 语言前端（GCOBOL），源码在 `gcc.git` 的 `gcc/cobol/` 目录。
- 产物：`cobol1`（COBOL 前端编译器）、`gcobol`（编译器驱动）、依赖 `libgcobol`（运行时库，已单独适配 PR #11888）。
- 许可证：`GPL-3.0-or-later WITH GCC-exception-3.1`。
- 版本：Conan 包版本取 `16.1.0`，与上游 `gcc-16.1.0.tar.xz` 一致。

## 二、W0 依赖结论

| 依赖 | 类别 | 版本/来源 | 结论 |
|------|------|----------|------|
| gcc 16.1.0 源码 | 构建 | `gcc-16.1.0.tar.xz` | ✅ |
| gmp/mpfr/mpc | 构建 | 6.3.0 / 4.2.2 / 1.3.1 | ✅（in-tree） |
| clang/clang++ | 构建编译器 | OHOS SDK | ✅ |
| libgcobol 源码 | 构建 | gcc 源码树内 libgcobol/ | ✅ |
| libxml2 | 运行时依赖 | conan `libxml2/2.15.3` | ✅（同 libgcobol 单独适配） |

## 三、OHOS 特有适配点（完整清单，已全部集成 conanfile.py）

1. **config.sub 注入 ohos triplet**（E122）：`aarch64-linux-ohos → aarch64-unknown-linux-ohos`。
2. **所有 configure 的 mktemp → `$TMPDIR`**（E011/E052/E060，36 个 configure）：TMPDIR 用 tmpfs `/data/storage/el2/base/cache`。
3. **move-if-change / gmp m4-ccas / mpfr get_patches.sh / libgcc mkheader.sh 通过 `$(SHELL)`**（E046/E087）。
4. **libgcc unwind_h 去掉 `sh $(SHELL)` 双重 shell**。
5. **CONFIG_SHELL=/bin/sh**（重启后 HMDFS 上 bash getcwd 失败）。
6. **CC/CXX 显式 clang**（configure 会找到无执行权限的 cc）。
7. **lexio.cc stdio_filebuf shim**：OHOS libc++ 无 `ext/stdio_filebuf.h`，内联 minimal write-only shim。
   **必须 `setvbuf(_file,NULL,_IONBF,0)` unbuffered**：输出临时文件靠 re-map fd 读回，
   若走 stdio 缓冲且程序无 COPY（不触发 `out.flush()`），缓冲内容丢失 → 词法器看
   到空文件 → "syntax error, unexpected end of file, expecting IDENTIFICATION DIVISION"。
   这是本次真机诊断出的关键 bug。
8. **defaults.h stack-check 默认宏无条件化**（STACK_CHECK_MAX_VAR_SIZE 等）。
9. **tm.h 补 `#include "insn-flags.h"`**（gen_nop 等声明只在 insn-flags.h）。
10. **gcc/Makefile PICFLAG=-fPIC, LD_PICFLAG=-no-pie**（stderr copy relocation 对齐，
    不能传 make 命令行，否则 leak 到 fixincludes 递归）。
11. **symbols.cc symbol-table 临时文件**：`tmpfile()` 在 HMDFS 失败 → 走
    `GCOBOL_TEMPDIR` + `mkstemp`（与 lexio.cc 一致）。
12. **libgcc gthr-posix.h**：`pthread_cancel` → `#if !defined(__BIONIC__) && !defined(__OHOS__)`，
    `GTHR_ACTIVE_PROXY pthread_create`（`__OHOS__` 经 `CFLAGS_FOR_TARGET=-D__OHOS__` 提供）。
13. **libgcc lse-init.c**：`__getauxval`（glibc 内部）→ `getauxval`（musl 公开导出）。
14. **libgcobol.cc**：`_Float32`/`_Float64` → `float`/`double`（libc++ 不认识 C23 类型）。
15. **顶层 Makefile 移除 libstdc++-v3**（`TARGET_CONFIGDIRS` + `configure-target` 依赖，
    gcobol 不需要 C++ 标准库，其 configure 会 "cannot run C compiled programs"）。
16. **libgcobol 用 clang++ 手动构建**（gcobol 构建无 cc1plus）：`--build/--host=aarch64-unknown-linux-musl`，
    `-nostdinc++ -I libcxx-ohos/include/c++/v1`，`-lclang_rt.builtins`，libxml2 从 conan 依赖取。
17. **动态链接器 musl**：OHOS 是 musl，GCC 默认动态链接器是 glibc 的
    `/lib/ld-linux-aarch64.so.1`（不存在）。gcobol 驱动 wrapper 加 `-mmusl`
    切到 `/lib/ld-musl-aarch64.so.1`。
18. **gcobol 驱动 wrapper**（package 后安装）：重定位 GCC_EXEC_PREFIX +
    `-mmusl` + `-B sysroot/usr/lib/$target`（crt1/crti/crtn）+
    `-B pkg/lib/gcc/$target/$version`（libgcc/crtbegin）+ `-D__availability__(...)=` +
    `-isystem sysroot/usr/include/$target`，并对 `-o` 链接输出的 ELF 补 `.codesign`。
19. **ELF 签名**：OHOS 动态链接器只加载带 `.codesign` 的 EXEC/DYN。
    package() 对全部 ELF（含 libgcobol.so）签名；wrapper 对用户链接输出签名。
20. **genapi.cc `_tolower` → `TOLOWER`**：`psa_global()` 用 glibc 无条件
    `c+0x20` 的 `_tolower`，把 `_`(0x5F) 误转成 0x7F(DEL)，生成的
    `__ggsr__<name>` 符号名含 DEL → aarch64 GNU as 2.45 拒绝（`bad expression`）。
    改 GCC safe-ctype 查表 `TOLOWER`（非字母原样返回）。
21. **musl iconv 缺 CP1140（EBCDIC）**：musl 的 iconv 不支持 `CP1140`，
    `iconv_open("CP1140",…)` 返回 -1 后仍被调用 → cobol1 段错误 / "cannot
    convert from CP1252 to CP1140"。修复 `charmaps.h` charmap_t 构造函数、
    `charmaps.cc` `__gg__iconverter`、`symbols.cc` reencode/encode 的
    `iconv_open` 失败检查，回退 gcobol 内置 `__gg__cp1252_to_cp1140_values`
    /`__gg__cp1140_to_cp1252_values` 映射表，并对 `cp1140↔任意编码` 做两步
    转换（cp1140→CP1252 内置表→iconv，或反向）。覆盖 `-fexec-charset=cp1140`
    与 `special-names locale cp1140` 的上游测试。
22. **musl `powl` 精度不足**：`powl(10,31)` 在 musl ≈ 9.9999e30（非精确
    10^31），`libgcobol.cc` `float128_to_int128` 用它缩放 intermediate 值 →
    `FUNCTION MAX/MIN` 返回 7.9999…、`DECIMAL-POINT` 返回 00,49。改
    `value *= (GCOB_FP128)__gg__power_of_ten(*rdigits)`（int128 10 次幂表，
    精确）。

## 三·补、上游 cobol.dg 全量验证结果（真机）

真机无 dejagnu/runtest/expect，无法直接 `make -C gcc check-cobol`；用 dg
驱动脚本复刻 `dg-do run/compile`、`dg-output`（顺序正则）、`dg-output-file`
（逐行精确）、`dg-error`、`dg-xfail-run-if`/`dg-do run { xfail }` 语义，在
完整 build-tree 上逐项真实「编译 → 链接 libgcobol+libxml2+musl → ELF 签名 →
运行」并比对断言：

| 结果 | 数量 | 说明 |
|------|-----:|------|
| PASS | 450 | 正常 run + compile（含 error-1/typo-1 预期报错） |
| XFAIL | 13 | `fail.cob` + 越界/`STOP RUN ERROR`/overflow 检查，按预期失败，0 XPASS |
| FAIL | 0 | — |
| SKIP | 1 | `_-static__compilation.cob`：OHOS libxml2 只有 `.so` 无 `libxml2.a`，完全静态链接环境不支持 |
| **合计** | **464** | **通过率 463/464** |

## 四、完整构建序列（conanfile.py build()）

1. configure（`--enable-languages=c,cobol --disable-bootstrap --disable-shared`，TMPDIR=tmpfs）
2. patch tm.h + gcc/Makefile（PICFLAG/LD_PICFLAG）
3. `make all-gcc`（clang 编译 cobol1/gcobol/cc1）
4. 删除 gcc/{as,collect-ld,nm} 包装脚本（HMDFS 无 exec 位）
5. patch 顶层 Makefile 移除 libstdc++-v3
6. `make all-target-libgcc`（xgcc 编译，CFLAGS_FOR_TARGET=-D__OHOS__）
7. clang++ 手动 configure+make libgcobol（libxml2 从 conan 依赖取）

## 五、已知未决问题

- **`-static` 完全静态链接（1 个上游测试 SKIP）**：`_-static__compilation.cob` 用
  `-static` 链接 libgcobol.a，OHOS 的 libxml2 依赖只有 `.so`、无 `libxml2.a`，
  完全静态链接无法解析 libxml2 符号。此为依赖链环境限制，非 gcobol 代码 bug，
  如实记为 SKIP。
- **完整 GCC 构建时长 > CI 默认窗口**：`all-gcc`（含 cobol1 链接 libcommon.a）
  本身接近/超过默认 3600s 窗口。真机手动构建是持久化 build tree 多步完成；
  公共 CI 设置本 PR 不改动（按规范），完整构建/超时策略由平台 CI 评审决定。

## 六、下一步

1. issue 编号：待补（任务大厅建号后回填关联 Issue）。
2. 提交后由平台 AI Review + CI 复核；路径 C 仅申请候选确认。
