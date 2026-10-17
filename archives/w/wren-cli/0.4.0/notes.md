# wren-cli 0.4.0 — HarmonyOS PC 适配记录（任务 #11988）

上游：https://github.com/wren-lang/wren-cli ，tag `0.4.0`
产物：`bin/wren_cli`（Wren 语言 CLI + REPL）+ `licenses/LICENSE`，`package_type = "application"`

## 上游构建与测试的真实形态

- 构建系统：premake 生成的 `projects/make/wren_cli.make`（**没有** automake `Makefile.am`、**没有** CMake、
  **没有** `make check`）。官方 CI 入口 `.travis.sh` = `make -C projects/make config=<X>` + `python3 ./util/test.py [--suffix=_d]`。
- 上游测试两套：
  1. `util/test.py` — 集成/语言套件。逐个跑 `test/` 下的 `.wren`（95 个文件：5 个 `// nontest` 是被 import 的
     模块夹具、3 个 `// skip:` 自身跳过）与 `example/` 的 8 个（按名跳过 animals/guess_number/skynet）。
     断言来自 `.wren` 里的 `// expect:` / `// expect runtime error:` 标记行，`test/` 全树共 220 行、实跑 216 行。
     汇总行：`All 92 tests passed (216 expectations).`
  2. `test/unit/` — 针对 `src/cli/path.c` 的 C 单测（`expectNormalize()` 52 条，grep 命中 53 处含函数定义行）。
     **官方 CI 没接它**，本配方接进 `build()`。
- 期望数对账（写进 PR 表的口径依据）：220（全树 grep） − 4（3 个 `// skip:` 文件贡献：1+2+1） = 216（运行器自报）✓

## 四个必须踩的点

1. **x86 开关与 vendored 依赖**：`projects/make/wren_cli.make` 的 `release_64bit` 配置把 `-m64` /
   `-L/usr/lib64` 用 `+=` 追加进 `ALL_CFLAGS`/`ALL_LDFLAGS`（第 41–43 行），命令行给 `CFLAGS=` 也挤不掉。
   `release_64bit-no-nan-tagging`（第 54–61 行）确实不带这两个开关，aarch64 可以直接编——但它会把
   vendored 的 `deps/wren` 与 `deps/libuv`（**1.38.0，无 OHOS 适配**）一起编进可执行文件，
   于是制品仓已发布的 `wren/0.4.0` 会以第二个制品名被重复交付、libuv 的 OHOS 移植补丁也用不上。
   → 本配方改用导出的 `CMakeLists.txt` 只编 CLI 自身 9 个源文件（清单 = 上游 `OBJECTS`，逐条列出不用 glob），
   VM 与 libuv 链制品仓发布包。
2. **RUNPATH**：`libuv` 发布的是 shared（`NEEDED = libuv.so.1`），它在 conan 缓存的依赖包目录里；
   真机上 conan 2.29 不把依赖 `libdirs` 拼进 `LD_LIBRARY_PATH`，交叉编译下 CMake 的
   `BUILD_RPATH/INSTALL_RPATH` 属性也没落地（`readelf -d` 只有 NEEDED，没有 RUNPATH）→
   `Error loading shared library libuv.so.1` + 一串 `Error relocating ... uv_*: symbol not found`。
   实测：这一条不打穿，`build()` 里的 `util/test.py` 与 test_package 的消费者套件都会红
   （本会话第一轮就是这样：`TOTAL=30 PASS=3 FAIL=27`）。
   修法两条同时走：链接期由配方把依赖 lib 目录经 `WREN_CLI_RPATH_DIRS` 传给 CMake 并显式
   `-Wl,-rpath=`；`package_info()` 再把同批目录导出到 `runenv_info`/`buildenv_info`
   （分别同 `archives/l/libe-book-tools/0.1.3` 的 libxml2 RUNPATH 与 `archives/j/jose/14` 的环境导出）。
3. **被测程序路径**：`util/test.py` 用 `realpath(__file__)` 反推源码根并固定取 `<源码根>/bin/wren_cli`
   → CMake 的 `RUNTIME_OUTPUT_DIRECTORY` 必须钉在源码根 `bin/`（含 4 个多配置变体），且必须在源码根运行。
   上游单元件 `path_test` 另放 `${CMAKE_BINARY_DIR}/upstream-unit`，避免混进 `bin/` 被打包。
4. **取证**：`util/test.py` 把逐条进度与最终汇总打在**同一行**且带 ANSI 颜色码，
   直接 `grep "tests passed"` 会拖进几十 KB 单行；先 `sed` 剥色 + 删 `(bin/wren_cli) Passed: N ...` 进度段再取。

## 依赖不是重复交付的理由（已逐文件比对）

- `deps/wren/` 与官方 `wren-lang/wren` tag `0.4.0`：`diff -rq src` 只在 `src/vm/wren_compiler.c` 差 1 行，
  且该行是注释（`// Otherwise we treat it as a token a token` → `... as a token`）；`include/` 与官方
  `src/include/` 逐文件完全一致。CLI 侧 `grep -rhoE '#include +[<"](wren|uv)[.a-z]*h[">]' src` 只有
  `wren.h` 与 `uv.h` → 链发布包 `wren/0.4.0` 与链 vendored 副本等价。
- `deps/libuv` 是 1.38.0 且不带 OHOS 适配；制品仓 `libuv/1.52.1.1` 带移植补丁，CLI 只用 `uv_*` 公共 API。

## 未做的事

- 未改上游任何源码/测试（`conandata.yml` 的 `patches: []`）；`CMakeLists.txt` 由 `export_sources()` 导出、不进包。
- 未使用任何第三方加速镜像，源只有一条 `https://codeload.github.com/...`（已核对与
  `github.com/…/archive/…` 同 sha256），且必须是单值 `url:`，否则 CI 的 `replace_url()` 不注入。
