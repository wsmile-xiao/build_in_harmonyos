# dwgsim 0.1.14 适配笔记

## 编译环境
- 构建系统: makefile（上游为裸 GNU Makefile，无 configure）
- 编译日期: 2026-10-08
- 编译器: clang 15.0.4（aarch64-linux-ohos）
- 状态: built

## 编译步骤

1. **W0 依赖预检**：`ci/scripts/preflight_check.sh dwgsim/0.1.14` → 预检通过；`conan download "zlib/1.3.1" -r=ohpcd --only-recipe` 取到 revision `2ee7c0eeb8f4dfef8982d0c5c1551a61`，唯一三方依赖 zlib 已发布。
2. **取源**（两份官方归档，均来自 codeload.github.com）：
   - `https://codeload.github.com/nh13/DWGSIM/tar.gz/refs/tags/dwgsim.0.1.14`
     sha256 `a974a253bf6bcd5a2162f9ebc6c78c56a29c541850f375a45ddb2b649574ce1b`，2206455 字节；
   - `https://codeload.github.com/samtools/samtools/tar.gz/28391e5898804ce6b805016d8c676fdf61442eb3`
     sha256 `b17bc6564eef101aeefc2d572347f7141bdb8eb5cdaa81725fdd768cf80d1a2b`，558464 字节，解到 `<src>/samtools/`。
3. **编译**（在 source_folder 内，全部变量来自命令行而非 shell 环境，R33）：

   ```
   make CC='<profile 的 c>' CFLAGS='-g -Wall -O3 -fPIE -Wl,-z,relro,-z,now -I<zlib>/include -L<zlib>/lib' DFLAGS='-D_FILE_OFFSET_BITS=64 -D_LARGEFILE64_SOURCE -D_USE_KNETFILE -DPACKAGE_VERSION=\"0.1.14\"' INCLUDES='-I.' -j2 dwgsim dwgsim_eval
   ```

4. **上游测试**：`bash testdata/test.sh`（与 `make test` 同一脚本，仅替换掉不存在的 `/bin/bash` 解释器）。
5. **打包**：`package()` 把 `dwgsim`、`dwgsim_eval` 装到 `bin/`、`LICENSE` 装到 `licenses/`，OHOS 上就地签名。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | tag 归档解出来 `samtools/` 是空目录，`make` 在 `lib-recur` 处报 `No rule to make target`；`dwgsim_eval` 也拿不到它直接链接的 19 个 `samtools/*.o` | `.gitmodules` 声明 samtools 为子模块，codeload 的 tag 归档不含子模块内容（上游 INSTALL 明确要求 `git submodule update`） | 从该 tag 的 git tree 读出 gitlink commit `28391e5898804ce6b805016d8c676fdf61442eb3`，按此固定 commit 取 samtools 官方归档作第二源，`source()` 解到 `samtools/`；两份源都写进 conandata.yml 并带真实 sha256 |
| 2 | 裸跑 `make`（默认目标 `all-recur`）在 samtools 子目录报 `unable to find library -lcurses` | 上游 Makefile 默认目标会递归 `make all`，把 ncurses 版 samtools 主程序一起编 | 显式目标 `make dwgsim dwgsim_eval`：仍会走 `lib-recur`（`libbam.a` + DWGSIM 对象），但不编带 curses 的 samtools 主程序；既不需要 ncurses，也不把 samtools 装进包内 |
| 3 | `src/dwgsim_opt.c:95: error: invalid suffix '.14' on floating constant`（另一形态是 `expected expression`） | `PACKAGE_VERSION` 必须作为带引号的 C 字符串进预处理。上游靠 Makefile 变量 `PACKAGE_VERSION="0.1.14"` 自带的双引号，经两层 shell 处理后正好落成 `\"0.1.14\"`；从命令行直接喂裸 `"0.1.14"` 会被 shell 吃掉引号，喂 `\\\"…\\\"` 又会把反斜杠带进宏 | 命令行 DFLAGS 写 `-DPACKAGE_VERSION=\"0.1.14\"`（单引号包裹、反斜杠原样保留），配方 shell 再把 `\"` 还原成字面双引号 ⇒ 宏值为字符串 `"0.1.14"`；实测 `dwgsim` 打印 `Version: 0.1.14` 正确 |
| 4 | `make test` 报 `make: /bin/bash: No such file or directory`（exit 127） | 上游 `test:` 目标写死 `/bin/bash testdata/test.sh`，OHOS 无 `/bin/bash` | 不改上游脚本，`build()` 里直接用 PATH 中的 `bash` 执行同一个 `testdata/test.sh`（仅换解释器，脚本内容零改动，R51 逐项说明） |
| 5 | `-lz` 可能被系统同名 `libz.so` 顶替，或找不到 | 上游链接行是 `$(CC) $(CFLAGS) -o $@ ... -lz`，没有 LDFLAGS 可挂 | 把 `self.dependencies["zlib"]` 包目录的 `include`/`lib` 绝对路径同时并入 `CFLAGS`（该变量同时用于编译与链接）；conan zlib 默认静态，只产出 `libz.a`，不污染 `/lib`（R26） |

