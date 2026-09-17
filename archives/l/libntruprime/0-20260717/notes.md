# libntruprime / 0-20260717 适配笔记

## 边界

- 本任务只处理 `libntruprime/0-20260717`，文件落点 `archives/l/libntruprime/0-20260717/`。
- Conan 包名 `libntruprime`，版本 `0-20260717`（任务命名；对应上游 release `20260717`）。
- 未修改任何其他库目录或基础设施目录。
- issue 编号未在任务正文中给出，manifest 暂记 `TBD`。
- 首轮状态：工作树已完成但**未经真机验证**，严守“验证前不提交、不建 PR”纪律。

## 版本与源码

- 上游官网：https://libntruprime.cr.yp.to ，Streamlined NTRU Prime（sntrup）格密码 KEM 微库，维护者 Daniel J. Bernstein。
- 上游版本：`20260717`（ version 文件内容；下载页最新 release；20260717 相对上一版 20241021 的主要变化：djbsort/cryptoint 升级、make 输出实现选择、`$CROSS`/`$DESTDIR` 初步支持、`configure` 识别 ppc64el 等）。
- 官方 tarball：https://libntruprime.cr.yp.to/libntruprime-20260717.tar.gz
  SHA-256 `768350cd57a9395d80545d2091ed27cd7ccf93c09b41671e4e50e053bcb0bff1`（2.7MB，已下载验算）。
- 许可证：上游置入公共领域，可选条款 `LicenseRef-PD-hp OR CC0-1.0 OR 0BSD OR MIT-0 OR MIT`；配方按其中 MIT 条款声明 `license = "MIT"`，许可证原文随包安装到 `licenses/license.md`（上游 `doc/license.md`）。
- 构建系统：djb 系 `./configure`（python3 脚本）+ `make`，与已入库 `libcpucycles/20260625` 同框架（`compilers/default` 编译器选择、`build/<arch>`  Leaf 构建树、全 symlink 布局）。

## W0 依赖检查

- 直接依赖：`librandombytes`（6 个 `crypto_kem/*/factored/kem.c` 调用 `randombytes()`；共享库链接行 `-lrandombytes`）。
- `libcpucycles` 仅被 `command/ntruprime-speed.c`（benchmark）引用，库与常规测试均不依赖，不处理。
- 仓库现状：`libcpucycles/20260625` 已入库但是否为已发布制品仓包首轮无法确认；`librandombytes` 在仓库内**无任何配方**。
- 决策（单 PR 单库约束下）：不声明任何 Conan `requires`（避免 PF4/R36 门禁失败），改为把官方 `librandombytes-20240318`（https://randombytes.cr.yp.to/librandombytes-20240318.tar.gz ，SHA-256 `fae6fb839096e54ce8abb6dc8ae46ed67b02034474e83cbda088eddd2e584641`，30KB）作为第二源码在配方内私有构建（libseqlib 式多源 vendor 前例），静态捆绑进 libntruprime。详见下节。
- python3：构建与测试均需要（configure 本身即 python3 脚本），由真机/HMBS 工具链提供（`HMBS_PYTHON3` 及 PATH），不作为 Conan 依赖。

## OHOS 适配设计（conanfile.py build 流程）

1. **编译器注入（复用 libcpucycles 结论）**：上游 configure 不读任何环境变量，编译器唯一来源是源码树 `compilers/default`（逐行 `--version` 探测，首个可用者胜出）。build() 把 `tools.build:compiler_executables.c` 解析出的 OHOS clang 按上游原 flags（`-Wall -fPIC -fwrapv -Qunused-arguments -O2`）前置到**构建缓存副本**，上游原有候选行保留作 fallback；零补丁。找不到可用编译器时 fail closed（R33）。
2. **vendored randombytes 私有构建**：先对其源码执行同样注入 + `./configure --host=arm64` + `make -j1`，随后删除其产物目录中的 `.so*`（只留 `.a`），使主构建的 `-lrandombytes` 经 `LIBRARY_PATH` 必然解析到静态包，对象被直接链入 `libntruprime.so.1`（无新增 DT_NEEDED）；静态包则在构建后用 `ar r` 把解出的 randombytes 对象并入 `libntruprime.a`。消费者只链 `-lntruprime`。
   randombytes 自身运行时三选一（getrandom/getentropy//dev/urandom，`__attribute__((constructor))` 探测），musl/OHOS 均具备对应能力，具体选中项以真机 `randombytes_source()` …（注：库未导出调用入口，该行为由 KEM 测试间接验证）为准，记录待回填。
