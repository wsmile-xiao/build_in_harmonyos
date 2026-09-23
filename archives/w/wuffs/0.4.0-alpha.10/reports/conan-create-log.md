# `conan create` 采信轮完整日志（逐字留档）

> **为什么不是 `.log`**：`.gitcode/review-memory.md` 规则 19 把 `*.log` 明列在「PR 中禁止的
> 文件」内——构建 / CI / 测试产生的运行日志一律不入库（该路径同时被 `.gitignore` 覆盖）。
> 因此把该轮输出**逐字**转存为本 Markdown：下方 fenced 代码块内容与原文件逐字节相同，
> 未做任何删改（规则 19 的唯一例外「上游夹具本身是 .log」不适用于本文件，故不以任何形式
> 把 `.log` 纳入版本控制）。
>
> | 项 | 值 |
> | --- | --- |
> | 原文件（仓库外留档，不随 PR 提交） | `conan-create-round9.log` |
> | 原始字节数 | 32736 |
> | 原始行数 | 356 |
> | 原始 sha256 | `2706666a65d9b0f4a258f4a88e21abe4437e10b0034086e46afee671a569f49d` |
> | recipe revision（**create 期物料**，见下） | `123c2bd7b1deae5b1b5d70fb2261d1ca` |

> **rrev 判据须写准（第十轮审计 P3-DOC-RREV）**：这个 rrev 是 `conan create` **执行期间**
> 的物料指纹。`scripts/ohc/conan_verify.py` 会在 create 前把工作区 `conandata.yml` 里
> `https://github.com` 就地替换成 `https://ghfast.top/https://github.com`（create 后再回滚），
> 所以该 rrev 对应的是**注入镜像后的** conandata.yml，而不是 HEAD 工作区里官方 URL 那一份
> —— 对 HEAD 的官方态物料单独 `conan export` 会得到**另一个** rrev。两者不同属工具行为，
> 不是包内不一致；本表只用它做**跨轮可比性**判据（同为镜像态时，rrev 相同即导出物料未变）。
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
> 换行」。如此得到的字节数/行数/sha256 应与上表三项逐一相等（实测相等）。第十轮审计用
> 另一种口径（额外剥掉结尾空行）得到 32735 B / 355 行，差恰为该空行——本表把命令写死后
> 该歧义即消除。
>
> **本日志里没有逐程序程序自报行**：本轮 30 个上游 C 测试程序是把 stdout 重定向到各自
> `<name>.out` 后断言的，所以正文只剩汇总行
> `upstream C tests: 30 programs, 232 test cases, all PASS`。
>
> **判据必须限定在代码块内**（重要）：本文件的**说明文字**里也会出现被检索的那个模式
> （本段即是），所以「对整份文件做一次 grep 计数」这种写法会**自我命中**、结论随文字改写而
> 翻转——本项目已在相邻两轮各踩一次。稳健判据是只在正文代码块内计数：
>
> ```sh
> python3 - "$MD" <<'PYEOF' | grep -c 'PASS ('
> import sys
> t = open(sys.argv[1], encoding="utf-8").read()
> body = t.split("```text" + "\n", 1)[1]
> sys.stdout.buffer.write(body[: body.rindex("```" + "\n")].encode())
> PYEOF
> # → 0
> ```
>
> 30 条逐程序 PASS 行的原始证据是 `reports/upstream-c-tests-log.md`（本 PR 提交面内，
> 逐字留档，31 行 / `FILES=30 TEST_PROCS=232 FAILED_FILES=0`）；`notes.md`、
> `test_package/MANIFEST.yml` 与 `manifest.yaml` 里「静态计数 232 与实跑 30/30 吻合」的
> 对账结论均指向该文件。

## 逐字内容

```text

======== Exporting recipe to the cache ========
wuffs/0.4.0-alpha.10@ohpcd/stable: Exporting package recipe: /storage/Users/currentUser/ws/wt-wuffs-0.4.0-alpha.10/archives/w/wuffs/0.4.0-alpha.10/conanfile.py
wuffs/0.4.0-alpha.10@ohpcd/stable: exports: File 'conandata.yml' found. Exporting it...
wuffs/0.4.0-alpha.10@ohpcd/stable: Calling export_sources()
wuffs/0.4.0-alpha.10@ohpcd/stable: Copied 1 '.yml' file: conandata.yml
wuffs/0.4.0-alpha.10@ohpcd/stable: Copied 1 '.py' file: conanfile.py
wuffs/0.4.0-alpha.10@ohpcd/stable: Copied 30 '.patch' files
wuffs/0.4.0-alpha.10@ohpcd/stable: Exported to cache folder: /storage/Users/currentUser/.conan2/p/wuffsfaac6527b850b/e
wuffs/0.4.0-alpha.10@ohpcd/stable: Exported: wuffs/0.4.0-alpha.10@ohpcd/stable#123c2bd7b1deae5b1b5d70fb2261d1ca (2026-09-11 13:21:38 UTC)

======== Input profiles ========
Profile host:
[settings]
arch=armv8
build_type=Release
compiler=clang
compiler.cppstd=17
compiler.libcxx=libc++
compiler.version=15
os=OHOS
os.version=6.0
[conf]
tools.build:compiler_executables={'c': '/data/service/hnp/bin/clang', 'cpp': '/data/service/hnp/bin/clang++'}
[buildenv]
CONFIG_SHELL=/data/service/hnp/bin/bash
SHELL=/data/service/hnp/bin/bash
PATH=+(path)/storage/Users/currentUser/usr/local/bin
PATH=+(path)/data/service/hnp/bin
LD_LIBRARY_PATH=+(path)/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib

Profile build:
[settings]
arch=armv8
build_type=Release
compiler=clang
compiler.cppstd=17
compiler.libcxx=libc++
compiler.version=15
os=OHOS
os.version=6.0
[conf]
tools.build:compiler_executables={'c': '/data/service/hnp/bin/clang', 'cpp': '/data/service/hnp/bin/clang++'}
[buildenv]
CONFIG_SHELL=/data/service/hnp/bin/bash
SHELL=/data/service/hnp/bin/bash
PATH=+(path)/storage/Users/currentUser/usr/local/bin
PATH=+(path)/data/service/hnp/bin
LD_LIBRARY_PATH=+(path)/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib


