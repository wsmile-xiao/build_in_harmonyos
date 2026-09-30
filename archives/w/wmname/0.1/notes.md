# wmname 0.1 适配笔记

任务：平台 11953（lang=cpp，taskBranch `feat/wmname-0.1`）
上游：suckless wmname 0.1（`https://dl.suckless.org/tools/wmname-0.1.tar.gz`，2512B）
源码构成：`wmname.c`（单文件 C，59 行）+ `Makefile` + `config.mk` + `README` + `LICENSE`
构建系统：raw Makefile（**不是** autotools；无 configure、无 CMake、无测试套件）

## 编译环境

- 目标：HarmonyOS PC / OpenHarmony aarch64（`clang -dumpmachine` = `aarch64-unknown-linux-ohos`，musl）
- 构建系统: makefile
- 编译器: clang（来自 conan profile `tools.build:compiler_executables={"c": .../clang}`）
- 依赖: `libx11/6.4.0` + `xorgproto/2025.1`（二者均已发布到 ohpcd 制品仓，W0 实测）
- 状态: built

## 症状（首轮真实失败）

1. **上游 Makefile 的 X11 路径在目标环境不存在**
   `config.mk` 写死 `X11INC = /usr/X11R6/include`、`X11LIB = /usr/X11R6/lib`，
   `LIBS` 里还有 `-L/usr/lib -lc`。设备、CI worker、主机上 `/usr/X11R6` 与
   `/usr/include/X11` **都不存在**（实测 `ls` 均报 No such file）。
2. **构建/打包成功但产物在 HarmonyOS 上被拒载**
   实测最小复现（见下）得到 `Operation not permitted`，退出码 **126**，
   即 E318/E077B 家族：「ELF 存在且权限位正确」≠「可执行」。

## 根因

- 症状 1 根因：X11R6 是 1990 年代路径，上游把主机 X11 当默认。适配必须把
  头/库路径换成制品仓依赖包的真实路径（R36），**不写死设备路径、也不用主机
  `/usr/include`、`/usr/lib`**。
- 症状 2 根因（**本轮真正踩到的那一个**）：OHOS SDK 的 clang 在**链接期自动**
  写入 `.codesign` 段（自签名），而上游 `Makefile` 链接行带 `-s` **且链接后
  还显式执行 `strip`**。strip 改变了文件内容 ⇒ 链接期自动签名**失效**，
  内核拒载该 ELF。
  - 关键区分：`.codesign` **段仍在**（`llvm-readelf -S` 可见）——**「段存在」≠
    「签名有效」**。只看段存在会把这一条误判为「已签名」。

## 最小复现（一手读数，勿转述）

```sh
# 目标编译器；include/lib 取自 conan 制品仓依赖包
clang -c -std=c99 -Wall -Os -I<libx11>/include -I<xorgproto>/include -DVERSION=\"0.1\" wmname.c -o wmname.o
clang -o wmname_nostrip wmname.o -L<libx11>/lib -lX11        # 链接期自动签名
strip wmname_nostrip                                         # 上游 Makefile 也这么做
env -u DISPLAY LD_LIBRARY_PATH=<deps lib dirs> ./wmname_nostrip
# → env: './wmname_nostrip': Operation not permitted   （rc=126）
llvm-readelf -S wmname_nostrip | grep codesign
# → [24] .codesign  PROGBITS  ...   ← 段还在，但内容已失效
```

修复后同一文件：

```sh
llvm-objcopy --remove-section .codesign wmname_resigned
binary-sign-tool sign -inFile wmname_resigned -outFile wmname_resigned.tmp -selfSign 1
mv wmname_resigned.tmp wmname_resigned && chmod 755 wmname_resigned
env -u DISPLAY LD_LIBRARY_PATH=<deps lib dirs> ./wmname_resigned
# → wmname: cannot open display   （rc=1，正常进入上游程序逻辑）
```

## 已试过的失败方案（勿重走）

| # | 方案 | 结果 | 为什么不行 |
|---|------|------|-----------|
| 1 | 直接把 `X11INC` 指到主机 `/usr/include` | 不可能 | 主机与设备都没有 `X11/Xlib.h`（实测） |
| 2 | 只在 `package()` 里 `chmod 755` | 无效 | 权限位不是判据；内核看的是 `.codesign` 有效性 |
| 3 | 认为「`.codesign` 段存在 ⇒ 签名有效」，不重签 | 失败 rc=126 | 段存在 ≠ 签名有效（本条核心教训） |
| 4 | 用 `strip` 后不做任何处理 | 失败 rc=126 | strip 使链接期自动签名失效 |
| 5 | 在构建树签名、再把**未签名**副本拷进 package | 未采用 | 签名对象必须是最终包内文件（否则包内仍是失效签名） |

