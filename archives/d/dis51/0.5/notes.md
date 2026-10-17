# dis51 0.5 适配笔记

## 编译环境

- 构建系统：makefile（上游只有一份 5 目标 Makefile，无 configure、无 install、无 check 目标）
- 编译日期：2026-09-11
- 编译器：clang 15.0.4（`/data/service/hnp/bin/clang`，target `aarch64-unknown-linux-ohos`，musl libc）
- 平台：HarmonyOS PC / OpenHarmony aarch64，Conan profile `ci/conan/profiles/ohos-aarch64`
- 状态：built（conan-verify/W3 通过，release upload 未确认）

## 编译步骤

1. 取官方源码并校验：

   ```sh
   curl -sS -L -o dis51-0.5.tar.gz https://plit.de/asem-51/dis51-0.5.tar.gz
   sha256sum dis51-0.5.tar.gz
   ```

   上游作者原始地址（members.naspa.net 域）已失效，官方发布页（asem-51 站点）提供的
   tarball 顶层目录为 `dis51-0.5/`，共 16 个成员 = 1 个顶层目录 + 15 个文件
   （Makefile、README、NOTES、HISTORY、COPYING 与 10 个 .c/.h）。

2. 原生编译（探索与上游测试口径，见 `manifest.yaml` 的 `validation.native_build`）：

   ```sh
   cd dis51-0.5 && make -j1 CC=/data/service/hnp/bin/clang
   ```

   上游 Makefile 自带 `CFLAGS=-c -I. -Wall`，没有 install 目标；hnp clang 产出的
   `dis51` 为 PIE、`GNU_RELRO` + `FLAGS BIND_NOW`（full RELRO）、`GNU_STACK RW`。

3. 功能实测（stdin 进、stdout 出）：

   ```sh
   ./dis51 < basic.hex          # Intel HEX → 8051 汇编
   ./dis51 -l < basic.hex       # -l：列表模式，附带地址与字节
   ./dis51 16 < flow.hex        # 第二个入口地址
   ```

4. Conan 打包与验证（test_package 的 12 个用例，权威记录见 `manifest.yaml`
   的 `validation.test_package`）：

   ```sh
   python3 scripts/ohc-run.py conan-verify dis51 0.5 --project-dir <worktree>
   ```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `dis51 --version` 退出码 1，`--help` 同样不可用 | main() 只识别 `-l`，其余参数一律按入口地址 `sscanf`；两个长选项因此落空，程序继续读 stdin 并因无输入报错退出 | 补丁 0003：在读取标准输入之前拦截 `--version`/`--help` 并 `return 0`（E503 同型做法） |
| 2 | 编译告警 `format string is not a string literal [-Wformat-security]`（pass2.c:186） | `fprintf(ofile, mnemonic[opcode])` 直接用查表得到的字符串当格式串 | 补丁 0001：改为 `fprintf(ofile, "%s", mnemonic[opcode])`（与 Debian 发行版补丁同源） |
| 3 | `lbl[]` 定义与声明类型不一致，标签数超过 32767 时编号变负 | `global.h` 声明 `extern unsigned short lbl[65536]`，`global.c` 定义 `short lbl[65536]`；pass1 用 `unsigned short newlbl` 自增赋值，pass2 用 `%d` 打印 | 补丁 0002：定义改为 `unsigned short lbl[65536]`（与 Debian 发行版补丁同源） |
| 4 | 上游 Makefile 无 install 目标 | 0.5 是 2003 年的个人项目，只提供 `default/dis51/shared/clean` | `package()` 显式把 `dis51` 复制到 `bin/`、`COPYING` 复制到 `licenses/` |
| 5 | 上游没有任何测试入口 | tarball 无 test 目录，Makefile 无 check/test 目标 | 如实记为上游 0（不是 PASS 也不是 SKIP，台账见 `test_package/MANIFEST.yml`），另补 12 个消费者视角功能用例 |
| 6 | Debian 的 `dis51_0.5.orig.tar.gz` 与官方 tarball 字节不同 | 发行版重新打包：顶层目录为 `dis51-0.5.orig`，且源码里的联系邮箱是更早的 earthlink 版本 | `conandata.yml` 只锚定官方发布页 tarball 的 sha256，不用发行版重打包件做校验来源 |

