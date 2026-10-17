# ghostscript 10.07.1.1 测试记录

设备：HarmonyOS aarch64（HongMeng Kernel 1.12.0）。隔离缓存 `CONAN_HOME=/storage/Users/currentUser/work/psj/ch-gs14845`。

命令：

```
conan create archives/g/ghostscript/10.07.1.1 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
```

2026-10-04 那次打包日志是 `create.log`（末行 `CREATE_EXIT:0`，包修订 `01d92cf349a0dd98ff915f4bd99a04430171517f`）。当时声明的 35 项只覆盖了 `examples` 与 `acctest`，少于审查人按同一发行包数出的 508。2026-10-08 用 `upstream_tests.py` 补齐 508 项。真机 `github.com` 连接超时，隔离 `CONAN_HOME` 的 `core.sources:download_cache` 放入同一 SHA-256 的官方包后，`source()` 打印 `retrieved from local download cache`。配方里的 URL 没有改成镜像。本轮打包日志是 `/storage/Users/currentUser/work/psj/gs14845/create-508.log`。

## 产物

`make soinstall` 之后安装目录（2026-10-04 实测，本轮 create 会重装）：

- `lib/libgs.so` → `libgs.so.10.07`
- `lib/libgs.so.10` → `libgs.so.10.07`
- `lib/libgs.so.10.07`（32561664 字节，真实共享库）
- `include/ghostscript/iapi.h`、`ierrors.h`、`gdevdsp.h`
- `bin/gs` 保留

`make check` 仍会执行。上游 Makefile 的 `check` 目标不产生用例，不计入 N。

## 508 口径

在解压后的 `ghostscript-10.07.1` 根目录，普通文件计入 N 的条件是：路径上有一段目录名属于 `{test, tests, unittest, unittests, gstest}`，扩展名不是 `.xml`、`.po`、`.plo`、`.tpo`、`.o`、`.lo`、`.obj`、`.pyc`，并且不位于 `tiff-config`、`.deps`、`obj`、`soobj`、`generated`、`.libs`、`__pycache__`、`data` 或点目录下。发行包上这个条件是 508。配置后的源码树会多出 `tiff-config` 和 freetype 下载到 `tests/data` 的字体，这两类被排除后仍是 508。