======== Computing dependency graph ========
Graph root
    cli
Requirements
    wuffs/0.4.0-alpha.10@ohpcd/stable#123c2bd7b1deae5b1b5d70fb2261d1ca - Cache

======== Computing necessary packages ========
Connecting to remote 'ohpcd' anonymously
Requirements
    wuffs/0.4.0-alpha.10@ohpcd/stable#123c2bd7b1deae5b1b5d70fb2261d1ca:da39a3ee5e6b4b0d3255bfef95601890afd80709 - Build

======== Installing packages ========
wuffs/0.4.0-alpha.10@ohpcd/stable: Calling source() in /storage/Users/currentUser/.conan2/p/wuffsfaac6527b850b/s/src
wuffs/0.4.0-alpha.10@ohpcd/stable: Downloading 15.8MB wuffs-0.4.0-alpha.10.tar.gz
wuffs/0.4.0-alpha.10@ohpcd/stable: Sources correctly downloaded from https://ghfast.top/https://github.com/google/wuffs/archive/refs/tags/v0.4.0-alpha.10.tar.gz
wuffs/0.4.0-alpha.10@ohpcd/stable: Uncompressing wuffs-0.4.0-alpha.10.tar.gz to .

-------- Installing package wuffs/0.4.0-alpha.10@ohpcd/stable (1 of 1) --------
wuffs/0.4.0-alpha.10@ohpcd/stable: Building from source
wuffs/0.4.0-alpha.10@ohpcd/stable: Package wuffs/0.4.0-alpha.10@ohpcd/stable:da39a3ee5e6b4b0d3255bfef95601890afd80709
wuffs/0.4.0-alpha.10@ohpcd/stable: Building your package in /storage/Users/currentUser/.conan2/p/b/wuffs4f00ef893a778/b
wuffs/0.4.0-alpha.10@ohpcd/stable: Generating aggregated env files
wuffs/0.4.0-alpha.10@ohpcd/stable: Generated aggregated env files: ['conanbuild.sh', 'conanrun.sh']
wuffs/0.4.0-alpha.10@ohpcd/stable: Calling build()
wuffs/0.4.0-alpha.10@ohpcd/stable: Apply patch (portability): Point the adler32 C test at the versioned single-file release instead of the unversioned development snapshot
wuffs/0.4.0-alpha.10@ohpcd/stable: Apply patch (portability): Point the bmp C test at the versioned single-file release instead of the unversioned development snapshot
wuffs/0.4.0-alpha.10@ohpcd/stable: Apply patch (portability): Point the bzip2 C test at the versioned single-file release instead of the unversioned development snapshot
wuffs/0.4.0-alpha.10@ohpcd/stable: Apply patch (portability): Point the cbor C test at the versioned single-file release instead of the unversioned development snapshot
wuffs/0.4.0-alpha.10@ohpcd/stable: Apply patch (portability): Point the crc32 C test at the versioned single-file release instead of the unversioned development snapshot
wuffs/0.4.0-alpha.10@ohpcd/stable: Apply patch (portability): Point the crc64 C test at the versioned single-file release instead of the unversioned development snapshot
wuffs/0.4.0-alpha.10@ohpcd/stable: Apply patch (portability): Point the deflate C test at the versioned single-file release instead of the unversioned development snapshot
wuffs/0.4.0-alpha.10@ohpcd/stable: Apply patch (portability): Point the etc2 C test at the versioned single-file release instead of the unversioned development snapshot
wuffs/0.4.0-alpha.10@ohpcd/stable: Apply patch (portability): Point the gif C test at the versioned single-file release instead of the unversioned development snapshot
wuffs/0.4.0-alpha.10@ohpcd/stable: Apply patch (portability): Point the gzip C test at the versioned single-file release instead of the unversioned development snapshot
wuffs/0.4.0-alpha.10@ohpcd/stable: Apply patch (portability): Point the handsum C test at the versioned single-file release instead of the unversioned development snapshot
wuffs/0.4.0-alpha.10@ohpcd/stable: Apply patch (portability): Point the jpeg C test at the versioned single-file release instead of the unversioned development snapshot
wuffs/0.4.0-alpha.10@ohpcd/stable: Apply patch (portability): Point the json C test at the versioned single-file release instead of the unversioned development snapshot
wuffs/0.4.0-alpha.10@ohpcd/stable: Apply patch (portability): Point the lzip C test at the versioned single-file release instead of the unversioned development snapshot
wuffs/0.4.0-alpha.10@ohpcd/stable: Apply patch (portability): Point the lzma C test at the versioned single-file release instead of the unversioned development snapshot
wuffs/0.4.0-alpha.10@ohpcd/stable: Apply patch (portability): Point the lzw C test at the versioned single-file release instead of the unversioned development snapshot
wuffs/0.4.0-alpha.10@ohpcd/stable: Apply patch (portability): Point the netpbm C test at the versioned single-file release instead of the unversioned development snapshot
wuffs/0.4.0-alpha.10@ohpcd/stable: Apply patch (portability): Point the nie C test at the versioned single-file release instead of the unversioned development snapshot
wuffs/0.4.0-alpha.10@ohpcd/stable: Apply patch (portability): Point the png C test at the versioned single-file release instead of the unversioned development snapshot
wuffs/0.4.0-alpha.10@ohpcd/stable: Apply patch (portability): Point the qoi C test at the versioned single-file release instead of the unversioned development snapshot
wuffs/0.4.0-alpha.10@ohpcd/stable: Apply patch (portability): Point the sha256 C test at the versioned single-file release instead of the unversioned development snapshot
wuffs/0.4.0-alpha.10@ohpcd/stable: Apply patch (portability): Point the targa C test at the versioned single-file release instead of the unversioned development snapshot
wuffs/0.4.0-alpha.10@ohpcd/stable: Apply patch (portability): Point the thumbhash C test at the versioned single-file release instead of the unversioned development snapshot
wuffs/0.4.0-alpha.10@ohpcd/stable: Apply patch (portability): Point the vp8 C test at the versioned single-file release instead of the unversioned development snapshot
wuffs/0.4.0-alpha.10@ohpcd/stable: Apply patch (portability): Point the wbmp C test at the versioned single-file release instead of the unversioned development snapshot
wuffs/0.4.0-alpha.10@ohpcd/stable: Apply patch (portability): Point the webp C test at the versioned single-file release instead of the unversioned development snapshot
wuffs/0.4.0-alpha.10@ohpcd/stable: Apply patch (portability): Point the xxhash32 C test at the versioned single-file release instead of the unversioned development snapshot
wuffs/0.4.0-alpha.10@ohpcd/stable: Apply patch (portability): Point the xxhash64 C test at the versioned single-file release instead of the unversioned development snapshot
wuffs/0.4.0-alpha.10@ohpcd/stable: Apply patch (portability): Point the xz C test at the versioned single-file release instead of the unversioned development snapshot
wuffs/0.4.0-alpha.10@ohpcd/stable: Apply patch (portability): Point the zlib C test at the versioned single-file release instead of the unversioned development snapshot
wuffs/0.4.0-alpha.10@ohpcd/stable: RUN: /data/service/hnp/bin/clang -c -Wall -Werror -Wpedantic -Wcast-qual -Wcast-align -Wpointer-arith -Wfloat-equal -Wundef -Wvla -Wconversion -Wshadow -Wredundant-decls -Wunused-const-variable -Wstrict-prototypes -Wold-style-definition -std=c99 -Wc++-compat "release/c/wuffs-v0.4.c" -o "/storage/Users/currentUser/.conan2/p/b/wuffs4f00ef893a778/b/build-release/test-bin/header-only-C99-.o"

