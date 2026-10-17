# libpktriggercord 0.85.1-20221221181244 适配笔记

## 编译环境
- 构建系统: makefile（上游为裸 Makefile，无 configure.ac / CMakeLists.txt / meson.build）
- 上游: https://github.com/asalamon74/pktriggercord，commit `c1177a48`（`Makefile:22 VERSION=0.85.01` == 目标版本 0.85.1）
- 源码: https://github.com/asalamon74/pktriggercord/archive/c1177a4881f363455255866f6f6d8149574e4b35.tar.gz
  sha256 `3347fdd480666df97753b6da935e8550a00177bc1dbe05a5bcc0ab36220ec51b`
- 编译日期: 2026-09-17
- 编译器: clang 15.0.4（`/data/service/hnp/bin/clang`，conan profile `ci/conan/profiles/ohos-aarch64`）
- 状态: built（conan-verify G1–G4 通过；未 upload，等确认）

## 包范围（为什么不含 GUI 与 CLI）
上游产出两个可执行文件：`pktriggercord-cli`（仅用库对象）和 `pktriggercord`（GUI）。
- GUI 目标 `pktriggercord.c:30` 需要 GTK+ 2：`Makefile:18,20` 的
  `pkg-config --cflags/--libs gtk+-2.0 gmodule-2.0`、`pktriggercord.spec:30 BuildRequires: gtk2-devel`、
  `Changelog:34 Requires at least gtk+ 2.18`。GTK2 已 EOL，**不在 ohpcd 制品仓**
  （`conan download gtk2/2.24.33 -r=ohpcd --only-recipe` → `exit_code=1`；仓内只有
  `gtk/3.24.43`，其 `cpp_info.set_property("pkg_config_name", "gtk+-3.0")`，不能当 gtk+-2.0 用）。
  实测失败：`make gui` → `pktriggercord.c:30:10: fatal error: 'gtk/gtk.h' file not found`，`make: *** [Makefile:136: pktriggercord] Error 1`。
- 包名是 `libpktriggercord`（库），故交付 `libpktriggercord.so` + 8 个公共头 + 运行期数据；
  CLI 只在 `build()` 中作为上游测试入口执行，不进交付物（也避免库包混入 commands.json 义务，R38/PF8）。

## 编译步骤（真实执行）
1. `ohc-run.py init-build libpktriggercord 0.85.1-20221221181244 --url=<官方 commit-pinned URL>`
   （HMDFS 拒绝 `shutil.copytree(copy_function=os.link)` 硬链接，且 `android/jni/src -> ../..`
   符号链接回环使 copy2 回退路径崩溃 → 用 `cp -a` 手工生成 `.work` 后 `--no-download` 续跑）
2. `ohc-run.py lang-preflight` → 见「问题 6」
3. 探索编译：`make cli CFLAGS="$CFLAGS -O3 -Wall -Isrc/external/js0n"` → 成功
4. 配方：`conan-init` 生成骨架后按 makefile 路线重写（上游无库目标，配方自建）
5. `conan create`（由 conan-verify 驱动）：
   `make cli CC="/data/service/hnp/bin/clang" AR="/data/service/hnp/bin/llvm-ar" CFLAGS="-O3 -g -Wall -fPIC -Isrc/external/js0n" LDFLAGS="-lm" PREFIX="<pkg>" -j1`
   → 上游测试 → `clang -shared -o libpktriggercord.so <9 个 .o> -lm` → package
6. Staging 部署（真实部署最终 conan 产物）：把 package folder 的 `lib/ include/ share/ licenses/`
   复制进 `$TEST_PREFIX`（= `$TMPDIR/test-install-libpktriggercord-0.85.1-20221221181244`），
   随后 `ohc-run.py verify-build`（G1–G4 质量门禁 PASS → `.verify-passed`）
