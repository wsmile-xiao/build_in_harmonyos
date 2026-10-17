# vor 0.5.8 测试报告

> **项目**: vor (Variations on Rockdodger) 0.5.8
> **测试日期**: 2026-09-27
> **测试环境**: HarmonyOS PC aarch64 真机（B 机，HongMeng Kernel / clang 15.0.4 / Conan 2.29.1，profile `ci/conan/profiles/ohos-aarch64`）
> **测试类型**: 手动功能测试 + Conan 消费者测试（上游无官方测试套件）

---

## 一、测试摘要

| 指标 | 数值 | 百分比 |
|:----:|:----:|:------:|
| 总测试数 | 25 | 100% |
| 通过 (PASS) | 25 | 100% |
| 失败 (FAIL) | 0 | 0% |
| 跳过 (SKIP) | 0 | 0% |

**核心功能通过率**: ✅ **100%**（25/25）

上游官方测试套件：**0 条**（清点取证见 §五，非省略）。因此上表全部为本包
`test_package/test.sh` 的消费者断言，在 `conan create` 的 test 阶段真实执行。

---

## 二、测试结论

### 2.1 总体评价

⚠️ **可交付（构建/链接/打包/取数/CLI 全绿；显示与音乐受平台与依赖能力限制，逐项披露）**

### 2.2 主要问题

| 问题类别 | 影响范围 | 严重程度 |
|----------|----------|----------|
| tracker 音乐 `mph.xm` 无法解码（依赖 `sdl_mixer/1.2.12` 以 `--disable-music-mod` 构建） | 仅背景音乐；游戏音效与玩法不受影响 | 🟡 |
| 音频设备不可得时走上游自带降级路径（`Can't open sound, starting without it`） | 声音，不影响可运行性 | 🟢 |
| 包不可 relocate（`--prefix` 被烧成包绝对路径，系上游 `DATA_PREFIX` 设计） | 换缓存路径需重建 | 🟢 |

### 2.3 可用功能清单

```
✅ 编译与链接: 12 枚 .c 全量编译通过，bin/vor 424384 B ELF64/AArch64/PIE
✅ 安装与打包: bin/vor + share/vor(61: 59 PNG + bang.wav + mph.xm) + licenses/COPYING
✅ 可执行性: OHOS ELF 自签（含 .codesign 段），在 conan run env 内可直接执行
✅ CLI: --version 输出 'Variations on Rockdodger 0.5.8' 并退出 0；--help 输出 usage；未知选项正确报错
✅ 数据定位: 编译期烧入的 DATA_PREFIX 即包内 share/vor（改名即报缺数据、放回即恢复，双向验证）
⚠️ 视频: 本机默认驱动下实测进入主循环（2 秒看门狗终止）；强制 SDL_VIDEODRIVER=none 时在视频层失败
❌ 音乐: mph.xm（tracker module）在本仓 sdl_mixer 构建配置下不可用（--disable-music-mod）
```

### 2.4 已知限制

1. 上游无任何测试套件 ⇒ 无法给出"官方测试通过率"；可执行验证由消费者断言承担（25 条）。
2. 框架 `conan-verify` 的 L2/L4/L5 三条本轮输出「⏭️ 跳过（无 cache 路径）」，判决行虽写 PASS 但**未真正执行**；
   等价证据由本窗手工补齐（§四）。
3. finish 的 G0 clean-verify 以裸 `configure` 跑（不经 conan env，无 `CC`）⇒ 必然失败，属该步骤对本类包的
   结构性限制（非阻塞步骤）；同一份源码在 `conan create`（G2）内为 PASS。
4. 断言全部走"无需显示/无需音频"的路径，并统一用 `SDL_VIDEODRIVER=none` + 20 秒看门狗 ⇒
   在有显示的 worker 上不会卡死，在无显示的 worker 上不会假绿。

---

## 三、测试详情

### 3.1 通过的测试（25 条，全部来自 `test_package/test.sh`）

| 组 | 条数 | 内容 |
|----|------|------|
| CLI 面 | 11 | `--version` 退出码 0；banner 逐字等于 `Variations on Rockdodger 0.5.8`；`--help` 退出码非 0（上游设计）；usage 含 `-f, --full-screen` / `-s, --silent` / `-V, --version` / `-?, --help` 四行；未知短选项 `-Z` 非 0 退出 + `unknown option -Z`；未知长选项 `--bogus-option` 报错；裸参数报 `not an option` |
| 数据资产面 | 11 | `share/vor` 内 PNG 计数 = 59；条目总数 = 61；`b_variations.png`/`font.png`/`ship.png`/`icon.png`/`life.png`/`rock00.png`/`rock49.png`/`bang.wav`/`mph.xm` 逐一存在 |
| 运行期数据定位面 | 3 | 数据目录改名后 `vor -s` 报 `Can't find VoR data!`；放回后不再报缺数据；无动态链接器错误（`libSDL-1.2.so.0` 等运行期解析成功） |

末行机器可读读数：`ASSERTIONS=25 PASSED=25 FAILED=0` → `[result] PASS`。

### 3.2 失败的测试

无。

### 3.3 跳过的测试

