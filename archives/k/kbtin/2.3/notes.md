# kbtin 2.3 适配笔记

## 编译环境

- 构建系统：CMake（上游原生，无 autotools / meson 层）
- 编译器：clang（HarmonyOS PC 真机，aarch64，HarmonyOS 交叉配置）
- Conan：2.29.1；CMake：4.1.2（`/data/service/hnp/bin/cmake`，由 VirtualBuildEnv 注入）
- 真机 worktree：`~/qzy/hw-3-kbtin-2.3`，分支 `feat/kbtin-2.3`，基线 `c611f7d61b`
- CONAN_HOME：`~/tmp/ch/home-hw-3-kbtin`（与 `ci/conan/profiles/ohos-aarch64` 同源配置）
- 构建日期：2026-09-27

## 上游盘点

- 仓库：https://git.sr.ht/~kilobyte/kbtin ，tag `v2.3`
- 源码包：`https://git.sr.ht/~kilobyte/kbtin/archive/v2.3.tar.gz`
  sha256 `11c566630fe2c16cfca893bbe6e922a7a7eece7cfd1d15c00e76791525e46288`
  （sr.ht 归档名必须带 `v` 前缀，`archive/2.3.tar.gz` 实测 404。）
- 与 Debian 池件 `kbtin_2.3.orig.tar.gz`（214443 B，sha256 `fef06b64…e08e`，与
  `kbtin_2.3-1.dsc` 的 Checksums-Sha256 一致）去顶层前缀后逐文件比对 **268/268 sha 全等**
  ⇒ 同物坐实；conandata 只写官方 URL，池件 URL 不进仓。
- 组件：单可执行文件 `KBtin`（`add_executable(KBtin …)`，CMakeLists.txt:170）＋
  测试辅助 `ttyrec2ansi` / `get-utf8` / `kbitr`；无库产物、无 pkg-config 导出。
- 可选编译开关：`MCCP`（依赖 zlib）、`SSL`（依赖 gnutls）、`ICONV`（缺失即
  `FATAL_ERROR`，CMakeLists.txt:68 是硬门，故 libiconv 是必需依赖而非可选）。

## W0 依赖核验（全部命中已发布二进制）

- 直接依赖：`libiconv/1.17.1`、`zlib/1.3.1`、`gnutls/3.8.10`；
  传递闭包：`nettle/3.10.2.1`、`libtasn1/4.21`、`libgcrypt/1.11`、`libgpg-error/1.55`、
  `gmp/6.3.0`、`libunistring/1.0`，共 10 个 package_id。
- 判据用全新一轮 `conan install --build=never`（换新 CONAN_HOME，避免本地缓存把
  "已装"误读成"已发布"），11/11 从远端取到；再用配方仓
  `…/packages/<pid>/revisions/<prev>/files/conaninfo.txt` 抽查平台指纹，
  `os=OHOS` 与本机 profile 一致 ⇒ 依赖面为"已适配可用"，非仅配方存在。
- 未 `tool_requires` cmake：仓内 4 个既有 CMake 配方零个这么做，设备侧 cmake 由 hnp 提供，
  自行引入反而触发 R36 依赖面扩大。

## 关键适配点 1：CMake 的 RPATH 变量机制在 HarmonyOS 交叉配置下静默失效

这是本包唯一的实质失败域，也是改前/改后对照最完整的一条。

- 症状（改前，日志 `~/tmp/uc2/hw-3/kbtin/create-204630.log`）：
  `cmake.test()` 阶段 `2% tests passed, 88 tests failed out of 90`，
  失败的 88 条全部是经 `tests/runtest.sh` 调 `../KBtin` 的语料用例，
  仅 #10（`#end without sessions`）与 #90（`kbtree_itr`，不链外部共享库）通过；
  直接运行 `build/Release/KBtin` 报 `Error loading shared library libgnutls.so.30`。
- 当时的写法已经"按 CMake 文档做了"：`tc.cache_variables["CMAKE_BUILD_RPATH"]` 填入
  10 个依赖的绝对 lib 目录，且 `CMAKE_SKIP_BUILD_RPATH=OFF`、`CMAKE_SKIP_RPATH=NO`。
  该轮构建目录（`~/tmp/ch/home-hw-3-kbtin/p/b/kbtin3a0b20e598654/b/build/Release`）留存的
  三项读数是决定性的：
  1. cmake 命令行确实带 `-DCMAKE_BUILD_RPATH="/storage/.../p/libic…/p/lib;/storage/.../p/zlib…"`；
  2. `CMakeFiles/KBtin.dir/link.txt` 中 `rpath` 出现次数为 **0**；
  3. `readelf -d KBtin` 只有 `NEEDED libz.so / libgnutls.so.30 / libc.so`，
     **既无 RPATH 也无 RUNPATH**。