wuffs/0.4.0-alpha.10@ohpcd/stable: coherence check OK: header-only (C99)
wuffs/0.4.0-alpha.10@ohpcd/stable: RUN: /data/service/hnp/bin/clang -c -Wall -Werror -Wpedantic -Wcast-qual -Wcast-align -Wpointer-arith -Wfloat-equal -Wundef -Wvla -Wconversion -Wshadow -Wredundant-decls -Wunused-const-variable -Wstrict-prototypes -Wold-style-definition -DWUFFS_IMPLEMENTATION -std=c99 -Wc++-compat "release/c/wuffs-v0.4.c" -o "/storage/Users/currentUser/.conan2/p/b/wuffs4f00ef893a778/b/build-release/test-bin/implementation-C99-.o"

wuffs/0.4.0-alpha.10@ohpcd/stable: coherence check OK: implementation (C99)
wuffs/0.4.0-alpha.10@ohpcd/stable: RUN: /data/service/hnp/bin/clang++ -c -Wall -Werror -Wpedantic -Wcast-qual -Wcast-align -Wpointer-arith -Wfloat-equal -Wundef -Wvla -Wconversion -Wshadow -Wredundant-decls -Wunused-const-variable -Wno-c99-extensions -std=c++11 -x c++ "release/c/wuffs-v0.4.c" -o "/storage/Users/currentUser/.conan2/p/b/wuffs4f00ef893a778/b/build-release/test-bin/header-only-C-11-.o"

wuffs/0.4.0-alpha.10@ohpcd/stable: coherence check OK: header-only (C++11)
wuffs/0.4.0-alpha.10@ohpcd/stable: RUN: /data/service/hnp/bin/clang++ -c -Wall -Werror -Wpedantic -Wcast-qual -Wcast-align -Wpointer-arith -Wfloat-equal -Wundef -Wvla -Wconversion -Wshadow -Wredundant-decls -Wunused-const-variable -Wno-c99-extensions -DWUFFS_IMPLEMENTATION -std=c++11 -x c++ "release/c/wuffs-v0.4.c" -o "/storage/Users/currentUser/.conan2/p/b/wuffs4f00ef893a778/b/build-release/test-bin/implementation-C-11-.o"

wuffs/0.4.0-alpha.10@ohpcd/stable: coherence check OK: implementation (C++11)
wuffs/0.4.0-alpha.10@ohpcd/stable: RUN: /data/service/hnp/bin/clang -std=c99 -Wall -Werror "test/c/std/adler32.c" -o "/storage/Users/currentUser/.conan2/p/b/wuffs4f00ef893a778/b/build-release/test-bin/adler32"

wuffs/0.4.0-alpha.10@ohpcd/stable: RUN: "/storage/Users/currentUser/.conan2/p/b/wuffs4f00ef893a778/b/build-release/test-bin/adler32" > "/storage/Users/currentUser/.conan2/p/b/wuffs4f00ef893a778/b/build-release/test-bin/adler32.out" 2>&1

wuffs/0.4.0-alpha.10@ohpcd/stable: RUN: /data/service/hnp/bin/clang -std=c99 -Wall -Werror "test/c/std/bmp.c" -o "/storage/Users/currentUser/.conan2/p/b/wuffs4f00ef893a778/b/build-release/test-bin/bmp"

wuffs/0.4.0-alpha.10@ohpcd/stable: RUN: "/storage/Users/currentUser/.conan2/p/b/wuffs4f00ef893a778/b/build-release/test-bin/bmp" > "/storage/Users/currentUser/.conan2/p/b/wuffs4f00ef893a778/b/build-release/test-bin/bmp.out" 2>&1

wuffs/0.4.0-alpha.10@ohpcd/stable: RUN: /data/service/hnp/bin/clang -std=c99 -Wall -Werror "test/c/std/bzip2.c" -o "/storage/Users/currentUser/.conan2/p/b/wuffs4f00ef893a778/b/build-release/test-bin/bzip2"