| 项 | 类别 | 原因 |
|----|------|------|
| 上游 `make check` | 上游套件 | **不存在该目标**（`grep -nE "check\|TESTS" Makefile.in` 无输出）⇒ 不是跳过，是没有 |
| L2 smoke | 框架门禁 | 输出「⏭️ 跳过（无 cache 路径）」；本窗以 `--version` 实跑 rc=0 补证 |
| L4 checksec | 框架门禁 | 同上；本窗以 `readelf` 补证（PIE / NX / RELRO，见 §四） |
| L5 产物基线 | 框架门禁 | 同上；本窗以 `readelf -d` NEEDED 清单与包文件计数补证 |
| 真实对局（键盘操作玩一局） | 手工 | 需交互输入与窗口焦点，非交互沙箱内不执行；未删断言、未放宽口径 |

---

## 四、产物与运行期证据

```
包目录:  ~/tmp/ch/home-vor/p/b/vor65ee8c77cf7ef/p
bin/vor: 424384 B  ELF64  Type: DYN (PIE)  Machine: AArch64  含 .codesign 段
NEEDED:   libSDL-1.2.so.0 libtiff.so.6 libjpeg.so.62 libturbojpeg.so.0
          libzstd.so.1 libwebp.so.7 libsharpyuv.so.0 libc.so
          （SDL_image / SDL_mixer 为静态库链入 ⇒ 无对应 NEEDED，符合依赖包 default_options.shared=False）
段属性:   GNU_STACK 非可执行（NX 生效）、GNU_RELRO 存在
share/vor: 61 个条目（59 *.png + bang.wav + mph.xm）
licenses/: COPYING
```

原样调用与输出（在 `conan install --requires=vor/0.5.8@ohpcd/stable -g VirtualRunEnv` +
`. conanrun.sh` 之后执行；裸 shell 会因未注入 `LD_LIBRARY_PATH` 报
`Error loading shared library libSDL-1.2.so.0` —— 属环境未激活，不是产物缺陷）：

```
$ vor --version
Variations on Rockdodger 0.5.8                                  rc=0
$ vor --help | head -1
Dodge the rocks until you die.                                  rc=1（上游设计）
$ SDL_VIDEODRIVER=none vor -s
vor: SDL error: 'none not available'                            rc=1
$ SDL_VIDEODRIVER=none vor            # 不传 -s，走音频初始化
Can't open sound, starting without it
vor: SDL error: 'none not available'
$ vor -s                              # 不指定驱动，2 秒看门狗
（无错误输出，进程存活至看门狗 SIGKILL）                          rc=137
$ mv <pkg>/share/vor <pkg>/share/vor.hold && SDL_VIDEODRIVER=none vor -s
Can't find VoR data! Tried:
        /storage/.../p/share/vor        ($VOR_DATA 为空 ⇒ 跳过)
        data                            (相对 CWD)
        /storage/.../p/share/vor        (DATA_PREFIX)          rc=1
```

---

## 五、上游测试清点（R51 第一步"清点"的取证命令）

```
$ tar xf vor_0.5.8.orig.tar.gz && cd vor-0.5.8
$ grep -nE "check|TESTS" Makefile.in            → 无输出（无 check: 目标、无 TESTS 变量）
$ grep -n "^.PHONY" Makefile.in                 → all clean maintainer-clean install uninstall
                                                  program data mkinstalldirs ...（无 check）
$ grep -n "AC_CONFIG_TESTDIR\|AM_INIT_AUTOMAKE" configure.ac → 无输出
$ ls                                             → 无 tests/ test/ t/ 目录
$ ls *.c | wc -l                                 → 12（全部为游戏源码，无测试源）
⇒ 上游注册测试数 = 0
```

---

## 六、门禁读数汇总

| 门禁 | 读数 | 日志 |
|---|---|---|
| `preflight_check.sh vor/0.5.8`（写 requires 后） | `[OK] 预检通过`，rc=0 | `~/tmp/uc2/z75v-vor/gate1-preflight-with-deps.log` |
| `recipe-search vor` | 语料 6173 条，无相似配方 | `gate1-recipe-search.log` |
| `build vor 0.5.8`（模式 A） | 失败（探索段无 conan env）⇒ 按 R14 转配方路线 | `gate3-build.log` |
| `conan-verify vor 0.5.8` | `**Verdict**: PASS`；G0/G1/G2/G3 实检 PASS，**G4 是空判**（正文只有「⚠️ 无法找到程序包 ID」⇒ conan-verify 的实际覆盖为 G0-G3，逐字见 `reports/conan-verify-report.md:39-40`）；L2/L4/L5 判决 PASS 但实为 skip（§2.4） | 随 PR 的 `reports/conan-verify-report.md`（判决行与 G0-G4 各段标题）+ `reports/conan-create.log`（G2 的 conan create 实录）；设备侧的 4 枚 gate4 探索日志登在 `notes.md:399-402`（**不存在** `-7`，也没有 1..7 序列，见 `notes.md:421-423` 的更正段） |
| `finish vor 0.5.8 built` | 完成到 `built`；W3 `[5/10]` 通过并写 `.ci-result.json`（`exit_code: 0`，`log_sha256: 2a93090d4461…`）；step3 G0 clean-verify 与 step8 gen_summary 各有非阻塞失败（见 notes.md §12 与本报告 §2.4） | `gate5-finish.log` |
| `graph validate` | 见主窗汇报正文 | 本次执行日志 |