## 源码修改

无补丁：`patches/` 为空，源码零改动，所有差异都通过 make 变量与解释器选择解决（因此补丁里不含任何平台宏，R8/PF5）。

## 依赖版本

| 包 | 版本 | 用途 |
|---|---|---|
| zlib/1.3.1 | 配方 revision `2ee7c0eeb8f4dfef8982d0c5c1551a61` | `dwgsim` / `dwgsim_eval` / 内嵌 samtools 的 `-lz` |
| samtools（源码） | 上游 gitlink `28391e5898804ce6b805016d8c676fdf61442eb3` | 提供 `libbam.a` 及 `dwgsim_eval` 直接链接的 19 个对象 |

## 上游测试清点（R51）

- **静态清点**：上游只有一个测试入口 `testdata/test.sh`（`make test` 调它）。仓库内无 ctest/pytest/configure 测试框架；`.github/workflows/testing.yml` 也只有 `make` + `make test` 两步。
- **实跑**：`bash testdata/test.sh` → `rc=0`。脚本以 `-z 13 -N 10000` 从 `samtools/examples/ex1.fa` 生成 10000 条读段，再对 `bfast.fastq.gz` / `bwa.read1.fastq.gz` / `bwa.read2.fastq.gz` / `mutations.txt.gz` / `mutations.vcf.gz` 共 **5 个断言**逐一 `diff -q`，**5/5 通过**，无 skip。
- **`dwgsim_eval` 未被上游测试覆盖**：`testdata/test.sh` 全程不调用它，其评估路径需要外部比对器产出的 SAM/BAM，本包不附带比对器。消费者测试里对它的覆盖是执行 `dwgsim_eval -h` 并断言用法横幅（二进制可执行、参数解析正常）。
- **消费者测试（test_package）**：7 条断言 —— dwgsim 退出码 0（1）、5 个输出文件非空（5）、dwgsim_eval 用法横幅（1）。

## 验证结果

```bash
bash ci/scripts/preflight_check.sh dwgsim/0.1.14   # [OK] 预检通过（无依赖需要检查）
conan download "zlib/1.3.1" -r=ohpcd --only-recipe  # rc=0，revision 2ee7c0eeb8f4dfef8982d0c5c1551a61
bash testdata/test.sh                               # rc=0，5/5 diff 通过
./test_dwgsim <bindir>/dwgsim <bindir>/dwgsim_eval  # ALL TESTS PASSED
```

## 能力墙判定

**甲（无被拦能力）**：对 DWGSIM 源树与 samtools 子树按 `mmap` / `/dev/` / `setuid` / `ptrace` / `seccomp` / `io_uring` / `AF_PACKET` 逐项 grep，**命中 0**；构建为普通用户态 clang + GNU make，仅依赖 libc/zlib/pthread/libm，无设备节点、无特权调用、无大内存 mmap 依赖。实跑 `-N 10000` 全量上游测试在设备上正常完成（约 10 秒量级）。
---

**编译结束**: 2026-10-08 18:04
**最终状态**: built
