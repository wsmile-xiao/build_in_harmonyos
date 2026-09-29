# squsq 3.3 用例清单与执行结果

> **原始日志说明（review-memory 规则 19）**：`*.log` 属仓库审查规则 19 定义的 **PR 禁止文件**，故本目录下的 `.log` 原件**不随 PR 提交**（保留在工作区本地）；本报告引用的日志名指本地原件，其**关键原始输出已内联于本报告**，结论可被独立复核。

上游没有自动化测试（证据见 [`upstream-test-entry.md`](upstream-test-entry.md)），因此用例由上游
`readme` 的 *Changes to SQ / USQ* 条目、`sq.c`/`usq.c` 的选项处理与 `sqio.c`/`tr2.c`/`utr.c`
实现的磁盘格式**逐条派生**，全部真实执行。

## 执行（两次独立运行，均为实跑）

| # | 运行 | 命令 | 被测产物 | 结果 | 日志 |
| - | --- | --- | --- | --- | --- |
| ① | 上游派生用例（打包产物） | `python3 test_package/test_squsq.py <conan-cache>/bin --log reports/upstream-cases-run.log` | `~/.conan2/p/b/squsq3d23f1cbc42b3/p/bin`（conan 打包产物，sha256 `08ce15af…caf5d`(sq) / `a08fbc98…dda70`(usq)） | **TOTAL 27 PASSED 27 FAILED 0 SKIPPED 0** | `upstream-cases-run.log`（本地工作区原件，按规则 19 不随 PR 提交） |
| ② | test_package 消费端验证（`conan create` 内） | `conan create archives/s/squsq/3.3 -pr:h=… -pr:b=… --build=missing --user=ohpcd --channel=stable` → `test()` → `python3 test_squsq.py <package>/bin` | conan 包 `squsq/3.3@ohpcd/stable:<pkgid>` | **TOTAL 27 PASSED 27 FAILED 0 SKIPPED 0** | `conan-create.log`（本地工作区原件，按规则 19 不随 PR 提交） 第 64–124 行（`Launching test_package` → `TOTAL`） |

统计口径：**用例总数 27 = 上游行为用例 24 + 鸿蒙特有用例 3**；通过 27、失败 0、跳过 0。

## A. 上游行为用例（24）

派生来源缩写：**R**=readme（*Changes to SQ/USQ*）、**S**=源码（`sq.c`/`usq.c` 选项与 `main()`/`obey()`）、
**F**=磁盘格式（`sqio.c`/`tr2.c`/`utr.c` 实现的 Squeeze 头）。