wuffs/0.4.0-alpha.10@ohpcd/stable: RUN: "/storage/Users/currentUser/.conan2/p/b/wuffs4f00ef893a778/b/build-release/test-bin/bzip2" > "/storage/Users/currentUser/.conan2/p/b/wuffs4f00ef893a778/b/build-release/test-bin/bzip2.out" 2>&1

wuffs/0.4.0-alpha.10@ohpcd/stable: RUN: /data/service/hnp/bin/clang -std=c99 -Wall -Werror "test/c/std/cbor.c" -o "/storage/Users/currentUser/.conan2/p/b/wuffs4f00ef893a778/b/build-release/test-bin/cbor"

wuffs/0.4.0-alpha.10@ohpcd/stable: RUN: "/storage/Users/currentUser/.conan2/p/b/wuffs4f00ef893a778/b/build-release/test-bin/cbor" > "/storage/Users/currentUser/.conan2/p/b/wuffs4f00ef893a778/b/build-release/test-bin/cbor.out" 2>&1

wuffs/0.4.0-alpha.10@ohpcd/stable: RUN: /data/service/hnp/bin/clang -std=c99 -Wall -Werror "test/c/std/crc32.c" -o "/storage/Users/currentUser/.conan2/p/b/wuffs4f00ef893a778/b/build-release/test-bin/crc32"

wuffs/0.4.0-alpha.10@ohpcd/stable: RUN: "/storage/Users/currentUser/.conan2/p/b/wuffs4f00ef893a778/b/build-release/test-bin/crc32" > "/storage/Users/currentUser/.conan2/p/b/wuffs4f00ef893a778/b/build-release/test-bin/crc32.out" 2>&1

wuffs/0.4.0-alpha.10@ohpcd/stable: RUN: /data/service/hnp/bin/clang -std=c99 -Wall -Werror "test/c/std/crc64.c" -o "/storage/Users/currentUser/.conan2/p/b/wuffs4f00ef893a778/b/build-release/test-bin/crc64"

wuffs/0.4.0-alpha.10@ohpcd/stable: RUN: "/storage/Users/currentUser/.conan2/p/b/wuffs4f00ef893a778/b/build-release/test-bin/crc64" > "/storage/Users/currentUser/.conan2/p/b/wuffs4f00ef893a778/b/build-release/test-bin/crc64.out" 2>&1

wuffs/0.4.0-alpha.10@ohpcd/stable: RUN: /data/service/hnp/bin/clang -std=c99 -Wall -Werror "test/c/std/deflate.c" -o "/storage/Users/currentUser/.conan2/p/b/wuffs4f00ef893a778/b/build-release/test-bin/deflate"

wuffs/0.4.0-alpha.10@ohpcd/stable: RUN: "/storage/Users/currentUser/.conan2/p/b/wuffs4f00ef893a778/b/build-release/test-bin/deflate" > "/storage/Users/currentUser/.conan2/p/b/wuffs4f00ef893a778/b/build-release/test-bin/deflate.out" 2>&1

wuffs/0.4.0-alpha.10@ohpcd/stable: RUN: /data/service/hnp/bin/clang -std=c99 -Wall -Werror "test/c/std/etc2.c" -o "/storage/Users/currentUser/.conan2/p/b/wuffs4f00ef893a778/b/build-release/test-bin/etc2"

wuffs/0.4.0-alpha.10@ohpcd/stable: RUN: "/storage/Users/currentUser/.conan2/p/b/wuffs4f00ef893a778/b/build-release/test-bin/etc2" > "/storage/Users/currentUser/.conan2/p/b/wuffs4f00ef893a778/b/build-release/test-bin/etc2.out" 2>&1

wuffs/0.4.0-alpha.10@ohpcd/stable: RUN: /data/service/hnp/bin/clang -std=c99 -Wall -Werror "test/c/std/gif.c" -o "/storage/Users/currentUser/.conan2/p/b/wuffs4f00ef893a778/b/build-release/test-bin/gif"

wuffs/0.4.0-alpha.10@ohpcd/stable: RUN: "/storage/Users/currentUser/.conan2/p/b/wuffs4f00ef893a778/b/build-release/test-bin/gif" > "/storage/Users/currentUser/.conan2/p/b/wuffs4f00ef893a778/b/build-release/test-bin/gif.out" 2>&1

wuffs/0.4.0-alpha.10@ohpcd/stable: RUN: /data/service/hnp/bin/clang -std=c99 -Wall -Werror "test/c/std/gzip.c" -o "/storage/Users/currentUser/.conan2/p/b/wuffs4f00ef893a778/b/build-release/test-bin/gzip"

wuffs/0.4.0-alpha.10@ohpcd/stable: RUN: "/storage/Users/currentUser/.conan2/p/b/wuffs4f00ef893a778/b/build-release/test-bin/gzip" > "/storage/Users/currentUser/.conan2/p/b/wuffs4f00ef893a778/b/build-release/test-bin/gzip.out" 2>&1

wuffs/0.4.0-alpha.10@ohpcd/stable: RUN: /data/service/hnp/bin/clang -std=c99 -Wall -Werror "test/c/std/handsum.c" -o "/storage/Users/currentUser/.conan2/p/b/wuffs4f00ef893a778/b/build-release/test-bin/handsum"

wuffs/0.4.0-alpha.10@ohpcd/stable: RUN: "/storage/Users/currentUser/.conan2/p/b/wuffs4f00ef893a778/b/build-release/test-bin/handsum" > "/storage/Users/currentUser/.conan2/p/b/wuffs4f00ef893a778/b/build-release/test-bin/handsum.out" 2>&1

wuffs/0.4.0-alpha.10@ohpcd/stable: RUN: /data/service/hnp/bin/clang -std=c99 -Wall -Werror "test/c/std/jpeg.c" -o "/storage/Users/currentUser/.conan2/p/b/wuffs4f00ef893a778/b/build-release/test-bin/jpeg"

wuffs/0.4.0-alpha.10@ohpcd/stable: RUN: "/storage/Users/currentUser/.conan2/p/b/wuffs4f00ef893a778/b/build-release/test-bin/jpeg" > "/storage/Users/currentUser/.conan2/p/b/wuffs4f00ef893a778/b/build-release/test-bin/jpeg.out" 2>&1

