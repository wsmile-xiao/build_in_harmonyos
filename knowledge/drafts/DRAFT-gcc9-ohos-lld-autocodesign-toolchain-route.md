# DRAFT-gcc9-ohos-lld-autocodesign-toolchain-route

## OHOS 编译器工具链路线：ld.lld 链接即签名（gcc/9.5.0.1 路线 B）

- **事件**: gcc/9.5.0.1@ohpcd/stable 适配，替代 9.5.0 的 GNU ld + 全链手动签名
- **severity**: 2 | **category**: ohos, linking, codesign, gcc, lld, conan

## 核心事实

1. OHOS 内核只加载带 `.codesign` 节的 ELF。
2. **SDK ld.lld 每次链接自动附加 .codesign**（产物可直接运行）。
3. **GNU ld (binutils 2.45) 不签名** → 产物 execve 被拒（rc=126）。

## 路线对比

| 维度 | 路线 A（9.5.0） | 路线 B（9.5.0.1） |
|------|----------------|-------------------|
| 链接器 | GNU ld | SDK ld.lld（--with-ld 烘焙 + LD/LD_FOR_TARGET） |
| 签名 | CC 包装器 + `_sign_elf_tree` 全树 binary-sign-tool | LLD 链接即签名，零工具 |
| 包装器 | 每驱动 ~60 行签名逻辑 | 薄 exec 包装器（仅 -B/-isystem/-D 前缀） |
| 脆弱性 | 漏签即拒跑，随机中断 | 签名面收敛到链接器一处 |

## 配方要点

1. `--with-ld=<SDK ld.lld realpath>`：顶层 configure 不消费但经 baseargs 原样转发
   给 gcc/configure → `DEFAULT_LINKER` 烘焙进 gcc.c/collect2（对 "ld" 直取绝对路径）。
   gcc/configure 校验 `-v | grep GNU`——lld 报 "compatible with GNU linkers" 可过。
2. `LD` / `LD_FOR_TARGET` 环境补注。
3. **all-gcc 后 fail-fast 断言**：`xgcc -print-prog-name=ld` 必须等于烘焙路径。
4. 包内 `bin/gcc` 包装器：lld 可用性检查 + SDK llvm/lib 的 LD_LIBRARY_PATH 防御导出。
5. **拒绝 `-fuse-ld*` 入 CC**：`-fuse-ld=bfd` 会让 clang 对 -E 探测输出
   unused-argument 警告 → autoconf conftest.err 非空 → HAVE_LIMITS_H 误判 no →
   limits.h 缺失链式崩溃；且同时禁用 lld 自动签名。

## 禁止

1. `-fuse-ld=bfd` 类参数注入 CC（见上）。
2. 把"链接后 binary-sign-tool 全树补签"当主路线——构建期新产生的宿主程序
   （genattr/gencondmd 等）漏扫即拒跑，失败位置随机（9.5.0 实证）。

## 关系

- causes: DRAFT-gcc9-ohos-nonpie-copy-reloc-lo12-crash（lld 路线是 COPY 崩溃修复的载体）
- caused_by: DRAFT-ohos-elf-skip-strip-codesign、DRAFT-E077B-ohos-sdk-autocodesign-invalid
- similar_to: DRAFT-asmc-native-arm64-host-x86-64-elf-ldlld、
  DRAFT-aspectc-double-bootstrap-libstdcxx-abi-codesign
- 完整细节: archives/g/gcc/9.5.0.1/notes.md