3. **只构建显式目标**：`make -j1 package/lib/libntruprime.a package/lib/libntruprime.so.1 package/bin/ntruprime-test result-impl`。`make` 默认全量目标会构建 `ntruprime-speed`（需 libcpucycles，无包可用）故不执行；`sntrup*` 命令行工具与 man 页不打包（纯库包，与 libcpucycles 同口径，故无 `commands.json`）。
4. **跳过 `make install`**：`scripts-build/install` 与 libcpucycles 同款 `tempfile` + setgid + umask 077 模式，hmfs 上存在已知 PermissionError 风险；改为收集上游“供分发者打包”文档指定的 `build/<arch>/package/{include,lib}`。`--prefix` 仅为满足 configure 参数要求传入。
5. **`.so` 双名无 symlink**：`package/lib/libntruprime.so → .so.1` 上游用 `ln -s` 生成；hmfs symlink 能力未经证实，打包时改为复制同内容常规文件（SONAME 与 linker 名同时可用）。若真机证实 symlink 可用也不改回（复制文件兼容性最强）。
6. **TMPDIR**：复用 libcanard 式 `_ensure_writable_tmp`（注入的 TMPDIR/TMP/TEMP 优先，否则 build 文件夹下 `.hmbs-tmp`），`configure` 的 `TemporaryDirectory` 与测试子进程均不碰系统 `/tmp`。
7. **R32**：`validate()` 与其余 os 判断一律用 `in ("Linux", "OHOS")` 成员测试。

## 上游测试入口（双口径台账）

- 常规测试主力 `command/ntruprime-test.c`：`main()` 无参数运行时依次调用 **126** 个 `test_*` 函数（verify 6、hash/hashblocks 2、decode 31、encode 37、sort 2、core 42、kem 6；另有 30 个 `test_verify_*_impl` 内部派发，不单计）。每个函数内部失败即 `fail()` 打印并置位，最终 `all tests succeeded` + exit 0（失败则 `some tests failed` + exit 100）。
- 配方内判定（防“静默通过”）：exit 0 且输出含 `ntruprime version`/`ntruprime arch`（证明真实二进制执行）且含 `all tests succeeded`，且不含 `some tests failed`/`failure:`，才记 `passed`；`discovered=executed=126`。结果打印 `HMBS_UPSTREAM_TEST_RESULT` 并落盘 `res/upstream_test_result.json`（test_package 在包缓存命中时重发，libcanard 模式）。
- 未运行项（PR 补充说明如实披露）：
  - `ntruprime-fulltest` 并行编排（文档记载约 529 core-min；`jobs=1` 约束下远超构建超时预算）——常规测试已覆盖其全部 126 个函数（fulltest 只是加参数分片重跑 + 下述 valgrind pass）。
  - valgrind TIMECOP 数据流测试（`valgrind_multiplier` 模式）——OHOS 无 valgrind，无法补齐。

## 鸿蒙专项 / test_package 设计

- `test_package/test_ntruprime.c`：TAP 风格 8 检查——6 参数集各一次 keypair→enc→dec 会话密钥往返比对（`memcmp`），sntrup1277 两次封装密文不等（随机化证据）+ 各自解封正确。输出 `ok N - ...` 行由 conanfile 解析计数生成 `HMBS_TEST_PACKAGE_RESULT`（libcanard 模式：`executed/passed/discovered/passedCount` 实测填写）。
- 上游测试修改：无（`test_package` 为仓库规范要求的消费者视角测试，非上游测试修改；上游测试以配方 build() 内真实运行集成）。
- 补全测试：无（上游已有 126 用例覆盖；8 项消费者检查不属于补全上游缺失）。

## 风险与待真机验证项

1. `build/<arch>` 目录 symlink 树（configure 的 `dirlinksym`/`copytree` 全 symlink 布局）在 hmfs 上的可用性——同框架 libcpucycles 有真机成功先例，预期通过。
2. `package/lib/libntruprime.so` symlink 规则在 `make` 显式目标中的行为（仅测试二进制链接需要它；产物收集不依赖它）。
3. vendored randombytes 在 OHOS 上选中的熵源（getrandom 预期）及 KEM 测试实际耗时。
4. 全量构建耗时（`-O2`、`-j1`，约数百编译单元）是否在 3600s 默认预算内；超时则按仓库 `ci/config/build_timeouts.txt` 流程申请覆盖。
5. `ar`/`ranlib` 在真机 PATH 的可用性（配方按 `llvm-ar`→`ar` 顺序探测）。
6. `config_options` 中 `settings.os == "Windows"` 为 Conan settings 字符串比对（R32 约束的是 `os` 平台能力判断用成员测试；此处为 options 修剪的常规写法，与 libcanard 一致）。