wuffs/0.4.0-alpha.10@ohpcd/stable: RUN: /data/service/hnp/bin/clang -std=c99 -Wall -Werror "test/c/std/json.c" -o "/storage/Users/currentUser/.conan2/p/b/wuffs4f00ef893a778/b/build-release/test-bin/json"

wuffs/0.4.0-alpha.10@ohpcd/stable: RUN: "/storage/Users/currentUser/.conan2/p/b/wuffs4f00ef893a778/b/build-release/test-bin/json" > "/storage/Users/currentUser/.conan2/p/b/wuffs4f00ef893a778/b/build-release/test-bin/json.out" 2>&1

wuffs/0.4.0-alpha.10@ohpcd/stable: RUN: /data/service/hnp/bin/clang -std=c99 -Wall -Werror "test/c/std/lzip.c" -o "/storage/Users/currentUser/.conan2/p/b/wuffs4f00ef893a778/b/build-release/test-bin/lzip"

wuffs/0.4.0-alpha.10@ohpcd/stable: RUN: "/storage/Users/currentUser/.conan2/p/b/wuffs4f00ef893a778/b/build-release/test-bin/lzip" > "/storage/Users/currentUser/.conan2/p/b/wuffs4f00ef893a778/b/build-release/test-bin/lzip.out" 2>&1

wuffs/0.4.0-alpha.10@ohpcd/stable: RUN: /data/service/hnp/bin/clang -std=c99 -Wall -Werror "test/c/std/lzma.c" -o "/storage/Users/currentUser/.conan2/p/b/wuffs4f00ef893a778/b/build-release/test-bin/lzma"

wuffs/0.4.0-alpha.10@ohpcd/stable: RUN: "/storage/Users/currentUser/.conan2/p/b/wuffs4f00ef893a778/b/build-release/test-bin/lzma" > "/storage/Users/currentUser/.conan2/p/b/wuffs4f00ef893a778/b/build-release/test-bin/lzma.out" 2>&1

wuffs/0.4.0-alpha.10@ohpcd/stable: RUN: /data/service/hnp/bin/clang -std=c99 -Wall -Werror "test/c/std/lzw.c" -o "/storage/Users/currentUser/.conan2/p/b/wuffs4f00ef893a778/b/build-release/test-bin/lzw"

wuffs/0.4.0-alpha.10@ohpcd/stable: RUN: "/storage/Users/currentUser/.conan2/p/b/wuffs4f00ef893a778/b/build-release/test-bin/lzw" > "/storage/Users/currentUser/.conan2/p/b/wuffs4f00ef893a778/b/build-release/test-bin/lzw.out" 2>&1

wuffs/0.4.0-alpha.10@ohpcd/stable: RUN: /data/service/hnp/bin/clang -std=c99 -Wall -Werror "test/c/std/netpbm.c" -o "/storage/Users/currentUser/.conan2/p/b/wuffs4f00ef893a778/b/build-release/test-bin/netpbm"

wuffs/0.4.0-alpha.10@ohpcd/stable: RUN: "/storage/Users/currentUser/.conan2/p/b/wuffs4f00ef893a778/b/build-release/test-bin/netpbm" > "/storage/Users/currentUser/.conan2/p/b/wuffs4f00ef893a778/b/build-release/test-bin/netpbm.out" 2>&1

wuffs/0.4.0-alpha.10@ohpcd/stable: RUN: /data/service/hnp/bin/clang -std=c99 -Wall -Werror "test/c/std/nie.c" -o "/storage/Users/currentUser/.conan2/p/b/wuffs4f00ef893a778/b/build-release/test-bin/nie"

wuffs/0.4.0-alpha.10@ohpcd/stable: RUN: "/storage/Users/currentUser/.conan2/p/b/wuffs4f00ef893a778/b/build-release/test-bin/nie" > "/storage/Users/currentUser/.conan2/p/b/wuffs4f00ef893a778/b/build-release/test-bin/nie.out" 2>&1

wuffs/0.4.0-alpha.10@ohpcd/stable: RUN: /data/service/hnp/bin/clang -std=c99 -Wall -Werror "test/c/std/png.c" -o "/storage/Users/currentUser/.conan2/p/b/wuffs4f00ef893a778/b/build-release/test-bin/png"

wuffs/0.4.0-alpha.10@ohpcd/stable: RUN: "/storage/Users/currentUser/.conan2/p/b/wuffs4f00ef893a778/b/build-release/test-bin/png" > "/storage/Users/currentUser/.conan2/p/b/wuffs4f00ef893a778/b/build-release/test-bin/png.out" 2>&1

wuffs/0.4.0-alpha.10@ohpcd/stable: RUN: /data/service/hnp/bin/clang -std=c99 -Wall -Werror "test/c/std/qoi.c" -o "/storage/Users/currentUser/.conan2/p/b/wuffs4f00ef893a778/b/build-release/test-bin/qoi"

wuffs/0.4.0-alpha.10@ohpcd/stable: RUN: "/storage/Users/currentUser/.conan2/p/b/wuffs4f00ef893a778/b/build-release/test-bin/qoi" > "/storage/Users/currentUser/.conan2/p/b/wuffs4f00ef893a778/b/build-release/test-bin/qoi.out" 2>&1

wuffs/0.4.0-alpha.10@ohpcd/stable: RUN: /data/service/hnp/bin/clang -std=c99 -Wall -Werror "test/c/std/sha256.c" -o "/storage/Users/currentUser/.conan2/p/b/wuffs4f00ef893a778/b/build-release/test-bin/sha256"

wuffs/0.4.0-alpha.10@ohpcd/stable: RUN: "/storage/Users/currentUser/.conan2/p/b/wuffs4f00ef893a778/b/build-release/test-bin/sha256" > "/storage/Users/currentUser/.conan2/p/b/wuffs4f00ef893a778/b/build-release/test-bin/sha256.out" 2>&1

