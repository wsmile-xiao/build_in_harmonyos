# 上游 30 个 C 测试程序逐程序 `PASS (N tests)` 原始输出（逐字留档）

> **为什么不是 `.log`**：`.gitcode/review-memory.md` 规则 19 把 `*.log` 明列在「PR 中禁止的
> 文件」内——构建 / CI / 测试产生的运行日志一律不入库（该路径同时被 `.gitignore` 覆盖）。
> 因此把该轮输出**逐字**转存为本 Markdown：下方 fenced 代码块内容与原文件逐字节相同，
> 未做任何删改（规则 19 的唯一例外「上游夹具本身是 .log」不适用于本文件，故不以任何形式
> 把 `.log` 纳入版本控制）。
>
> | 项 | 值 |
> | --- | --- |
> | 原文件（仓库外留档，不随 PR 提交） | `c-tests-v0.4.log` |
> | 原始字节数 | 1215 |
> | 原始行数 | 31 |
> | 原始 sha256 | `71f99ca645941e2c3f094ebeb3b0100c2dfd3813674760512a78d03d38357dcf` |
>
> **复核方式（给出确切命令，避免围栏边界歧义）**：下方代码块的**内容**按 CommonMark
> 语义是围栏之间的全部字节（含末尾空行），等价的抽取命令是
>
> ```sh
> python3 - "$MD" <<'PYEOF'
> import sys
> t = open(sys.argv[1], encoding="utf-8").read()
> body = t.split("```text" + "\n", 1)[1]
> sys.stdout.buffer.write(body[: body.rindex("```" + "\n")].encode())
> PYEOF
> ```
>
> 即「取 ```` ```text ```` 之后、最后一个 ```` ``` ```` 之前的全部内容，**不要**再剥掉末尾
> 换行」。如此得到的字节数/行数/sha256 应与上表三项逐一相等（实测相等）。若改用另一种
> 口径（额外剥掉结尾空行）抽取**本文件**，会得到 1214 B / 30 行 / sha256 `3a2c9a55…`，
> 与上表的 1215 B / 31 行差恰为那个空行——本表把命令写死后该歧义即消除。
> （同一现象在姊妹文件 `conan-create-log.md` 上表现为 32735 B / 355 行，见该文件头部；
> 两处数字不可混用。）

## 这份输出是怎么产生的

由探索期脚本 `run-c-tests.sh`（任务私有，仓库外）对**已打上 30 个补丁**的源码树逐个编译
并运行 `test/c/std/*.c`，收集每个程序自报的 `PASS (N tests)` 行后求和；脚本同时输出
`FILES=30 TEST_PROCS=232 FAILED_FILES=0` 尾部汇总。脚本形态与 `native-build-test.md`
第 103–104 行、`conan-verify-supplement.md` 第 8 节记载的一致。

**归因（勿混淆两层）**：脚本本身只做「逐个 `clang` 编译 + 运行 + 原样收集 stdout / 追加汇总」，
**不生成** `PASS (N tests)` 那一行的格式——该行由上游测试框架 `test/c/testlib/testlib.c:451`
打印（`printf("%-16s%-8sPASS (%d tests)\n", g_proc_package_name, g_cc, …)`），所以
`std/adler32` 后面的 `clang15` 标签来自 testlib 自报的编译器名（设备 `clang --version`
为 15.0.4），列宽是 testlib 的 `%-16s%-8s`（16 / 8 列），**不是**手工 clang 循环的产物，
也不是「两空格对齐」。

## 逐字内容

```text
std/adler32     clang15 PASS (3 tests)
std/bmp         clang15 PASS (4 tests)
std/bzip2       clang15 PASS (7 tests)
std/cbor        clang15 PASS (4 tests)
std/crc32       clang15 PASS (3 tests)
std/crc64       clang15 PASS (3 tests)
std/deflate     clang15 PASS (19 tests)
std/etc2        clang15 PASS (3 tests)
std/gif         clang15 PASS (45 tests)
std/gzip        clang15 PASS (9 tests)
std/handsum     clang15 PASS (6 tests)
std/jpeg        clang15 PASS (7 tests)
std/json        clang15 PASS (33 tests)
std/lzip        clang15 PASS (1 tests)
std/lzma        clang15 PASS (4 tests)
std/lzw         clang15 PASS (11 tests)
std/netpbm      clang15 PASS (4 tests)
std/nie         clang15 PASS (5 tests)
std/png         clang15 PASS (12 tests)
std/qoi         clang15 PASS (3 tests)
std/sha256      clang15 PASS (3 tests)
std/targa       clang15 PASS (2 tests)
std/thumbhash   clang15 PASS (4 tests)
std/vp8         clang15 PASS (5 tests)
std/wbmp        clang15 PASS (8 tests)
std/webp        clang15 PASS (3 tests)
std/xxhash32    clang15 PASS (3 tests)
std/xxhash64    clang15 PASS (3 tests)
std/xz          clang15 PASS (5 tests)
std/zlib        clang15 PASS (10 tests)
FILES=30 TEST_PROCS=232 FAILED_FILES=0
```