## 最终方案

1. **依赖全部走制品仓**：`requires("libx11/6.4.0")` + `requires("xorgproto/2025.1")`，
   `generate()` 用 `AutotoolsToolchain` 产出 `conanbuild` 环境（R33：`$CC` 来自
   工具链脚本，不裸用调用方 shell 变量）。
2. **沿用上游 Makefile，只覆盖路径变量**：
   `make -j1 CC=$CC LD=$CC X11INC=<libx11 inc> X11LIB=<libx11 lib> INCS=<deps inc> LIBS=<deps lib> -lX11`
   —— 编译式、`-DVERSION`、`strip` 步骤都保持上游不变（最小偏离，R1）。
3. **在最终包内 ELF 上重签名**：`package()` 拷贝后用
   `llvm-objcopy --remove-section .codesign` + `binary-sign-tool sign -selfSign 1`
   自签，临时文件原子替换并恢复 `0755`；只在 `settings.os == "OHOS"` 时执行；
   找不到签名工具直接 `ConanException`（绝不把失效签名的产物当交付物）。
   - **E077 硬要求（本配方已落实）**：调用签名器的子进程必须**剔除
     `LD_LIBRARY_PATH`** —— conan 构建环境里它指向工具链运行时，`binary-sign-tool`
   会重定位失败（报 `std::__h` 系列符号全缺）；且必须「先移除旧 `.codesign`
   段再签」，对已签产物重复签会以 127 退出。二者均按经验库 §12.13/E077 执行。
4. **消费者测试补位**（上游 N_static = 0，无 `make check`）：
   `test_package/test_wmname.sh` 执行打包产物，断言 12 项（2026-09-30 CI 返修，原 10 项）。

## 测试与数字（五维账本）

| 维度 | 值 | 说明 |
|---|---|---|
| `N_static`（上游静态用例） | **0** | tarball 仅 5 个文件，无 test 目录、无 make check、无框架注册入口（`test_package/MANIFEST.yml` 申报） |
| `N_registered` | 0 | 上游无构建系统注册的测试目标 |
| `N_executed`（上游） | **0** | 上游确无测试可执行（非「跳过」，是「不存在」） |
| 未执行分类数 | 0 | 同上，无被条件/依赖屏蔽的用例 |
| `N_consumer`（新增消费者测试） | **1** 个程序 / **12** 条断言 | `test_package/test_wmname.sh` |

断言明细（每条都真实执行打包产物或读链接后 ELF）：
A1 产物存在且可执行 ｜ A2 `wmname a b` 退出码=1 ｜ A3 打印 `usage: wmname [name] [-v]`
｜ A4 `wmname -v` 退出码=1 ｜ A5 打印 `wmname-0.1` ｜ A6 `wmname LG3D`（无 X）退出码=1
｜ A7 打印 `wmname: cannot open display` ｜ A8 二进制含 `_NET_WM_NAME`（可移植检法）
｜ A9 二进制含 `_NET_SUPPORTING_WM_CHECK`（可移植检法） ｜ A10 二进制含 `UTF8_STRING`（可移植检法）
｜ A11 二进制含 `libX11.so` 的 DT_NEEDED SONAME（真链 X11） ｜ A12 ELF 头为 ELF64/小端/AArch64（`od` 直读字节）

**A8–A10 的检法（2026-09-30 返修，见下节）**：主检 `strings "$BIN" | grep -q <字面量>`
（纯文本输入，各 grep 实现语义一致），备检保留原 `grep -a <字面量> "$BIN"`（GNU 环境），
**同一事实两种检法，任一命中即通过**；工具按 `/system/bin/{strings,od,grep}` 绝对路径优先解析。
脚本另打印三法读数（`grep -a` / `strings|grep` / `python3` 字节搜索）供对照。