wuffs/0.4.0-alpha.10@ohpcd/stable: RUN: /data/service/hnp/bin/clang -std=c99 -Wall -Werror "test/c/std/targa.c" -o "/storage/Users/currentUser/.conan2/p/b/wuffs4f00ef893a778/b/build-release/test-bin/targa"

wuffs/0.4.0-alpha.10@ohpcd/stable: RUN: "/storage/Users/currentUser/.conan2/p/b/wuffs4f00ef893a778/b/build-release/test-bin/targa" > "/storage/Users/currentUser/.conan2/p/b/wuffs4f00ef893a778/b/build-release/test-bin/targa.out" 2>&1

wuffs/0.4.0-alpha.10@ohpcd/stable: RUN: /data/service/hnp/bin/clang -std=c99 -Wall -Werror "test/c/std/thumbhash.c" -o "/storage/Users/currentUser/.conan2/p/b/wuffs4f00ef893a778/b/build-release/test-bin/thumbhash"

wuffs/0.4.0-alpha.10@ohpcd/stable: RUN: "/storage/Users/currentUser/.conan2/p/b/wuffs4f00ef893a778/b/build-release/test-bin/thumbhash" > "/storage/Users/currentUser/.conan2/p/b/wuffs4f00ef893a778/b/build-release/test-bin/thumbhash.out" 2>&1

wuffs/0.4.0-alpha.10@ohpcd/stable: RUN: /data/service/hnp/bin/clang -std=c99 -Wall -Werror "test/c/std/vp8.c" -o "/storage/Users/currentUser/.conan2/p/b/wuffs4f00ef893a778/b/build-release/test-bin/vp8"

wuffs/0.4.0-alpha.10@ohpcd/stable: RUN: "/storage/Users/currentUser/.conan2/p/b/wuffs4f00ef893a778/b/build-release/test-bin/vp8" > "/storage/Users/currentUser/.conan2/p/b/wuffs4f00ef893a778/b/build-release/test-bin/vp8.out" 2>&1

wuffs/0.4.0-alpha.10@ohpcd/stable: RUN: /data/service/hnp/bin/clang -std=c99 -Wall -Werror "test/c/std/wbmp.c" -o "/storage/Users/currentUser/.conan2/p/b/wuffs4f00ef893a778/b/build-release/test-bin/wbmp"

wuffs/0.4.0-alpha.10@ohpcd/stable: RUN: "/storage/Users/currentUser/.conan2/p/b/wuffs4f00ef893a778/b/build-release/test-bin/wbmp" > "/storage/Users/currentUser/.conan2/p/b/wuffs4f00ef893a778/b/build-release/test-bin/wbmp.out" 2>&1

wuffs/0.4.0-alpha.10@ohpcd/stable: RUN: /data/service/hnp/bin/clang -std=c99 -Wall -Werror "test/c/std/webp.c" -o "/storage/Users/currentUser/.conan2/p/b/wuffs4f00ef893a778/b/build-release/test-bin/webp"

wuffs/0.4.0-alpha.10@ohpcd/stable: RUN: "/storage/Users/currentUser/.conan2/p/b/wuffs4f00ef893a778/b/build-release/test-bin/webp" > "/storage/Users/currentUser/.conan2/p/b/wuffs4f00ef893a778/b/build-release/test-bin/webp.out" 2>&1

wuffs/0.4.0-alpha.10@ohpcd/stable: RUN: /data/service/hnp/bin/clang -std=c99 -Wall -Werror "test/c/std/xxhash32.c" -o "/storage/Users/currentUser/.conan2/p/b/wuffs4f00ef893a778/b/build-release/test-bin/xxhash32"

wuffs/0.4.0-alpha.10@ohpcd/stable: RUN: "/storage/Users/currentUser/.conan2/p/b/wuffs4f00ef893a778/b/build-release/test-bin/xxhash32" > "/storage/Users/currentUser/.conan2/p/b/wuffs4f00ef893a778/b/build-release/test-bin/xxhash32.out" 2>&1

wuffs/0.4.0-alpha.10@ohpcd/stable: RUN: /data/service/hnp/bin/clang -std=c99 -Wall -Werror "test/c/std/xxhash64.c" -o "/storage/Users/currentUser/.conan2/p/b/wuffs4f00ef893a778/b/build-release/test-bin/xxhash64"

wuffs/0.4.0-alpha.10@ohpcd/stable: RUN: "/storage/Users/currentUser/.conan2/p/b/wuffs4f00ef893a778/b/build-release/test-bin/xxhash64" > "/storage/Users/currentUser/.conan2/p/b/wuffs4f00ef893a778/b/build-release/test-bin/xxhash64.out" 2>&1

wuffs/0.4.0-alpha.10@ohpcd/stable: RUN: /data/service/hnp/bin/clang -std=c99 -Wall -Werror "test/c/std/xz.c" -o "/storage/Users/currentUser/.conan2/p/b/wuffs4f00ef893a778/b/build-release/test-bin/xz"

wuffs/0.4.0-alpha.10@ohpcd/stable: RUN: "/storage/Users/currentUser/.conan2/p/b/wuffs4f00ef893a778/b/build-release/test-bin/xz" > "/storage/Users/currentUser/.conan2/p/b/wuffs4f00ef893a778/b/build-release/test-bin/xz.out" 2>&1

wuffs/0.4.0-alpha.10@ohpcd/stable: RUN: /data/service/hnp/bin/clang -std=c99 -Wall -Werror "test/c/std/zlib.c" -o "/storage/Users/currentUser/.conan2/p/b/wuffs4f00ef893a778/b/build-release/test-bin/zlib"

wuffs/0.4.0-alpha.10@ohpcd/stable: RUN: "/storage/Users/currentUser/.conan2/p/b/wuffs4f00ef893a778/b/build-release/test-bin/zlib" > "/storage/Users/currentUser/.conan2/p/b/wuffs4f00ef893a778/b/build-release/test-bin/zlib.out" 2>&1

