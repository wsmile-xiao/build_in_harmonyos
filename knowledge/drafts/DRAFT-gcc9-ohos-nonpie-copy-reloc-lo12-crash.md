# DRAFT-gcc9-ohos-nonpie-copy-reloc-lo12-crash

## OHOS lld AArch64 COPY 重定位 LO12 未对齐段错误（gcc/9.5.0 崩溃根因）

- **事件**: gcc/9.5.0@ohpcd/stable 功能性损坏 → gcc/9.5.0.1 路线 B 修复（2026-09）
- **现象**: 9.5.0 包所编程序在 `gcc.c-torture/execute` 的 nestfunc / printf-2 /
  fprintf-2 等用例段错误；宿主生成器构建期也可能随机崩溃
- **severity**: 2 | **category**: ohos, linking, gcc, pie, copy-relocation, aarch64

## 根因

1. 非 PIE 目标对象引用 libc 外部数据符号（`stderr` 等）→ 链接期产生
   **R_AARCH64_COPY** 重定位（符号值在可执行文件 .bss 建副本）。
2. OHOS lld 为 COPY 目标生成 LO12 字面量加载序列（16 字节对齐布置）。
3. 非 PIE 可执行文件加载基址无对齐保证 → `ldr x0, [x0, :lo12:stderr]`
   **未对齐访问 → SIGSEGV**。
4. PIE 下该类符号走 GOT（R_AARCH64_GLOB_DAT / LD64_GOT_LO12_NC），不存在此问题。

## 识别

```bash
llvm-readelf -h prog | grep Type        # ET_EXEC = 非 PIE（DYN = PIE）
llvm-readelf -rW prog | grep COPY       # 命中 R_AARCH64_COPY
```

## 修复（全链 PIE，勿走链接侧止血）

```bash
# configure 阶段
../gcc-src/configure ... --enable-default-pie --with-ld=<SDK ld.lld> ...
# configure 后、make 前：宿主生成器保持 PIE
sed -i 's/^NO_PIE_CFLAGS =.*/NO_PIE_CFLAGS =/' gcc/Makefile
sed -i 's/^NO_PIE_FLAG =.*/NO_PIE_FLAG =/'   gcc/Makefile
# （_FOR_BUILD 对同清；BUILD_NO_PIE_* 经 $(NO_PIE_*) 间接引用自动联动）
```

修复后断言：产物 `Type: DYN`、重定位仅 `RELATIVE/GLOB_DAT`、无 `COPY`；
stderr 引用程序运行正常。

## 禁止

1. **预置 `gcc_cv_c_no_fpie` / `gcc_cv_no_pie` env** —— 顶层 configure 生态不
   消费该 cache 变量，预置无效（9.5.0 实证踩坑）。
2. **只加 `--enable-default-pie` 就认为全链 PIE** —— gcc/Makefile 的
   `NO_PIE_CFLAGS`/`NO_PIE_FLAG` 会把宿主生成器剥回非 PIE，必须后置 sed。

## 关系

- caused_by / 配套: DRAFT-gcc9-ohos-lld-autocodesign-toolchain-route（lld 唯一链接器路线）
- similar_to: E2188-draft-B94A（zlib z_errmsg 非 PIC 重定位）、
  DRAFT-lld-shlib-undefined-host-contract
- 完整配方级细节见 archives/g/gcc/9.5.0.1/notes.md