**property 断言的边界（如实申报）**：设备与 CI worker **都没有 X server**
（实测无 `Xvfb`/`Xorg`），因此无法现场读写 X property。A8–A10 断言的是
**链接后二进制内 `XInternAtom` 的入参字面量**，配合 A2/A4/A6 的退出码=1
（而非 126/127）与 A11 的 `libX11` SONAME 共同证明：ELF 已签名可加载、
`libX11` 动态链接解析正确、程序进入并走完上游逻辑。property 的**实际读写**路径
在本平台无执行环境，未执行原因即「无 X server」。

上游三条消息**均输出到 stderr**（非笔误）：`wmname.c` 的 `eprint()` 是
`vfprintf(stderr, ...)`，`-v` 分支虽然多传了 `stdout` 作为变参，但格式串无
转换符 ⇒ 该实参被忽略，消息仍落 stderr。测试脚本因此合并捕获两个流。

## 门禁执行记录（第一手读数）

| 门禁 | 命令 | 读数 |
|---|---|---|
| W0/预检 | `bash ci/scripts/preflight_check.sh wmname/0.1` | **RC=0**：「已发布: libx11/6.4.0」「已发布: xorgproto/2025.1」「版本号未被占用: wmname/0.1」 |
| 配方检索 | `python3 scripts/ohc-run.py recipe-search wmname` | **RC=0**（catalog 重建 6175 配方；top1 指向本包骨架） |
| 驱动探索 | `python3 scripts/ohc-run.py build wmname 0.1` | **不可用（结构性）**，见下 |
| G0–G4 + L2/L4/L5 | `python3 scripts/ohc-run.py conan-verify wmname 0.1` | **RC=0**，`Verdict: PASS`；G2 为真实 `conan create`（profile `ohos-aarch64`），日志 `reports/conan-create.log` |

驱动探索阶段（`build wmname 0.1`）的两处**真实首错**（非猜测，逐字取自日志）：

```
# 第 1 轮：init-build 无法自动推断源码 URL
❌ 源码目录不存在: <archive>/src
   ℹ️ 请先执行 init-build 下载源码
   HANDOFF: EXIT_REASON=init_build_failed  STEP_FAILED=Step1
# → 用文档化参数解决：init-build wmname 0.1 --url=https://dl.suckless.org/tools/wmname-0.1.tar.gz  ⇒ RC=0

# 第 2 轮：[4/14] make
make: cc: No such file or directory
make: *** [Makefile:19: wmname.o] Error 127
```

**为什么探索阶段对本包结构上不可用**（不是我们没修）：
1. `config.mk` 写死 `CC = cc`，目标环境**没有 `cc`**（`command -v cc` 为空）⇒ 第一步就 Error 127；
   即便补上 `CC`，下一步必然撞上 `X11INC = /usr/X11R6/include` —— 设备/CI/主机**都没有该目录**，
   而派发要求禁止写死主机或设备 X11 路径。
2. 驱动 `[9/14] conan-init` 调用 `conan_init(..., force=True)`，会**强制覆盖**手写配方
   ⇒ 不能借驱动来验证一份人工审定的配方。
3. `--resume-from` 的 `_STEP_MAP` **只认 Step1–Step9**（driver.py:41-44）；传 `Step10` 会被
   `.get(..., 0)` 静默降级为 0＝"从 Step0 全跑"，**不是报错**——此类"看起来跳过了其实没跳过"的
   参数是坑，勿再试。
⇒ 因此按 SKILL §1.1 **模式 B** 的正规路径执行：`init-build` → 配方 → `conan-verify` → `finish`。

> 旁证（框架自动行为，需知悉）：`build` 的 R18 自动修复在 `[4/14] make` 失败后自行执行了
> `curl … | sh -s -- sed 4.9` / `coreutils 9.10`，把两者装进了 `~/usr/local`（基础设施区）。
> 该动作由驱动内部发起、非本包配方要求；未自行回滚，已上报。

## 验证结果