wuffs/0.4.0-alpha.10@ohpcd/stable: upstream C tests: 30 programs, 232 test cases, all PASS
wuffs/0.4.0-alpha.10@ohpcd/stable: RUN: /data/service/hnp/bin/clang++ -O3 -fdata-sections -ffunction-sections -Wall -Wl,--gc-sections -fno-rtti -fno-exceptions example/crc32/*.cc -o "/storage/Users/currentUser/.conan2/p/b/wuffs4f00ef893a778/b/build-release/test-bin/example-crc32"

wuffs/0.4.0-alpha.10@ohpcd/stable: RUN: /data/service/hnp/bin/clang++ -O3 -fdata-sections -ffunction-sections -Wall -Wl,--gc-sections -fno-rtti -fno-exceptions example/jsonptr/*.cc -o "/storage/Users/currentUser/.conan2/p/b/wuffs4f00ef893a778/b/build-release/test-bin/example-jsonptr"

wuffs/0.4.0-alpha.10@ohpcd/stable: RUN: /data/service/hnp/bin/clang -O3 -fdata-sections -ffunction-sections -Wall -Wl,--gc-sections example/convert-to-nia/*.c -o "/storage/Users/currentUser/.conan2/p/b/wuffs4f00ef893a778/b/build-release/test-bin/example-convert-to-nia"

wuffs/0.4.0-alpha.10@ohpcd/stable: RUN: /data/service/hnp/bin/clang -O3 -fdata-sections -ffunction-sections -Wall -Wl,--gc-sections example/mzcat/*.c -o "/storage/Users/currentUser/.conan2/p/b/wuffs4f00ef893a778/b/build-release/test-bin/example-mzcat"

wuffs/0.4.0-alpha.10@ohpcd/stable: golden regression OK: test/nia-checksums-of-data.txt (202 entries)
wuffs/0.4.0-alpha.10@ohpcd/stable: golden regression OK: test/mzcat-checksums-of-data.txt (34 entries)
wuffs/0.4.0-alpha.10@ohpcd/stable: Package 'da39a3ee5e6b4b0d3255bfef95601890afd80709' built
wuffs/0.4.0-alpha.10@ohpcd/stable: Build folder /storage/Users/currentUser/.conan2/p/b/wuffs4f00ef893a778/b/build-release
wuffs/0.4.0-alpha.10@ohpcd/stable: Generating the package
wuffs/0.4.0-alpha.10@ohpcd/stable: Packaging in folder /storage/Users/currentUser/.conan2/p/b/wuffs4f00ef893a778/p
wuffs/0.4.0-alpha.10@ohpcd/stable: Calling package()
wuffs/0.4.0-alpha.10@ohpcd/stable: package(): Packaged 1 '.c' file: wuffs-v0.4.c
wuffs/0.4.0-alpha.10@ohpcd/stable: package(): Packaged 3 files: LICENSE, LICENSE-APACHE, LICENSE-MIT
wuffs/0.4.0-alpha.10@ohpcd/stable: Created package revision 36d0e32051f317b95c8f56a40e8f183f
wuffs/0.4.0-alpha.10@ohpcd/stable: Package 'da39a3ee5e6b4b0d3255bfef95601890afd80709' created
wuffs/0.4.0-alpha.10@ohpcd/stable: Full package reference: wuffs/0.4.0-alpha.10@ohpcd/stable#123c2bd7b1deae5b1b5d70fb2261d1ca:da39a3ee5e6b4b0d3255bfef95601890afd80709#36d0e32051f317b95c8f56a40e8f183f
wuffs/0.4.0-alpha.10@ohpcd/stable: Package folder /storage/Users/currentUser/.conan2/p/b/wuffs4f00ef893a778/p

======== Launching test_package ========

======== Computing dependency graph ========
Graph root
    wuffs/0.4.0-alpha.10@ohpcd/stable (test package): /storage/Users/currentUser/ws/wt-wuffs-0.4.0-alpha.10/archives/w/wuffs/0.4.0-alpha.10/test_package/conanfile.py
Requirements
    wuffs/0.4.0-alpha.10@ohpcd/stable#123c2bd7b1deae5b1b5d70fb2261d1ca - Cache

======== Computing necessary packages ========
Requirements
    wuffs/0.4.0-alpha.10@ohpcd/stable#123c2bd7b1deae5b1b5d70fb2261d1ca:da39a3ee5e6b4b0d3255bfef95601890afd80709#36d0e32051f317b95c8f56a40e8f183f - Cache

======== Installing packages ========
wuffs/0.4.0-alpha.10@ohpcd/stable: Already installed! (1 of 1)

======== Testing the package ========
Removing previously existing 'test_package' build folder: /storage/Users/currentUser/ws/wt-wuffs-0.4.0-alpha.10/archives/w/wuffs/0.4.0-alpha.10/test_package/build/clang-15-armv8-17-release
wuffs/0.4.0-alpha.10@ohpcd/stable (test package): Test package build: build/clang-15-armv8-17-release
wuffs/0.4.0-alpha.10@ohpcd/stable (test package): Test package build folder: /storage/Users/currentUser/ws/wt-wuffs-0.4.0-alpha.10/archives/w/wuffs/0.4.0-alpha.10/test_package/build/clang-15-armv8-17-release
wuffs/0.4.0-alpha.10@ohpcd/stable (test package): Calling generate()
wuffs/0.4.0-alpha.10@ohpcd/stable (test package): Generators folder: /storage/Users/currentUser/ws/wt-wuffs-0.4.0-alpha.10/archives/w/wuffs/0.4.0-alpha.10/test_package/build/clang-15-armv8-17-release/generators
wuffs/0.4.0-alpha.10@ohpcd/stable (test package): CMakeDeps necessary find_package() and targets for your CMakeLists.txt
    find_package(wuffs)
    target_link_libraries(... wuffs::wuffs)
wuffs/0.4.0-alpha.10@ohpcd/stable (test package): CMakeToolchain generated: conan_toolchain.cmake
wuffs/0.4.0-alpha.10@ohpcd/stable (test package): CMakeToolchain generated: /storage/Users/currentUser/ws/wt-wuffs-0.4.0-alpha.10/archives/w/wuffs/0.4.0-alpha.10/test_package/build/clang-15-armv8-17-release/generators/CMakePresets.json
wuffs/0.4.0-alpha.10@ohpcd/stable (test package): CMakeToolchain generated: /storage/Users/currentUser/ws/wt-wuffs-0.4.0-alpha.10/archives/w/wuffs/0.4.0-alpha.10/test_package/CMakeUserPresets.json
wuffs/0.4.0-alpha.10@ohpcd/stable (test package): Generating aggregated env files
wuffs/0.4.0-alpha.10@ohpcd/stable (test package): Generated aggregated env files: ['conanbuild.sh', 'conanrun.sh']

======== Testing the package: Building ========
wuffs/0.4.0-alpha.10@ohpcd/stable (test package): Calling build()
wuffs/0.4.0-alpha.10@ohpcd/stable (test package): Running CMake.configure()
wuffs/0.4.0-alpha.10@ohpcd/stable (test package): RUN: cmake -G "Unix Makefiles" -DCMAKE_TOOLCHAIN_FILE="generators/conan_toolchain.cmake" -DCMAKE_INSTALL_PREFIX="/storage/Users/currentUser/ws/wt-wuffs-0.4.0-alpha.10/archives/w/wuffs/0.4.0-alpha.10/test_package" -DCMAKE_POLICY_DEFAULT_CMP0091="NEW" -DCMAKE_BUILD_TYPE="Release" "/storage/Users/currentUser/ws/wt-wuffs-0.4.0-alpha.10/archives/w/wuffs/0.4.0-alpha.10/test_package"
Problem parsing /proc/meminfo
-- Using Conan toolchain: /storage/Users/currentUser/ws/wt-wuffs-0.4.0-alpha.10/archives/w/wuffs/0.4.0-alpha.10/test_package/build/clang-15-armv8-17-release/generators/conan_toolchain.cmake
-- Conan toolchain: Defining libcxx as C++ flags: -stdlib=libc++
-- Conan toolchain: C++ Standard 17 with extensions OFF
-- The C compiler identification is Clang 15.0.4
-- The CXX compiler identification is Clang 15.0.4
System is unknown to cmake, create:
Platform/HarmonyOS to use this system, please post your config file on discourse.cmake.org so it can be added to cmake
-- Detecting C compiler ABI info
System is unknown to cmake, create:
Platform/HarmonyOS to use this system, please post your config file on discourse.cmake.org so it can be added to cmake
-- Detecting C compiler ABI info - done
-- Check for working C compiler: /data/service/hnp/bin/clang - skipped
-- Detecting C compile features
-- Detecting C compile features - done
-- Detecting CXX compiler ABI info
System is unknown to cmake, create:
Platform/HarmonyOS to use this system, please post your config file on discourse.cmake.org so it can be added to cmake
-- Detecting CXX compiler ABI info - done
-- Check for working CXX compiler: /data/service/hnp/bin/clang++ - skipped
-- Detecting CXX compile features
-- Detecting CXX compile features - done
-- Conan: Target declared 'wuffs::wuffs'
-- Configuring done (1.6s)
-- Generating done (0.0s)
-- Build files have been written to: /storage/Users/currentUser/ws/wt-wuffs-0.4.0-alpha.10/archives/w/wuffs/0.4.0-alpha.10/test_package/build/clang-15-armv8-17-release

wuffs/0.4.0-alpha.10@ohpcd/stable (test package): Running CMake.build()
wuffs/0.4.0-alpha.10@ohpcd/stable (test package): RUN: cmake --build "/storage/Users/currentUser/ws/wt-wuffs-0.4.0-alpha.10/archives/w/wuffs/0.4.0-alpha.10/test_package/build/clang-15-armv8-17-release" -- -j20
make: jobserver mkfifo: /storage/Users/currentUser/GMfifo28339: Operation not permitted
[ 12%] Building C object CMakeFiles/ohos_platform_test.dir/ohos_platform_test.c.obj
[ 25%] Building C object CMakeFiles/test_wuffs.dir/test_wuffs.c.obj
[ 37%] Building C object CMakeFiles/test_wuffs.dir/test_wuffs_header_only_tu.c.obj
[ 50%] Building C object CMakeFiles/ohos_platform_test_portable.dir/ohos_platform_test.c.obj
[ 62%] Building CXX object CMakeFiles/test_wuffs.dir/test_wuffs_cpp.cpp.obj
[ 75%] Linking C executable ohos_platform_test_portable
[ 75%] Built target ohos_platform_test_portable
[ 87%] Linking C executable ohos_platform_test
[ 87%] Built target ohos_platform_test
[100%] Linking CXX executable test_wuffs
[100%] Built target test_wuffs


======== Testing the package: Executing test ========
wuffs/0.4.0-alpha.10@ohpcd/stable (test package): Running test()
wuffs/0.4.0-alpha.10@ohpcd/stable (test package): RUN: ./test_wuffs
OK: 15 checks passed, 0 failed

wuffs/0.4.0-alpha.10@ohpcd/stable (test package): RUN: ./ohos_platform_test
# build: default (aarch64 fast paths enabled)
# wuffs_base__cpu_arch__have_arm_neon()     = 1 (want 1)
# wuffs_base__cpu_arch__have_arm_crc32()    = 0
# wuffs_base__cpu_arch__have_x86_sse42()    = 0
OK: 32 checks passed, 0 failed

wuffs/0.4.0-alpha.10@ohpcd/stable (test package): RUN: ./ohos_platform_test_portable
# build: portable (WUFFS_CONFIG__AVOID_CPU_ARCH): arch-specific code disabled
# wuffs_base__cpu_arch__have_arm_neon()     = 0 (want 0)
# wuffs_base__cpu_arch__have_arm_crc32()    = 0
# wuffs_base__cpu_arch__have_x86_sse42()    = 0
OK: 32 checks passed, 0 failed

```
