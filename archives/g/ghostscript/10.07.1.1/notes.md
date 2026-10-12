# ghostscript 10.07.1.1

制品仓 `ghostscript/10.07.1` 只有 `bin/gs` 和资源，没有 `libgs` 与 `ghostscript/iapi.h`。本版本使用同一官方源码包，额外执行上游 `make so` 与 `make soinstall`，安装带 soname 链接的 `libgs.so`，以及 `iapi.h`、`ierrors.h`、`gdevdsp.h`。

HarmonyOS 的 `config.guess` 与 `umask 077` 问题复用已合入的 10.07.1 补丁，对应知识库 E007 与既有 HMDFS 临时目录条目，不单独立项。

`make check` 在上游 Makefile 里是 `check : default` 后接空操作，不产生用例。声明 N 按发行包里的测试文件计数，由 `upstream_tests.py` 执行并写台账。

## 计数口径

官方包 `ghostscript-10.07.1.tar.gz`（sha256 `2fc74362f9be6fae1b0a65d38fdcfd4f0b518cc3b07c5581fb661eb4d2e15251`）中，普通文件只要路径上有一段目录名正好是 `test`、`tests`、`unittest`、`unittests` 或 `gstest`，就计入。排除扩展名 `.xml`、`.po`、`.plo`、`.tpo`、`.o`、`.lo`、`.obj`、`.pyc`。跳过目录 `tiff-config`、`.deps`、`obj`、`soobj`、`generated`、`.libs`、`__pycache__`、`data` 以及点目录。`.xml` 都在 extract 的 `*.dir.ref` 夹具里。这个口径是 508。

构成：tiff 162、extract 131、tesseract 81、toolbin 51、zlib 36、libpng 34、brotli 6、freetype 4、`demos/java/gstest` 3。`examples` 与 `lib/acctest.ps` 不在这 508 项里，脚本仍会实跑，记为 EXTRA。

## 设备验证（2026-10-08）

隔离 `CONAN_HOME=/storage/Users/currentUser/work/psj/ch-gs14845`。真机访问 `github.com` 超时，同一 SHA-256 的官方包放进该隔离缓存的 `core.sources:download_cache` 后，`source()` 从本地缓存解压，没有改配方里的下载地址。

`upstream_tests.py` 在已安装的 `gs` 10.07.1 上实跑（2026-10-08 03:39，日志 `/storage/Users/currentUser/work/psj/gs14845/upstream-rerun2.log`，台账 `upstream-rerun2/ledger.txt` 共 508 行）：`UPSTREAM_ENUM=508`、`UPSTREAM_TOTAL=508`、`UPSTREAM_PASS=217`、`UPSTREAM_FAIL=1`、`UPSTREAM_BLOCKED=290`、`UPSTREAM_RESULT=REASONS_RECORDED`。`GS_VERSION_RC=0 10.07.1`。

同一次 `conan create`（`create-508.log`，`CREATE_EXIT:0`）里嵌进去的那次套件是修脚本之前的结果，libpng 的 `make check` 在 2400 秒超时、tiff 的 configure 选中了环境里坏掉的 `c++`（`/lib/cpp` 预处理失败）。那次台账不能当作声明结果。当前脚本把 libpng/tiff 的检查超时改成 7200 秒，tiff 的 `CXX` 固定为 SDK `clang++`，并在 `tests/data/As.I.Lay.Dying.ttf` 已经存在时跳过会超时的 GitHub 字体下载。

唯一失败是 `libpng/tests/pngtest-all`。`pngtest --strict pngtest.png` 重编码后按字节比较，设备链接的是 harmonybrew 的 zlib-ng。`upstream-rerun2/libpng-build/test-suite.log` 写明 `with zlib version 1.3.1.zlib-ng`，以及参考 PNG 与 `pngout.png` 不同。automake 汇总 `# TOTAL: 32 # PASS: 31 # FAIL: 1`。这是压缩字节与参考文件不一致，不是 libgs 链接失败。badpal 样本是 `FAIL(EXPECTED)`，算进 XFAIL，不另计失败。

受阻 290 项都有具体原因：extract 122 项缺 `mutool`；tesseract 81 项缺 gtest 源码、`traineddata` 和 leptonica（`git clone googletest` 超时）；toolbin 45 项是 Python 2 集群脚本，设备只有 Python 3.14；zlib contrib/puff/minigzip 28 项没有可对应的通过用例；brotli 6 项缺 `tests/testdata`；gstest 3 项没有 JDK；libpng 2 个辅助程序没有单独的 automake 结果行；toolbin 另有 README、`run_nightly`、fuzzy 各 1 项。没有把这些记成通过，也没有从 508 里删掉。

freetype 4 项通过：`meson test` 打印 `1/1 regression - freetype2:issue-1063 OK`。字体文件 `tests/data/As.I.Lay.Dying.ttf`（23120 字节）已在源码树里，不计入 508。重新下载该字体时 `github.com:443` 连接超时。

EXTRA（508 之外）：29 项通过，6 项 CID 字体失败（`all_ac1.ps`、`all_ag1.ps`、`all_aj1.ps`、`all_aj2.ps`、`all_ak1.ps`、`article9.ps`）。发行包没有这些商业字体，未外置进配方。

消费者：`test_package.c` 用配方里的 SDK clang 链接 `-lgs`，检查 `gsapi_revision` 并渲染一页 PNG；`test.sh` 检查 `gs --version` 与命令行 PNG。两项各 2 个断言，共 4。