```sh
# conan-verify G2 = 真实 conan create，test_package 在设备上实际执行（reports/conan-create.log）
# 2026-09-30 CI 返修后重跑（12 条断言，见上「CI 返修」节）
RUN: /data/service/hnp/bin/bash test_package/test_wmname.sh <pkg>/bin/wmname <build>
  [ok]   A1 packaged bin/wmname exists and is executable
  [ok]   A2 wmname a b exits 1 (got 1)
  [ok]   A3 usage text 'usage: wmname [name] [-v]' printed
  [ok]   A4 wmname -v exits 1 (got 1)
  [ok]   A5 version string 'wmname-0.1' printed
  [ok]   A6 wmname LG3D without X server exits 1 (got 1)
  [ok]   A7 'wmname: cannot open display' message printed
  [ok]   A8 binary carries _NET_WM_NAME atom literal (strings|grep)
  [ok]   A9 binary carries _NET_SUPPORTING_WM_CHECK atom literal (strings|grep)
  [ok]   A10 binary carries UTF8_STRING atom literal (strings|grep)
  [ok]   A11 binary dynamically links libX11 (DT_NEEDED SONAME present)
  [ok]   A12 ELF header is ELF64/LSB AArch64 (magic=7f454c46 e_machine=b700)
  [info] A8-A10 cross-check readings (grep -a is grep-implementation-dependent):
         _NET_WM_NAME               grep -a rc=1 | strings|grep rc=0 | python3 rc=0
         _NET_SUPPORTING_WM_CHECK   grep -a rc=1 | strings|grep rc=0 | python3 rc=0
         UTF8_STRING                grep -a rc=1 | strings|grep rc=0 | python3 rc=0
wmname consumer test: 12/12 assertions
# 上游无测试套件，上游侧可执行数 = 0（N_static = 0）
```

W3 本地 CI 模拟（`.ci-result.json`，由 finish 写入、随 `.gitignore` 不入库）：`exit_code=0`、
`step=W3_local_ci`；日志 `L0_RESULT=pass / L1_RESULT=pass / L2_RESULT=skip / L4_RESULT=pass /
L5_RESULT=pass`、`Pass rate 100.0% (1/1)`（`reports/w3-local-ci.log`）。
（其 `integrity_hash` 覆盖归档目录内容 ⇒ 不在此转抄：任何后续编辑都会让它失配。）

门禁报告其余读数：`G0 PASS`（知识命中 E490「autotools 脚本可执行位」——本包是 raw Makefile，
**不适用**，属检索到同类但不同构建系统的提示）、`G1 PASS`、`G3 PASS`（无可链接库、无系统同名库冲突）、
`G4 PASS`、`L2/L4/L5` 均为 **跳过**（`无 cache 路径`，纯 `bin/` 包无 lib/ 可扫），跳过≠失败。

**finish 的 `G0 干净构建验证` 仍报失败（非阻塞，结构性、与本包配方无关）**：
`G0: 运行 configure...` → `❌ G0: configure 失败 (exit 127)`，首错原文
`/data/service/hnp/bin/bash: ./configure: No such file or directory`
（`g0-configure.log`）——框架的 clean-verify 走 autotools 口径，而本包是 raw Makefile
（无 `configure`，且上游 `config.mk` 的 `CC = cc` 在目标环境不存在）。SKILL Step 3 表明确标注
该项**非阻塞，平台限制可跳过**；`Step 5/10 W3 [阻塞门禁]` 与 `Step 10/10 submit 就绪预检` 均 **通过**，
`EXIT_REASON: finish_success`（rc 非零仅由该非阻塞项与 `gen_summary` 框架异常
`'str' object has no attribute 'append'` 引起）。

## 依赖版本

- `libx11/6.4.0`（ohpcd 制品仓，实测 download 成功）
- `xorgproto/2025.1`（ohpcd 制品仓，实测 download 成功）
- 传递依赖：`libxcb/1.16`、`libxau/1.0.11`、`libxdmcp/1.1.5`、`xtrans/1.6.0`

## 注意事项

- 上游 `Makefile` 的链接行含 `strip` ⇒ **任何**同类 raw-Makefile + OHOS 工具链
  组合都必须「strip 之后重签」，否则得到 rc=126 的拒载产物。
- `config.mk` 的 `CC = cc` 在目标环境**不存在** `cc`（实测 `command -v cc` 为空）
  ⇒ 必须显式传 `CC=`，不能依赖 Makefile 默认值。
- 构建目录/包内不得出现 `.signed.tmp` 残留（本配方用临时文件 + 原子替换，
  失败路径也清理）。

## CI 返修：PR #13906 首红（2026-09-30）

### 现场（一手读数，勿转述）

- buildbot：PR #13906 → build **75413**，失败 step = 5 `conan-build-test`；日志全文
  `https://ohpcd.atomgit.com/buildbot/api/v2/logs/421589/raw`（本机留档 `~/tmp/uc2/ci13906-stdio.txt`，388 行）