| # | 用例名 | 来源 | 实际执行的命令（工作目录内） | 断言要点 | 结果 |
| - | --- | --- | --- | --- | --- |
| 1 | `sq_prints_version_banner` | S `sq.c:72,96` | `sq` | stdout 含 `File squeezer version 3.3   10/29/86` 与作者署名 | PASS |
| 2 | `usq_prints_version_banner` | S `usq.c:82` | `usq` | stdout 含 `File unsqueezer version 3.3   10/29/86` | PASS |
| 3 | `sq_squeezes_file_to_SQ_extension` | R/SQ-3.0、S `sq.c:189-212` | `sq sample.txt` | 生成 `sample.SQ`；stdout 含 `sample.txt -> sample.SQ: analyzing, squeezing, done.` | PASS |
| 4 | `sq_header_has_squeeze_magic` | F `tr2.c:wrt_head`、`sqcom.h:15` | 读取 `sample.SQ` 前 2 字节 | 小端 `0xFF76`（`RECOGNIZE`） | PASS |
| 5 | `sq_header_stores_original_name` | R/SQ-读我「original file name is stored」、F | 读取 `sample.SQ` 头部 | 头部含 `sample.txt\0` | PASS |
| 6 | `usq_roundtrip_restores_bytes` | R、F | `usq sample.SQ`（先删原文件） | 还原出的 `sample.txt` 与原文逐字节相同 | PASS |
| 7 | `usq_output_name_comes_from_header` | R、F | `cp sample.SQ renamed.SQ; usq renamed.SQ` | 输出名仍取头部记录的 `sample.txt`（与 .SQ 文件名无关） | PASS |
| 8 | `sq_replaces_existing_extension` | S `sq.c:193-210`（`UNIX` 未定义 → 删除原扩展名） | `sq data.bin` | 产出 `data.SQ`，不产出 `data.bin.SQ` | PASS |
| 9 | `sq_appends_suffix_when_no_extension` | S 同上 | `sq plain` | 产出 `plain.SQ` | PASS |
| 10 | `sq_truncates_name_to_FNM_LEN` | S `sq.c:66-68` (`FNM_LEN 14`) | `sq abcdefghijklmnop.txt` | 产出 `abcdefghijk.SQ`（保留 11 字符 + `.SQ`） | PASS |
| 11 | `sq_rejects_ambiguous_name` | R/SQ-4、S `sq.c:182-187` | `sq '*.txt'` | stdout 含 `Ambiguous name *.txt ignored`，不产出文件 | PASS |
| 12 | `usq_rejects_ambiguous_name` | S `usq.c:143-148` | `usq '*.SQ'` | stdout 含 `Can't accept ambiguous name *.SQ` | PASS |
| 13 | `sq_accepts_multiple_files` | S `sq.c:99-100`（参数按序处理） | `sq m1.txt m2.txt` | 两个文件各自产出 `.SQ` 并各打印一行进度 | PASS |
| 14 | `sq_accepts_debug_option` | S `sq.c:135-139`（历史 1.5「Add debugging displays option '-'」） | `sq - dbg.txt` | 退出码 0，仍正常压缩 | PASS |
| 15 | `roundtrip_empty_file` | R/F 边界 | `sq empty.txt; usq empty.SQ` | 空文件可压缩（16 字节 `.SQ`）并还原为 0 字节 | PASS |
| 16 | `roundtrip_all_byte_values` | R「compresses a file without losing information」 | `sq bytes.bin; usq bytes.SQ`（0x00–0xFF ×4） | 8 位数据无损 | PASS |
| 17 | `roundtrip_large_multibuffer_file` | F `usq.c:315-333`（128 字节输出缓冲刷写路径） | `sq large.bin; usq large.SQ`（64 KiB 非重复数据） | 还原逐字节相同 | PASS |
| 18 | `sq_reports_missing_input` | S `sq.c:239` | `sq nosuchfile.txt` | stdout 含 `Can't open nosuchfile.txt for input pass 1` | PASS |
| 19 | `usq_reports_not_a_squeezed_file` | S `usq.c:212-215` | `usq notsqueezed.bin` | stdout 含 `notsqueezed.bin is not a squeezed file` | PASS |
| 20 | `usq_reports_missing_input` | S `usq.c:197` | `usq nosuch.SQ` | stdout 含 `Can't open nosuch.SQ` | PASS |
| 21 | `usq_preview_limits_lines` | R/USQ-1、S `usq.c:120-131,267-292` | `usq -2 lines.SQ` | 只打印前 2 行、不生成输出文件 | PASS |
| 22 | `usq_preview_whole_file_by_default` | S `usq.c:124`（`dispcnt = 65535`） | `usq - lines.SQ` | 4 行全部打印 | PASS |
| 23 | `usq_preview_formfeed_option` | S `usq.c:121-122,293-294` | `usq -F lines.SQ` | 预览内容以 `\f` 结尾 | PASS |
| 24 | `usq_preview_bad_count_is_reported` | S `usq.c:126-127` | `usq -0 lines.SQ` | stdout 含 `BAD COUNT 0`，随后按普通模式解压并写出文件 | PASS |

> 用例 11 与 readme 的 *Changes to SQ* 第 4 条（「Wildcard input filenames are accepted」）
> 存在表面冲突：本构建与 FreeBSD/NetBSD 发行版构建一样**没有定义 `UNIX` 宏**，
> 走 `#ifndef UNIX` 分支，`obey()` 对含 `*`/`?` 的名字直接打印
> `Ambiguous name … ignored` 并返回。用例断言的是**本平台实际构建出的行为**，
> 并在 `notes.md` 中记录了与发行版构建一致这一事实，未做任何源码改动。

## B. 鸿蒙特有测试用例（3，≥1 达标）

| # | 用例名 | 断言要点 | 实测证据 | 结果 |
| - | --- | --- | --- | --- |
| 25 | `ohos_binaries_are_aarch64_elfs` | 包内 `bin/sq`、`bin/usq` 均为 ELF64 小端、`e_machine == 183`(AArch64)，即面向 OHOS/aarch64 目标 | 纯 Python 解析 ELF 头（不依赖外部工具），并用 `llvm-readelf -h` 交叉印证：`Machine: AArch64` | PASS |
| 26 | `ohos_elfs_carry_ohos_identity_note` | 两个 ELF 都带 `.note.ohos.ident` 段（OHOS 工具链产物标识） | 解析节区头表得到段名列表，与 `llvm-readelf -S` 输出一致 | PASS |
| 27 | `ohos_elfs_are_codesigned` | 两个 ELF 都带 `.codesign` 段（E077：HarmonyOS 只加载带有效签名的 ELF） | 节区表内 `.codesign` 存在；`llvm-readelf -S` 输出 `[37] .codesign PROGBITS` | PASS |

CHANGELOG/readme 未涉及任何平台相关改动：**本包对上游源码零补丁**
（`patches/` 不存在，`conandata.yml` 的 `patches: {}`），
唯一的平台相关处理是构建期从 Conan profile 取编译器（R33）与打包期校验 OHOS 签名（E077）。

## C. 与 test_package 的关系

`test_package/` 运行的是**同一个** 27 例脚本（R34：真实调用被测包二进制，非空壳）。
上面第 ① 次运行与第 ② 次运行是两次独立执行，产物分别来自 conan 打包目录与
`conan create` 的 test_package 环境；两者结果一致（27/27）。
`test_package` 不能替代上游测试统计——本包上游无测试可统计，相关口径已在
`upstream-test-entry.md` 明确说明，`MANIFEST.yml` 中 `upstream_tests: []`。