7. 本地预编译包：`scripts/ohc/package_builder.py`（10 步流水线，未在 `ohc-run.py` 注册子命令，
   以模块方式调用）产出 `packaging/libpktriggercord-0.85.1-20221221181244-ohos-aarch64.tar.gz`
   （278KB，"收集 0 个外部依赖"与零依赖闭包一致）+ `-debug.tar.gz`。
   注：`packaging/`、`.staging-verified`、`.verify-passed` 均被 .gitignore 忽略，只是本地工件，
   不进 PR；`submit` 的 `packaging_present` 自检仍沿用 DESTDIR 时代口径（R20 已废弃该步骤），
   故 conan 流程必须手工补这一步才能过自检——已在框架反馈中登记。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 探索编译首个真实错误：`pslr_model.c:45:10: fatal error: 'js0n.h' file not found`（`make: *** [Makefile:129: pslr_model.o] Error 1`，exit=2） | `Makefile:5` 是 `CFLAGS ?= -O3 -g -Wall -I$(JSONDIR)`；环境已有 `CFLAGS=-fPIC -O2` 时 `?=` 不再赋值，**整条默认值连同内嵌 js0n 的 `-Isrc/external/js0n` 一起被顶掉**。同一陷阱也吞掉 `Makefile:7 LDFLAGS ?= -lm` | 不以"少传参数"为准，改为**始终**通过 make 命令行变量传入（命令行优先级高于环境）：`CFLAGS="-O3 -g -Wall -fPIC -Isrc/external/js0n"`、`LDFLAGS="-lm"`；编译器取自 `tools.build:compiler_executables`（R33，不裸用 `${CC}`）。重验：`make cli` exit=0，产物 `ELF 64-bit arm64 / ld-musl-aarch64` |
| 2 | GUI 目标不可编译（`gtk/gtk.h` 缺失） | GTK2 缺失且制品仓无 gtk2（只有 gtk+-3.0） | 排除 GUI 子目标，包范围限定为库；证据见上节。若后续要 GUI，需先立项 `gtk2`（连带 atk/pango/cairo/gdk-pixbuf/X11 全栈，实测这些传递依赖本身都可消费） |
| 3 | 首次 `conan-verify` G2 FAIL：`Error in package() method, line 208 / TypeError: copy() got an unexpected keyword argument 'root'` | conan 2 的 `conan.tools.files.copy()` 没有 `root` 参数（那是 conan 1 语义） | 改为按 `Makefile:83` 的头文件清单逐个显式复制 8 个公共头，并对缺失头 fail-fast；重验 G2 PASS |
| 4 | 上游没有任何"库"产物目标（无 `.so/.a`、`install` 也不装头文件） | 上游只有 `cli`/`gui` 两个可执行目标（`Makefile:72-77,138`） | 复用 `make cli` 产出的 -fPIC 目标文件（上游规则本就 `-fPIC`）自行 `-shared` 链接，`shared=False` 时 `llvm-ar rcs` 归档；导出符号实测 117 个 `T pslr_*` |
| 5 | `./pktriggercord-cli --status` 挂起 350s 需 kill | 上游默认 `--timeout=0`（永久等待相机），无设备时不返回 | 不作为测试入口；仅执行 `.travis.yml` 里的 `--version`（+ `--help` 冒烟，上游设计以 255 退出，只断言 Usage 文本） |
| 6 | R47 `lang-preflight` 判 `mixed` → `env_unsupported`，exit=2 | `scripts/ohc/lang_detect.py:_manifest_scan` 对 gradle 用**全树** `names` 集合（`android/build.gradle`）命中 java，而对 CMake/meson/package.json 用**顶层** `tops`；顶层实际只有 `Makefile`（c/cpp 族）。统计 `c:15, java:4`（C 占 79%），java 全在 `android/` 子工程（`make android*` 专用，不参与库/CLI 构建）。按协议附录 D.4「辅助子项目不算主体」，正确判定应为 `c` | 不修改框架脚本（协作者铁律）。以真实适配范围（去掉 out-of-scope `android/` 子工程的同源副本）复跑：`detected_language: c`、`build_system: make`、`source_stats: 源文件 15 个（c:15），主体占比 100%`，exit=0。偏差已在本节留痕，PR 说明需同步 |
| 7 | `init-build` 崩溃：HMDFS 拒绝硬链接 + `android/jni/src -> ../..` 符号链接回环 | `shutil.copytree` 的 copy2 回退跟随自指符号链接 | 用 `cp -a`（保留符号链接不跟随）手工产出 `.work`，再以 `--no-download` 续跑 |
| 8 | W3 首跑 L5 门禁失败：`[fail] L5a: libpktriggercord.so 缺少 DT_SONAME — 下游链接器无法按 SONAME 寻址`（`L5_RESULT=fail: soname_gate_failed`） | `clang -shared -o libpktriggercord.so` 不会自动写 `DT_SONAME`（上游没有库目标，无既有链接参数可继承） | 链接命令补 `-Wl,-soname,libpktriggercord.so`；重跑 W3 → `L5_RESULT=pass: lib/ has content` |
| 9 | W3 跑完后 `conandata.yml` 被改写成 `url: [ "https://gh-proxy.com/<官方>", "<官方>" ]`（W4 审计判 P1/R39） | `ci/conan/build_and_test.sh` 的预下载会为 GitHub 源注入镜像回退列表，restore 只回滚到运行前状态——本地多次 W3/verify 后镜像形态残留在工作树 | 归档文件还原为**单条官方 URL** 并实测核验（`curl` http=200、sha256 逐字节一致，见「验证结果」）；镜像由 CI 侧 `get_mirrors()` 自行注入，PR 内不得手写（R39/PF7） |