- CI 红原文：
  ```
  [ok]   A1 packaged bin/wmname exists and is executable
  ...（A2-A7 全 ok）
  [FAIL] A8 binary carries _NET_WM_NAME atom literal
  [FAIL] A9 binary carries _NET_SUPPORTING_WM_CHECK atom literal
  [FAIL] A10 binary carries UTF8_STRING atom literal
  wmname consumer test: 7/10 assertions
  ERROR: wmname/0.1 (test package): Error in test() method, line 50
  [fail] wmname/0.1 — conan create failed
  L1_RESULT=fail: conan create failed   （L2/L4/L5=skip）
  ```
- CI 侧确系**源码重建**（`Building from source` / `CC=/data/service/hnp/bin/clang` / `CC wmname.c` /
  `LD wmname` / `Package '779b26622d…' created`），L0k（commands.json）与 L0n（分支名）均 pass。

### 根因（已实测复现，非推断）

**关键读数一：CI 那份产物与本机逐字节相同 ⇒ 三个字面量一直在产物里。**
本机用**未改动的配方 + 直接 `conan create`**（不经过 CI 脚本）复现出 **CI 的完整包引用**：

| 来源 | recipe revision | package_id | package revision |
|---|---|---|---|
| CI build 75413 | `c75f03c0ec43e1cc2e879b33aca6c669` | `779b26622d2d7d40dd8ae866450d8c0db13fb628` | `841175955f9f8e4272dcfdbc9d1525e2` |
| 本机对照实验（未改动配方） | `c75f03c0ec43e1cc2e879b33aca6c669` | 同上 | 同上 |

三项全等 ⇒ CI 被打包 ELF 与本机**同一份**。本机对该二进制的读数：
`readelf -p .rodata` 三条字面量全在（`UTF8_STRING` / `_NET_SUPPORTING_WM_CHECK` / `_NET_WM_NAME`）、
`python3` 字节搜索三条全 `True`、GNU grep `-ac`=1、`readelf -d` 有 `NEEDED libX11.so.6`、
`file` 报 `ELF shared object, 64-bit LSB arm64, dynamic, stripped`（`readelf -S` 无 `.symtab`＝确被 `-s` 剥过）。

**为什么 package revision 相同就等价于字节相同**（同批做的控变量实验，非引用文档）：
只给配方 `conanfile.py` 加一行注释 → recipe revision 变（`c75f03c0…`→`5f98715d…`），
而 **package revision 不变**（仍 `841175955f…`）；两次构建出的 `bin/wmname` sha256 均为
`0776406e50dc3a27a675873fa07ff615f6c492b3dbb02e1097d5566cc397ad92`。
⇒ package revision 由**打包内容**决定、与 recipe revision 无关。本机共三次独立构建
（两个 CONAN_HOME）sha256 全部相同。

**关键读数二：失败的是检法，不是产物。** 同一条 `grep -a <字面量> <ELF>`、同一份二进制：

| grep 实现 | 绝对路径 | 读数 |
|---|---|---|
| GNU grep 3.12 | `/data/service/hnp/bin/grep` | `-aq` rc=**0**（命中）、`-ac`=1 |
| toybox 0.8.12 | `/system/bin/grep` | `-aq` rc=**1**（不命中）、`-ac`=**0** |

toybox grep 按 C 字符串语义切行，**每行第一个 NUL 之后的字节不可见**。本机最小复现（同一目录、同一文件内容）：
`ABC\0\0def` → rc=0；`def\0\0ABC` → rc=1。而 ELF 的 `.rodata` 字面量都排在 NUL 之后。
CI 的 `test_package` 运行环境（conan `env="conanrun"`）PATH 里只有系统 toolbox，没有 profile
`[buildenv]` 追加的 `/data/service/hnp/bin` —— 实测证据：把本机 PATH 收窄成 CI 那套
（`/data/app/bin:/system/bin:/system/sbin:/vendor/bin:$HOME/.local/bin`）后，连 `bash` 都
`command not found`，而 conanfile 正是用**绝对路径** `/data/service/hnp/bin/bash` 起测试的 ⇒ 完全吻合。

⇒ **结论**：A8–A10 当时测的是「某个 grep 实现对二进制文件的匹配语义」，不是产物契约；
同一 PR 在本机（GNU grep）恒 10/10、在 CI（toybox）恒 7/10。与 `-Os`/`-s` **无关**
（用 CI 完全相同的 `CFLAGS/LDFLAGS` 重建，字面量仍在 `.rodata`）。