- 根因（本机实测，非推断）：该轮 `CMakeFiles/*/CMakeSystem.cmake` 写
  `set(CMAKE_SYSTEM_NAME "HarmonyOS")`，而 CMake 4.1.2 的
  `Modules/Platform/` 下只有 `OHOS.cmake`（内容仅 `include(Platform/Linux)`）
  与 `Linux.cmake`、`Generic.cmake`，**没有 `HarmonyOS.cmake`**。
  平台模块未加载 ⇒ `CMAKE_SHARED_LIBRARY_RUNTIME_C_FLAG` 从未被设置
  （该变量只在 `Platform/Linux.cmake:2` 里赋 `"-Wl,-rpath,"`），
  CMake 的整套 RPATH 装配逻辑因此静默产出空集 —— 变量存在、值也进了缓存，
  但没有任何一处会把它翻译成链接参数，且不报错、不告警。
- 修法：绕开 CMake 的 RPATH 机制，把绝对路径以裸链接参数形式交给链接器 ——
  `tc.extra_exelinkflags` 与 `tc.extra_sharedlinkflags` 各追加
  `-Wl,-rpath,<dep>/p/lib`（conan 把它们写进 `CONAN_EXE_LINKER_FLAGS_RELEASE`，
  由 `CMAKE_EXE_LINKER_FLAGS` 进入 link.txt，不经过 CMake 的平台 RPATH 逻辑）。
- 改后（日志 `create-210006.log`）：`link.txt` 含 `-Wl,-rpath,…` 条目，
  `readelf -d` 显示 `RUNPATH` 列出 9 个依赖 lib 目录，
  `100% tests passed, 0 tests failed out of 90`，
  安装副本 `bin/KBtin` 同样带 RUNPATH ⇒ `test_package` 无需注入 `LD_LIBRARY_PATH` 即可运行。
- 边界与反例：这只解决"依赖库在包外绝对目录"的场景。若包本身产 `.so` 供插件 dlopen，
  仍需 E504（install 期 RPATH_CHANGE 字节级改写）与 E505（LD_LIBRARY_PATH 压过 DT_RPATH）
  的处置；本包无库产物，故两条不触发，仅按 §12.38 保留
  `CMAKE_SKIP_INSTALL_RPATH=ON` ＋ 打包时用构建树原件覆盖 `bin/KBtin`，
  使安装副本与已验证原件字节一致。

## 关键适配点 2：HMDFS 默认 660 让上游脚本失去执行位（E543 家族）

- 上游根目录 6 个脚本被构建流程直接执行：`get_version` 在 configure 期由
  `execute_process` 调用（决定版本号注入），`make_commands`、`make_protos`、`a2html`、
  `help2ansi`、`fixmanual` 在构建期生成 `KBtin.6` / `KBtin_help.gz` / `manual.html`。
  HMDFS 新建文件默认 660 ⇒ 无执行位，configure 期即失败。
- 处置：`build()` 第一步对存在的上述脚本补可执行位；configure 期所需的
  `get_version` 若缺失则直接抛 `ConanInvalidConfiguration`，不让它退化成"版本串为空继续构建"。
  真机日志逐条命中：`E543 chmod +x: get_version / make_commands / a2html / help2ansi / fixmanual`。

## 关键适配点 3：数据与手册的安装位置

- 上游把 gzip 后的手册页 `KBtin_help.gz` 装到 `DATA_PATH`，运行时读取。
  配方用 `-DCMAKE_INSTALL_DATADIR=res`、`-DCMAKE_INSTALL_MANDIR=res/man`
  将其固定进包的 `res/kbtin/`（实测 `Packaged 1 '.gz' file: KBtin_help.gz`）。
- 消费者测试按 `cpp_info.resdirs` 定位该文件并真实 gzip 解压读字节数
  （`KBtin_help.gz 解压 OK: 73669B`），不用 `stat` 存在性冒充验证，
  也不使用 `self.user_info`（conan 2 的 `ConanFileInterface` 无该属性，
  真机报 `AttributeError` 后更正）。

## 关键适配点 4：上游测试的运行条件与判定口径

- 89 条语料用例由 `tests/CMakeLists.txt:21` 的 foreach 注册，命令是
  `tests/runtest.sh`，脚本内部以相对路径调用 `../KBtin` 与 `./get-utf8`
  ⇒ `cmake.test()` 的工作目录必须是 `build/tests`（CMake 默认如此，
  换成安装树或 build 根执行会整批假失败，本包改前的 88 条失败里就混有这一类噪声）。
- `runtest.sh:9` 的调用形态是 `KBtin -p -q <setup-file>`，
  新增消费者测试沿用同一形态，不另造入口。