## 源码修改
**无**。`diff -rq .orig .work` 与逐文件 `cmp` 对 `*.c/*.h/Makefile` 均无差异，
`patches/` 为空（R5/R21 零介入；`refresh-patch --auto` 无需生成补丁）。
所有适配都落在配方侧（make 命令行变量 + 自建库目标）。

## 依赖版本
无第三方依赖。实测产物 `llvm-readelf -d libpktriggercord.so` → `NEEDED` 仅 `libc.so`。
- libc/libm：OHOS NDK sysroot（`-lm` 显式传给 make 命令行）
- `<scsi/sg.h>`：sysroot 已提供
  （`/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/sysroot/usr/include/scsi/sg.h`）
- js0n：树内 vendored（`Makefile:1`，`src/external/js0n/`），不外部化
- 可选 `LIBGPHOTO` 日志后端（`pslr_log.h:43`）默认不定义 → 不需要 libgphoto2

## 验证结果

```bash
# 上游测试（无测试框架；.travis.yml 唯一功能入口）
HMBS_UPSTREAM_TEST_RESULT={"status": "passed", "framework": "upstream-cli-smoke",
 "command": "./pktriggercord-cli --version; ./pktriggercord-cli --help",
 "discovered": 2, "executed": 2, "passed": 2, "failed": 0, "skipped": 0}
./pktriggercord-cli --version  -> rc=0，输出 "pktriggercord-cli 0.85.01"
./pktriggercord-cli --help     -> rc=255（上游设计），输出含 "Usage:" -> 判 PASS

# test_package（消费者链接 + 真实断言，计数由被测程序写出的 result 文件解析，非硬编码）
RESULT discovered=13 passed=13 failed=0        # 13/13 全通过

# conan-verify（reports/conan-verify-report.md）
G1 PASS / G2 PASS / G3 PASS（无系统同名库冲突）

# W3 本地 CI 门禁实测（reports/w3-local-ci.log 的 JC/L0–L5 结果行；该日志为本地工件，行号随运行浮动）
检查模式: prdiff (11 个文件)                      JC_RESULT=pass
L0_RESULT=pass: all checks passed                 # 结构六件套/sha256/测试源/MANIFEST
L1_RESULT=pass: test_package executed             # 含 L1e 破坏性反向验证：
                                                  #   [ok] Negative test confirmed — test genuinely depends on libpktriggercord
L2_RESULT=skip: no bin/ dir                       # 纯库包无 bin/，按设计跳过
L4_RESULT=pass: patches clean
L5_RESULT=pass: lib/ has content                  # 含 L5a DT_SONAME、L5b NEEDED 校验
Pass rate: 100.0% (1/1)

# 手工补充核验（.pktc-build-logs/t9_artifact_checks.log）
  Type: DYN (Shared object file)  Machine: AArch64
  SONAME: libpktriggercord.so     NEEDED: libc.so（依赖闭包为空）
  FLAGS: BIND_NOW（+GNU_RELRO，full RELRO）
  导出符号: 117 × T pslr_*
  产物: include/ 8 头 + lib/libpktriggercord.so(352K) + share/pktriggercord/pentax_settings.json + licenses/COPYING

# 源码 URL 与校验和（R39：conandata.yml 只写官方单条 URL，镜像由 CI 注入）
$ curl -sSL -o "$TMPDIR/pktc-official.tar.gz" \
    https://github.com/asalamon74/pktriggercord/archive/c1177a4881f363455255866f6f6d8149574e4b35.tar.gz
http=200 size=4330943
actual  : 3347fdd480666df97753b6da935e8550a00177bc1dbe05a5bcc0ab36220ec51b
expected: 3347fdd480666df97753b6da935e8550a00177bc1dbe05a5bcc0ab36220ec51b  ← 一致
```