## 源码修改

补丁全部是上游代码缺陷修复与 CLI 可测性补充，不含平台条件编译（无 `__OHOS__` 分支），
也不改动任何测试：

1. `patches/0001-fix-format-string-warning.patch` — pass2.c 用字面量格式串调用 `fprintf`。
2. `patches/0002-fix-signed-label-array.patch` — global.c 的 `lbl[]` 定义与 global.h 声明对齐为 `unsigned short`。
3. `patches/0003-add-version-and-help-options.patch` — main.c 在读取 stdin 之前处理 `--version`/`--help`。

三个补丁都用 `patch_ng`（Conan `apply_conandata_patches` 的实际执行路径，`strip=0`）在
纯净源码树上验证过：应用结果与探索树逐字节一致。

补丁生成方式说明：这 3 个补丁按 workflow 第 17 节登记的工具缺陷（`refresh-patch` 会静默丢补丁、
改名不同步 `conandata.yml`、`patch_generation` 正则删除 manifest 后续小节）的临时口径，
用人工 GNU diff 生成并逐条同步进 `conandata.yml`；`.build-context-dis51-0.5`（被 gitignore）
的 `BUILD_SRC_DIR`/`BUILD_SRC_ORIG_DIR` 指向两份逐字节相同的 pristine 副本（内容 = 官方
tarball + 全部 3 个补丁，不含构建产物），因此复跑 `refresh-patch --auto dis51 0.5`
实测输出「无差异，保留现有补丁」且不改动任何文件。待框架缺陷修复后回改为
`refresh-patch --auto` 生成。

## 依赖版本

无第三方依赖（只链接 C 标准库 `libc.so`）。

## 验证结果

实跑命令与结果以 `manifest.yaml` 的 `validation:` 段为权威副本；摘要：

- 上游可运行测试入口：0（`python3 -m tarfile -l dis51-0.5.tar.gz | grep -Ec '(test|check|spec)'` → 0）；
- 新增 `test_package` 功能用例：12/12 通过（`dis51 test_package summary: TOTAL=12 PASS=12 FAIL=0`）；
- 反向验证：删除包内 `bin/dis51` 后运行 `test.sh`，第一个用例即失败并以非零码退出（L1e 口径）。

## 交付物

| 文件 | 说明 |
|------|------|
| `bin/dis51` | 8051 HEX 反汇编器可执行文件（约 39KB，aarch64 OHOS musl） |
| `licenses/COPYING` | 上游 GPL-2.0 许可证原文 |

## 发现与知识

- ✅ CLI 工具缺 `--version`/`--help` 长选项会落到位置参数分支，本程序还会阻塞在 stdin 上 → 在 main() 读取输入前拦截（E503 同类）。
- ✅ 上游零测试入口的包按可审计台账记 0，替代验证用与实现独立的输入夹具加人工核对清单，并保留 L1e 破坏性反向验证（`DRAFT-cute_files-1.0.0-upstream-zero-test-ohos-validation` 同口径）。
- ✅ 同版本号的发行版重打包 tarball 与官方发布页 tarball 可能字节不同，源码 sha256 必须锚定官方发布页那一份。

## 注意事项

- dis51 的输入固定从 **stdin** 读取、汇编固定写到 **stdout**，没有 `-o`/输入文件参数；调用时需要重定向。
- 默认入口地址为 0；入口地址在默认模式下按十进制解析，`-l` 列表模式下按 `strtoul(..., 0)`（可用 `0x` 前缀）。
- 间接跳转 `JMP @A+DPTR` 无法静态跟踪（上游设计限制），跳转表后的代码会以 `DB` 数据形式输出，需要人工补入口地址再跑一次。
---

**编译结束**: 2026-09-10 23:58
**最终状态**: built
