# OHOS 上 flang 驱动链接 Fortran 可执行文件缺目标级链接件时，应建 symlink overlay 资源目录并以 `-resource-dir` 注入

slug: `ohos-flang-driver-link-overlay`｜B【知识库扩展】主条（run liblapacke-0.3.30，Curator 判定 + Auditor CONFIRMED）｜2026-09-15

## 问题描述（规则陈述）

任何在 OHOS 设备/SDK 上以 LLVM Flang 系驱动（flang-ohos 等）**链接 Fortran 可执行文件**的构建，都会因驱动资源目录缺失目标级链接件而失败；正确解法是在构建目录内建 symlink overlay 假资源目录（文件名按 flang 期望、实体指向 SDK 同物异名），链接期以 `LDFLAGS="-resource-dir <overlay>"` 注入。不改上游源码/Makefile 逻辑，不动 flang 包与 SDK 实体。

## 根因（完整因果机理链）

- **工具实现证据**：flang 驱动 `-v` 实测链接行 =
  `ld.lld ... -pie -dynamic-linker /lib/ld-musl-aarch64.so.1 Scrt1.o crti.o <rd>/lib/aarch64-linux-ohos/crtbeginS.o <objs> -L<flang包>/lib -lFortranRuntime -lFortranDecimal -lm <rd>/lib/aarch64-linux-ohos/libclang_rt.builtins.a -l:libunwind.a -lc`。
  flang 包 `lib/` 只有 FortranRuntime/Decimal/Common.a，`<包>/lib/clang/20` 资源目录不存在；`--sysroot` 选项不被该驱动接受，`-isysroot` 也不注入链接搜索。
- **SDK 有全部实体但名字/布局不同**（clang 15.0.4 布局）：`llvm/lib/clang/15.0.4/lib/aarch64-linux-ohos/{clang_rt.crtbegin.o, clang_rt.crtend.o, libclang_rt.builtins.a}`、`llvm/lib/aarch64-linux-ohos/libunwind.a`、`sysroot/usr/lib/aarch64-linux-ohos/{Scrt1.o, crti.o, crtn.o, libc.so, libm.a}`。
- **触发命令**：任何 `flang -o <exe> <objs>` 链接。
- **失败点**：`ld.lld: error: unable to find Scrt1.o / crti.o / libclang_rt.builtins.a / libunwind.a`。
- **归类**：跨工具链资源目录布局语义差异（L1 平台/工具链层，单库发现即申报，阻塞面=链接失败）。
- 附证：OHOS flang 编译的 program 对象自带 `main` + `_QQmain` 双符号（llvm-nm 实证），**不需要 FortranMain**。

## overlay 内容（symlink，名字按 flang-20 期望）

| overlay 内名字 | 指向（SDK 实体，`$S=<sdk>/ohos/native`） |
|---|---|
| crtbeginS.o / crtendS.o | `$S/llvm/lib/clang/15.0.4/lib/aarch64-linux-ohos/clang_rt.crt{begin,end}.o` |
| libclang_rt.builtins.a | `$S/llvm/lib/clang/15.0.4/lib/aarch64-linux-ohos/libclang_rt.builtins.a` |
| libunwind.a | `$S/llvm/lib/aarch64-linux-ohos/libunwind.a` |
| Scrt1.o / crti.o / crtn.o / libc.so / libm.a | `$S/sysroot/usr/lib/aarch64-linux-ohos/` 同名 |
| libpthread.so | `$S/sysroot/usr/lib/aarch64-linux-ohos/libc.so`（musl 合并线程） |

驱动对 `-resource-dir <overlay>` 自动追加 `-L<overlay>/lib/aarch64-linux-ohos`，以上全部命中。

## 方案空间