- `runtest.sh` 用 `which valgrind` 探测决定是否附加 `--error-exitcode=1`。
  本机 PATH 实测无 valgrind（`which valgrind` 无命中）⇒ 判定口径保持上游默认，
  既不因缺工具降级，也没有被环境偷偷加强。
- 制表口径：`make` 的 jobserver 在 HMDFS 上报
  `jobserver mkfifo: … Operation not permitted`（无害告警，构建与测试照常完成），
  故并发固定 `-j2`、测试阶段 `-j1`，不试图消除该告警。

## 签名

`package()` 对包内可执行文件用 `binary-sign-tool sign -selfSign 1` 逐件自签；
工具缺失时抛 `ConanInvalidConfiguration` 而不是产出"装好但跑不了"的包。

## 测试账本（§10.1 五维）

| 维度 | 数 | 来源 |
|---|---|---|
| N_static | 90 | 上游 `tests/CMakeLists.txt` 注册入口逐项数：89 条 foreach 语料 ＋ 1 条 `kbtree_itr` |
| N_registered | 90 | 本轮 `ctest` 输出 `out of 90` |
| N_executed | 90 | `create-210006.log`：`100% tests passed, 0 tests failed out of 90` |
| 未执行 / 跳过 | 0 | 无条件编译剔除、无缺资产、无预期失败项 |
| N_consumer | 6 | `test_package/kbtin_behavior.py`，逐字语料断言 ＋ 1 项随包 gzip 真实解压 |

- 消费者 6 条取自官方 `tests/data/*.in/.out` 语料（`#shell`、`#strw`、`tabbed_args`、
  `#sys`、递归守卫、`#end`），以使用者身份运行已安装的 `KBtin`，
  逐字节比对 stdout；真机读数 `KBtin consumer suite: PASS=6 FAIL=0`。
- 申报分双口径：执行项 90/90（100%）；静态全量 90/90，两者分母相同，无删除用例。

## 已知限制：上游的第二个命令名与第二份手册页在 HMDFS 上被大小写折叠

- 上游不装库、只装一个可执行文件，但**故意提供两个入口名**：
  - `CMakeLists.txt:185-189` 用 `add_custom_command(OUTPUT kbtin …  COMMENT "SYMLINK KBTIN")`
    ＋`add_custom_target(symlink_kbtin ALL DEPENDS kbtin)` 生成**指向 `KBtin` 的软链 `kbtin`**，
    再由 `install(FILES ${CMAKE_BINARY_DIR}/kbtin DESTINATION bin)` 装进 `bin/`；
  - `install(FILES KBtin.6 kbtin.6 DESTINATION ${CMAKE_INSTALL_MANDIR}/man6)` 同时装两份手册。
- 本机文件系统（HMDFS）大小写不敏感 ⇒ `kbtin` 与 `KBtin`、`kbtin.6` 与 `KBtin.6` 是同一个路径，
  软链无法与自己的目标共存。逐字读数（本轮真机，包 `c1a03404d4bc711b794caadff25c2cdba1554833`）：
  - 构建树：`ls -l build/Release/KBtin build/Release/kbtin` 两行**同为 1264256 字节普通 ELF**，
    没有任何一行是 `lrwxr…`（软链未成立）；
  - 安装树 `bin/` 仅 `KBtin` 一个文件；
  - 包内清单实测为
    `bin/KBtin`、`licenses/COPYING`、`res/kbtin/KBtin_help.gz`、`res/man/man6/KBtin.6`、
    `share/doc/kbtin/manual.html` ⇒ 上游清单里的 `bin/kbtin` 与 `man6/kbtin.6` **未随包交付**，
    且 CMake 与 conan 全程零告警（静默折叠）。
- 影响与取舍：`KBtin` 本体功能完整（上游 90 条语料用例与 6 条消费者断言全部通过），
  少的是"用小写名调用"这一别名入口与对应手册页。HMDFS 的折叠是文件系统属性，
  不是配方缺陷，也没有在不改上游命令名的前提下同时交付两个仅大小写不同文件名的办法；
  因此**如实记为平台限制，不做改名伪交付**（改名会偏离上游契约；本包主入口按上游主名 `KBtin`
  交付，`commands.json` 的 `binary: true` 也以该二进制为准）。需要小写入口的使用方，可用 shell
  别名或自行 ln -s（在同盘上同样会被折叠）。
- 交叉影响提示：同一条折叠也会波及 `install(FILES KBtin.6 kbtin.6 …)`，
  即本包的**手册页只交付了一份**；`res/man/man6/` 下的实测清单已在上文列出。
---

**编译结束**: 2026-09-27 21:15
**最终状态**: built