**recipe revision 与本地不同的解释**：`ci/conan/build_and_test.sh` 的预下载段会**在
conan create 之前就地改写 `conandata.yml`**（镜像 fallback / `file://`，EXIT trap 才还原），
而 recipe revision 对配方文件内容取哈希 ⇒ 经 CI 脚本跑得 `7fbae007…`、直接 `conan create`
得 `c75f03c0…`（＝CI 那次）。**不影响产物**：两条路径的 package revision 相同（见上）。

### 修法（等价强度、可移植；总数 10 → 12，不缩水）

- **A8/A9/A10 保留原语义**（三条 atom 字面量在链接后 ELF 内），换判定方式：
  ①主检 `strings "$BIN" | grep -q <字面量>` —— 输入是**纯文本**，各 grep 实现语义一致；
  ②备检保留原 `grep -a <字面量> "$BIN"`（GNU 环境命中）；同一事实两法，任一命中即通过；
  ③工具以 `/system/bin/{strings,od,grep}` **绝对路径**优先解析，消除 PATH 依赖；
  ④脚本额外打印三法读数（`grep -a` / `strings|grep` / `python3` 字节搜索）留痕对照。
- **新增 A11**：产物内含 `libX11.so` 的 DT_NEEDED SONAME —— 证明真链 X11（非静态/占位糊弄），
  与 A2/A4/A6「退出码恰为 1 而非 127」互为佐证（127 = 动态库未解析）。
- **新增 A12**：`od` 直读 ELF 头字节 —— `e_ident[0:4]=7f454c46`（ELF64）且 `e_machine`
  （偏移 18，LE 2 字节）= `b700`（183 = AArch64）；不经任何 grep。

**为什么等价甚至更强**：被替换的三条仍断言「产物内确有该字节串」，只是不再把结论绑在某个
工具的实现细节上（分母不缩、无跳过）；A11/A12 把原本隐含在退出码里的两条契约（真链 `libX11`、
确为 aarch64 ELF）显式化。

### 返修复验读数（最终 HEAD `212cf66198a347e14587ca055e06d0c35947a6c8` 上）

- **控变量复现 CI 环境**（PATH 收窄成 CI 那套 + 只上 conanrun 的 `LD_LIBRARY_PATH`，
  用同一份二进制跑 `test_wmname.sh`）⇒ `wmname consumer test: 12/12 assertions`，诊断行原文：
  ```
  _NET_WM_NAME               grep -a rc=1 | strings|grep rc=0 | python3 rc=na
  _NET_SUPPORTING_WM_CHECK   grep -a rc=1 | strings|grep rc=0 | python3 rc=na
  UTF8_STRING                grep -a rc=1 | strings|grep rc=0 | python3 rc=na
  ```
  —— 直接坐实「旧断言在 toybox 下必红、新断言两种环境都绿」。
- CI 入口本机复跑（全新 `CONAN_HOME`，`CI_PACKAGES=archives/w/wmname/0.1
  CI_BRANCH=feat/wmname-0.1` + `zsh ci/conan/build_and_test.sh`）⇒ `L0/L1=pass`、
  `Pass rate 100.0% (1/1)`、消费者 12/12。

### worker 侧顺带留痕（**不是**红因）

`[step] Pre-download` 预下载 3 次全部 `[fail] [Errno 2] No such file or directory: 'curl'`，
回退 conan 直连下载（本包成功，属 WARN）。worker 缺 `curl` 会让「预下载兜底」整体失效，
来源为 GitHub 的包在 CI 侧抖动时无兜底 ⇒ 已随终报上报，非本包红因。

## 进度

- 2026-09-30 配方四件套 + 元数据落盘；`conan-verify` 全绿（10/10 消费者断言，真实 `conan create`）；
  下一步唯一动作 = `finish wmname 0.1 built` → `submit` 建 PR → 触发 CI。
- 2026-09-30 CI 返修（PR #13906 首红）：根因＝A8–A10 依赖 grep 实现对二进制文件的匹配语义
  （toybox 在 NUL 处截断），非产物问题；A8–A10 改可移植检法 + 新增 A11/A12（10 → 12 条断言），
  复验 12/12（含 CI 同构 PATH 控变量实验）→ 复推同一 PR。

---

**编译结束** 2026-09-30

**最终状态** built（conan-verify RC=0，消费者测试 12/12；CI 首红已返修复验，复推 PR #13906）
---

**编译结束**: 2026-09-30 01:39
**最终状态**: built