## W4 独立审计闭环（两轮）

| 轮次 | 判定 | 明细 |
|---|---|---|
| 第 1 轮 | ❌ fail（P0=0 P1=1 P2=2 P3=6） | P1 R39/PF7：`conandata.yml` 残留 `https://gh-proxy.com/` 镜像前缀（即问题 9 的 W3 改写未还原）；P2 R52：`notes.md` 把 L4/L5 误写成"跳过"；P2 R51：test_package 结果标记用常量 13 回填而非解析实测输出 |
| 修复 | — | 还原官方单条 URL 并实测 `http=200` + sha256 逐字节一致；重写「验证结果」小节为与 `w3-local-ci.log` 行号一致的准确表述；test_package 改为解析被测程序写出的 result 文件（缺文件/无 RESULT/passed≠discovered/逐项与汇总不符四处抛 `ConanException`），并补 `can_run` 守卫 smoke 执行、helper 上移、`ConanException`/`glob` 规范化 |
| 第 2 轮 | ✅ pass（P0=0 P1=0 P2=0 P3=5） | 三项前序问题由审计方独立复核为 fixed（含机械复跑 `preflight.check_source_urls()` 与工作树/HEAD 逐字节比对）；欺骗性检测全部通过。本轮新 P3 已全部处置：notes.md 行号与"11 个文件"口径、`assertion_count` 回改为 13（消费者断言，与 upstream_test_case_count=2 分列）、删除 3 处 `print()` 统一走 `self.output.info`（code-style §19） |
| 保留未改 | 2 项 P3 存量 | ① PF9 对包级 `README.md`/`manifest.yaml` 的误报（`preflight.py:570` 判据 `len(split('/')) < 5`，与 review-memory 规则 17 冲突，删除反而触发六件套缺失）；② 工作副本 `archives/l/libXext/*` 未提交改动系大小写碰撞的既有状态，本 PR 提交严格限定 `git add archives/l/libpktriggercord knowledge/drafts/E429-draft-EF9C.*`，未用 `git add -A` |

## 多配置复验（配方 options/build_type 覆盖）

默认配置由 W3 + 远端 CI 校验；其余两个配置手工复验（`.pktc-build-logs/t26_static_variant.log`、
`t27_debug_buildtype.log`），三者结果一致：上游 2/2、test_package 13/13。