| 层 | 方案 | 诚实权衡 |
|---|---|---|
| rec | symlink overlay 资源目录 + `-resource-dir` 注入（仅 flang 驱动的链接调用）；静态归档另以 `FEXTRALIB="<绝对路径>libFortranRuntime.a <绝对路径>libFortranDecimal.a"` 闭合（lld 弱符号归档成员按序拉取，Runtime 在前 Decimal 在后） | overlay 建在 run 私有构建目录内，10 项全 isfile 守卫，无环境副作用 |
| fallback | 仅静态库构建可退化为 CC 驱动 + `FEXTRALIB` 绝对路径闭合——配方树先例（blas/3.12.0、lapack/3.12.1）即此形态 | **Auditor 否定性实验：同族 16+（20 配方文件）先例均止步库构建、可执行链接为空白**——fallback 不是本问题的完整解；拒绝 overlay 的唯一其他路线是 NOFORTRAN，但 `Makefile.system` 机理上 `NOFORTRAN=1→C_LAPACK=1`（:379-382）、`NO_LAPACK=1→NO_LAPACKE=1`（:1455-1458），LAPACKE 类交付直接不可用 |
| forbid | ① 禁给 clang 驱动的 C 目标注入该 `-resource-dir`；② 禁改 flang 包/SDK 实体（改名/复制/替换） | ① clang 15 与 flang 20 布局/命名不同，注入后 C 目标拿不到自身头文件与 crt，直接失败并可能掩盖真实错误；② 共享设备环境污染，其他 run 不可复现 |

## 验证（自包含探针，2026-09-15 auditor-probe 实测；新 shell 逐条可跑）

```bash
P=/storage/Users/currentUser/tmp/flang-link-probe; rm -rf $P; mkdir -p $P; cd $P
printf 'program hello\n  real :: x\n  x = 2.0\n  print *, "AUDITOR_HELLO_OK", sqrt(x)\nend program hello\n' > hello.f90
F=/storage/Users/currentUser/.conan2/p/flang74dc24ecd515c/p/bin/flang-20
S=/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native
$F -c hello.f90                            # ① 编译必成功（问题只在链接）
$F -o hello_neg hello.o                    # ② 负对照：无 overlay 链接，预期失败
mkdir -p rd/lib/aarch64-linux-ohos         # ③ 建 overlay（10 项 symlink，见上表）
D=rd/lib/aarch64-linux-ohos
ln -s $S/llvm/lib/clang/15.0.4/lib/aarch64-linux-ohos/clang_rt.crtbegin.o $D/crtbeginS.o
ln -s $S/llvm/lib/clang/15.0.4/lib/aarch64-linux-ohos/clang_rt.crtend.o  $D/crtendS.o
ln -s $S/llvm/lib/clang/15.0.4/lib/aarch64-linux-ohos/libclang_rt.builtins.a $D/
ln -s $S/llvm/lib/aarch64-linux-ohos/libunwind.a $D/
for f in Scrt1.o crti.o crtn.o libc.so libm.a; do ln -s $S/sysroot/usr/lib/aarch64-linux-ohos/$f $D/; done
ln -s $S/sysroot/usr/lib/aarch64-linux-ohos/libc.so $D/libpthread.so
$F -o hello_pos hello.o -resource-dir $PWD/rd   # ④ -resource-dir 注入链接 → 成功
./hello_pos                                     # ⑤ 预期输出：AUDITOR_HELLO_OK 1.4142136
```

配对门：打通可执行链接后，GotoBLAS 系测试就地执行还差 `CROSS=0` 覆盖——见姊妹条 `DRAFT-ohos-gotoblas-cross-silent-skip`。

## 先例与增量（L2 挂钩）

- similar_to **E286**（OHOS SDK 组件/资源目录缺失 → 构建目录 overlay 桥接族）、**E064**（平台探测语义差异族）。
- **supersedes E109**（Fortran Compiler Missing）：E109 结论"OHOS 无 Fortran 编译器，只能交叉编译或等待官方支持"已过时——flang-ohos/20.1.0 conan 包可在设备全量编译 Fortran，本条补齐其可执行链接缺口，显式取代之。
- 本条为跨库工程模式（L2）：同族 16+（20 配方文件）先例均止步库构建、可执行链接为空白——本 run 为该空白的首个实证。

## 参考

- principles：P-TOOLCHAIN-001、P-BUILD-001
- 证据：run liblapacke-0.3.30（flang -v 链接行、llvm-nm 双符号、gate_verify overlay 逐字复跑 OVERLAY_OK、utest/blat/ctest/lapack-test 真实执行 5,195,617 项判定）

---

**草稿状态**：待主编审核后提升为正式条目（最终 Exxx 编号由知识库主编确认）
**最后更新**：2026-09-15