| 位置 | 文件数 | 归类 |
|---|---|---|
| tiff/test | 162 | 单元测试 |
| libpng/tests | 34 | 单元测试 |
| zlib 的 test 与 contrib/*/test | 36 | 单元测试 |
| freetype/tests | 4 | 单元测试 |
| brotli/python/tests | 6 | 单元测试 |
| tesseract/unittest | 81 | 单元测试 |
| extract/test | 131 | 集成测试 |
| toolbin/tests | 51 | 集成测试 |
| demos/java/gstest | 3 | 集成测试 |
| 合计 | 508 | 单元 323 + 集成 185 |

`examples` 与 `lib/acctest.ps` 共 35 项不在这 508 里。脚本仍运行它们，结果记为 EXTRA，不拿来冒充声明 N。

## 2026-10-08 真机实跑

声明结果来自修过依赖处理之后的脚本，对本次 `conan create` 装好的 `gs` 再跑一遍。开始时间 Thu Oct 8 03:39:33 CST 2026。日志 `upstream-rerun2.log`，台账 `upstream-rerun2/ledger.txt` 共 508 行。`GS_VERSION_RC=0 10.07.1`。

```
UPSTREAM_ENUM=508
UPSTREAM_TOTAL=508
UPSTREAM_PASS=217
UPSTREAM_FAIL=1
UPSTREAM_BLOCKED=290
UPSTREAM_RESULT=REASONS_RECORDED
```

通过 217 的构成：tiff 162、libpng 31、extract 的 test-gs 相关 9、freetype 4、zlib 8、toolbin 3。

`create-508.log` 里嵌在 `conan create` 中的那次套件不是这组数字。那次脚本还没有把 tiff 的 `CXX` 固定成 SDK `clang++`，libpng 检查超时仍是 2400 秒，当时另一路构建占着 CPU，libpng 以退出码 124 结束，tiff configure 停在 `/lib/cpp`。那次台账已作废。当前脚本已改这两处，并在字体文件已存在时不再因为 GitHub 超时放弃 freetype。

### 失败 1

`libpng/tests/pngtest-all`。automake 汇总 `# TOTAL: 32 # PASS: 31 # FAIL: 1`。`upstream-rerun2/libpng-build/test-suite.log`：

```
pngtest --strict .../libpng/pngtest.png
   with zlib   version 1.3.1.zlib-ng
Files .../libpng/pngtest.png and pngout.png are different
   Was .../pngtest.png written with the same maximum IDAT chunk size (8192 bytes),
   filtering heuristic (libpng default), compression level (zlib default),
   and zlib version (1.3.1.zlib-ng)?
FAIL
libpng FAILS test
```

设备上的 `libz.so` 是 harmonybrew 的 zlib-ng。参考 PNG 不是用这个 zlib 生成的，`--strict` 的字节比较失败。同一次输出里的 badpal 样本是 `FAIL(EXPECTED)`，套件把它们算进 XFAIL，不另计失败。

### 受阻 290

- extract 122：`command -v mutool` 为空。这些文件是 mupdf mutool 的输入或期望输出。`make test-gs` 已通过，不在本配方里构建 mupdf。
- tesseract 81：`Makefile.am` 要链接 `unittest/third_party/googletest/googletest/src/gtest-all.cc`，发行包里没有该文件。`include_gunit.h` 需要 `gtest/gtest.h`，试编译 `list_test.cc` 报 `fileio.h` file not found。`pkg-config --exists lept` 退出码 1。没有 `*.traineddata`。`git clone googletest` 在 90 秒后超时，退出码 124。
- toolbin 45：集群脚本是 Python 2。设备没有 python2，Python 3.14.7 报 `TabError`、`IndentationError` 或 `SyntaxError`。
- zlib 19：`contrib/blast`、`iostream3`、`minizip` 的嵌套 ctest 退出码 8，`find_package` 失败。顶层测试在设置 `ZLIB_DIR` 指向本次安装的 cmake 包后已通过。
- zlib 8：puff 的 ctest 打印 `No tests were found!!!`，退出码 0，但没有 Passed 行。
- zlib 1：`minigzip.c` 被编成 `minigzip` 与 `static_minigzip`，`CMakeLists.txt` 没有 `add_test`。
- brotli 6：扩展模块能导入。pytest 读 `brotli/tests/testdata/zerosukkanooa.compressed` 时 `FileNotFoundError`。发行包没有 `brotli/tests` 样本目录。
- demos/java/gstest 3：`.classpath`、`.project`、`Main.java`。这次直接跑脚本时 `command -v java` 与 `command -v javac` 都为空，harmonybrew opt 没有 JDK。若在 `conanbuild` 里能找到 `javac`，`Main.java` 仍会因缺少随 C 库构建生成的 `NativePointer`、`GS_SPT_INT` 而编不过，脚本把这种情况记为受阻，不记失败。
- libpng 2：`pngstest`、`pngstest-large-stride` 没有单独的 automake PASS/FAIL 行。套件的那次失败是 `pngtest-all`。
- toolbin 3：`README` 指向发行包没有的 `/home/regression/comparefiles`；一个脚本启动后找不到该目录；`fuzzy.c` 用 SDK clang 编译成功，无参数运行打印 Usage 后退出码 1，比较用的 ppm 不在发行包里。

### EXTRA（不计进 508）

29 项通过（`acctest.ps`、非 CID 的 examples、ps2pdf、pdf2ps）。6 项失败：

- `all_ac1.ps`：`MKai-Medium`
- `all_ag1.ps`：`STHeiti-Regular`
- `all_aj1.ps`：`HeiseiKakuGo`
- `all_aj2.ps`：`WadaMin-Regular`
- `all_ak1.ps`：`HYGoThic-Medium`
- `article9.ps`：缺 `GothicBBB-Medium-V` 与 `Ryumin-Light-V` 后 `/rangecheck in widthshow`

这些字体不在官方 tar.gz 里。未外置商业字体，也没有把这 6 项从任何声明总数里删掉。非 CID 的 EXTRA 失败会使脚本退出码 1。

## 消费者

`test_package/test_package.c` 用 profile 里的 SDK clang 编译，`-I include -L lib -Wl,-rpath,lib -lgs`，断言 `gsapi_revision` 和一页 PNG（魔数与大小至少 500 字节）。`test_package/test.sh` 断言 `gs --version` 匹配 `10.07.1*`，再用打包后的 `gs` 渲染 PNG。共 4 个断言。

`create-508.log` 末尾（`CREATE_EXIT:0`）：

```
PASS 1/2 libgs revision=10071 product=GPL Ghostscript
PASS png bytes=3069
PASS 2/2 libgs rendered one page
PASS 1/2 gs --version
PASS 2/2 gs cli rendered one page bytes=3071
```

同一日志还记录 `package()` 打进了 `libgs.so`、`libgs.so.10`、`libgs.so.10.07` 和 `iapi.h`、`ierrors.h`、`gserrors.h`、`gdevdsp.h`。源码行是 `retrieved from local download cache`，配方 URL 仍是 GitHub 官方地址。