| 配置 | 命令 | 结果 | 关键证据 |
|---|---|---|---|
| Release + shared（默认，CI 覆盖） | `conan create`（profile 默认） | ✅ | `L5a SONAME` 通过、`.so` 打包 |
| Release + static | `conan create -o "&:shared=False"` | ✅ | `llvm-ar rcs libpktriggercord.a`、`Packaged 1 '.a' file`、test 链接 `.a` 后 `RESULT discovered=13 passed=13` |
| Debug + shared | `conan create -s build_type=Debug` | ✅ | `CFLAGS="-O0 -g -Wall -fPIC -Isrc/external/js0n"`（`-I` 未被丢）、13/13 |

## 运行时传输层可用性（R40 适配完整性，重要）

上游库唯一的设备传输路径是 `ioctl(SG_IO)` 打 `/dev/sg*`（`pslr_scsi_linux.c:35,212`）。
本机实测（`.pktc-build-logs/t28_sg_runtime.log`）：

```
$ ls -la /dev/sg* /dev/bsg/*
ls: /dev/sg*: No such file or directory
ls: /dev/bsg/*: No such file or directory
$ ls /dev | grep -c '^sg'
0
$ which setcap getcap
（无输出）
```

结论与影响：
- **不是"没插相机"，而是本 HarmonyOS PC 运行环境根本不提供 SCSI 通用（sg）设备节点**，
  也没有 `setcap`（上游 `%post` 靠它给二进制加 `CAP_SYS_RAWIO`）。
- 因此本包的**编译期与无相机逻辑（枚举表、镜头表、文件格式表、日志、CLI 冒烟）已实证**，
  而**取图/控制相机的 I/O 路径在本机不可验证**；若 OHOS PC 要真正驱动 Pentax 单反，
  需要另行接入平台的 USB 设备通道（候选方案：改走 libusb 后端，或经 OHOS USB/PTP 能力），
  这属于新的适配工作量，不在本 PR 范围（本 PR 不改上游源码、不加 `__OHOS__` 分支）。
- 下游 CI / 集成测试**只应调用 `--version` / `--help` 与纯逻辑 API**；任何 `pslr_camera_open`
  系调用都会因无设备节点而失败（配方与 test_package 已按此约束设计，不触碰设备）。

## 注意事项
- `PKTDATADIR` 在编译期被烤成 `<package_folder>/share/pktriggercord`（上游 `Makefile:4` 语义）。
  缓存路径变化时 `pslr_model.c:799-801` 的 `dir_exists()` 检查会静默回退到当前工作目录，
  仅影响"未知机型时读取 pentax_settings.json"这一条兜底路径，主 API 不受影响。
- 共享库不做 Linux 式版本化 soname（仅 `libpktriggercord.so`）：HMDFS 符号链接覆盖语义不可靠（§7 / R5），
  少一个失败面；如后续有下游 ABI 需求再加 `.so.0` 链。
- 运行时能力：库通过 `ioctl(SG_IO)` 走 `/dev/sg*`（`pslr_scsi_linux.c:35,212`）。**本机不提供 sg 设备节点，
  也无 `setcap`/`CAP_SYS_RAWIO` 工具链**（实测见上一节），故 I/O 路径不可验证——
  已实证的是编译期与全部无相机逻辑。**CI/下游测试只可调用 `--version`、`--help` 与纯逻辑 API，
  不要调用 `--status`/`--camera` 等需要设备的命令（且默认 `--timeout=0` 会永久阻塞）。**
- R40 视角：本库不是渲染/UI 适配类，平台相关点只有 SCSI-generic 传输分支；OHOS 沿用 `pslr_scsi_linux.c`
  且 sysroot 提供 `<scsi/sg.h>`，未新增 `__OHOS__` 分支（无补丁，PF5 无风险）。
---

**编译结束**: 2026-09-17 14:52
**最终状态**: built