## 真机失败定位（2026-09-14 upstream_test，待下轮预检验证）

- 首轮症状：`ntruprime-test` 启动即大量 `Error relocating ... symbol not found`（kem 6 参数集 keypair/enc/dec、sort、hashblocks 全缺），exit=127，126/126 判失败；静态包日志仅见 `bundled 4 vendored randombytes objects`。
- 首轮修复（conanfile.py，未动测试口径）：`_cc_flags()` 按家族选用上游原样 flags；拆两阶段 make，中间把 `.so` 归一化为常规文件；新增 `_verify_library_completeness` 硬门禁（ofiles≥50、零空 `.o`、nm 导出检查、`ar t` 含 kem）。
- 第二轮回来的关键新证据：远端 raise 行号变为 line 372，与本工作树当前行号一致，证明真机确实运行了首轮修复后的配方；但失败指纹完全相同。这意味着门禁已放行（nm 曾在 `.so.1` 里见到符号）而 loader 仍找不到——首轮 substring 匹配可能误命中未定义条目，或门禁与测试之间文件发生变化，或 loader 装载了别处的文件。
- 本轮改动（仍不碰测试口径）：① nm 检查改为严格解析（逐行取 `type/name`，只要已定义符号，`name` 精确相等才计数；完全解析不出时警告跳过而非基于解析器失败）；② 门禁记录 `.so.1` sha256，失败时 `_lib_forensics` 把“门禁后是否被重建”（digest 对比）、lib 目录文件尺寸、nm 已定义符号统计、测试二进制 DT_NEEDED 全部拼进 `reason`（聚焦摘要必带 reason，可穿透日志省略）；③ 其余构建流程不变。

- 第三轮回来的决定性证据（forensics 穿透省略生效）：`libfiles=[.a:924906,.so:403776,.so.1:403776]`、`so1sha==gate`（`rebuilt=False`）、`nm_defined=911 nm_kem=66 nm_kem761=True nm_sort=True`、`needed=['libc.so','libntruprime.so.1']`——门禁验证过的同一文件在测试时仍报符号缺失。因此被装载的不可能是该文件，`DT_NEEDED libntruprime.so.1` 在真机 loader 上下文里解析到了树外另一个同名文件（LD_LIBRARY_PATH 未生效或另有 impostor）。
- 本轮改动（仍不碰测试口径）：① 测试运行时新增 `LD_PRELOAD=<libdir>/libntruprime.so.1`，把装载钉死在门禁验证过的构建树文件（musl 对重复装载去重，解析原本正确时即为 no-op；只改 harness 环境，不改二进制、不断言、不跳用例）；② forensics 追加 `ldpath/preload` 回显、测试二进制 RUNPATH/RPATH 行、7 个系统目录的同名文件扫描（`impostors=`），若 preload 后仍失败即可定位 impostor 位置。
- 源码级确认（已下载官方 tarball 解包审计）：`scripts/compile` 编译失败时只生成空 `.o` 且返回成功，make 永不失败；`scripts/staticlib`（`ar cr ofiles/*.o`）与 `scripts/sharedlib`（`ofiles/*.o -lrandombytes`）在空 ofiles 下仍产出仅含 randombytes 符号的库；`compilers/default` 上游 clang 行含 clang 独有的 `-Qunused-arguments`（gcc 行无）；测试二进制依赖 `package/lib/libntruprime.so`（由 `ln -s` 规则生成）。

## PR 草稿

- `.hmbs/pr-body.md` 已按 `templates/积分赛事PR模板.md` 全章节填写；适配路径选**路径 A（基础适配）**；用例总数为源码审计事实（上游 126、新增 8），通过率待真机 evidence 轮回填；申请人 `yinuoguo`、队伍 `干`。

## 真机失败定位（2026-09-14 upstream_test 第4轮：IFUNC 路线，待下轮预检验证）

- 上轮（LD_PRELOAD 钉死）无效的决定性证据：预检仍 126/126 exit=127，且 forensics 显示 `preload=<libdir>/libntruprime.so.1` 已生效、`so1sha==gate`（`rebuilt=False`）、`nm_defined=911 nm_kem761=True nm_sort=True`、`needed=['libc.so','libntruprime.so.1']`、`rpaths=[]`、`impostors=[]`。同一文件、符号存在、装载路径正确、树外无同名文件——树外错装假设被证伪，上一周期三轮的文件身份路线全部作废。
- 重新审计上游源码（官方 tarball 解包）发现新根因候选：`scripts-build/dispatch` 对全部公开 `ntruprime_*` 符号默认生成 `__attribute__((ifunc))` 解析器（`dispatch/ifunc==1` 时）；`dispatch/ifunc.do` 的探测只是“编译器接受 ifunc 属性 + readelf 能看到 IFUNC 符号”，从不验证 loader 能否装载。OHOS/musl 无法重定位 `STT_GNU_IFUNC`，于是出现“nm -D 显示已定义（type i 也被计为 defined），loader 却报每个公开符号 not found”的矛盾——与本轮 `911 个已定义 yet 全量缺符号` 完全吻合；缺的 kem/sort/hashblocks 恰好全是 dispatch 分发的公开符号。
- 本轮改动（测试口径不变，仍 126 用例）：① 主 configure 增加上游官方开关 `--no-tryifunc`（`dispatch/ifunc` 恒为 0，`dispatch-auto` 回落到 constructor-pointer 普通 FUNC 包装，与 musl 兼容；vendored randombytes 无 dispatch 不受影响）；② 移除上一轮的 `LD_PRELOAD` 钉死（已证伪，只留 `LD_LIBRARY_PATH`）；③ `_nm_defined_symbols` 改为返回 `name->type` 映射，门禁对 `ntruprime_kem_sntrup761_keypair` / `ntruprime_sort_int32` 显式拒绝 `i/I`（IFUNC）类型并 fail closed；④ forensics 新增 `nm_ifunc` 计数与两符号的类型后缀（`nm_kem761=True:T` 形式），下一轮 reason 可直接验证 IFUNC 是否清零。
- 证伪设计：若下轮 `nm_ifunc=0` 且测试通过，即确认 IFUNC 根因；若 `nm_ifunc=0` 仍失败，则 IFUNC 假设被证伪，需另寻路线；若仍 `nm_ifunc>0`，说明开关未生效，需检查 configure 参数透传。

## 真机失败定位（2026-09-14 upstream_test 第5轮：主错误被截断，待下轮预检验证）

- 上轮（--no-tryifunc）部分生效的证据：`nm_ifunc=0`、`nm_kem761=True:T`、`nm_sort=True:T`（开关透传成功，IFUNC 已清零），但仍 126/126 exit=127 且 `ran=False`。IFUNC 假设被证伪（`nm_ifunc=0` 仍失败），上一周期的符号类型路线作废。
- 重新审计上游源码（官方 tarball 解包，上一轮在本机完成）发现盲区：musl 先打印主错误（`Error loading shared library ...`，输出头部），再逐符号打印 `Error relocating ... symbol not found`（输出尾部）。配方此前只记录 `output[-4000:]`（尾部），四轮从未见过头部；若 `libntruprime.so.1` 自身加载失败（自身 DT_NEEDED 缺失、错 arch 混入），loader 会对该库的每个符号报 not found——与“nm 可见 911 符号、loader 全量找不到”完全吻合，且首行被截断的 `uprime_hashblocks_sha512: symbol not found` 之前很可能就有一行主错误被省略号吞掉。
- 本轮改动（测试口径不变，仍 126 用例）：① 同时记录输出头部 `output[:3000]` 并把头部前 600 字符拼进 `reason.head`（聚焦摘要必带 reason，主错误下轮可见）；② `_lib_forensics` 新增 `libneeded=`（.so 自身 DT_NEEDED）、`machine=`（.so 与测试二进制的 ELF Machine）、`dlopen_probe=`（ctypes 显式路径 dlopen+dlsym，同 loader、绕过全部搜索路径：失败则文件自身不可装载且错误信息即主错误，成功则隐式解析必拿到别处文件）；③ impostor 扫描追加全部 `LD_LIBRARY_PATH` 条目（此前只扫 7 个系统目录，漏了 `usr/local/lib` 与 magic-cli 路径）；④ 新增 `_verify_elf_machine_and_needed` fail-closed 门禁（arm64 下 Machine 非 AArch64 直接失败；DT_NEEDED 含 randombytes/cpucycles 或绝对路径直接失败）；⑤ harness-only 加固：configure 生成的 `command/link`（构建缓存副本，非上游源码）嵌入绝对 RPATH 指向构建树 package/lib，DT_NEEDED 解析不再依赖环境变量透传（`LD_LIBRARY_PATH` 仍保留，双保险；测试二进制不打包，不影响产物）。
- 证伪设计：若下轮 `head=` 含 `Error loading shared library`，即确认“.so 自身加载失败”路线，按其具体原因（缺 NEEDED/错 arch/其他）修；若 `dlopen=ok` 但共享运行仍失败，则隐式解析拿到别处文件，`impostors=` 须给出位置；若 RPATH 后直接通过，则为环境变量透传问题。
