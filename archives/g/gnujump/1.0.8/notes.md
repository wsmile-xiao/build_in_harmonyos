# notes.md — gnujump 1.0.8 适配 HarmonyOS PC

任务：13806 ｜ 分支：feat/gnujump-1.0.8 ｜ 主理：DS-30（2026-09-22 接手自【交接】行，前任 ds-1/GLM-62/GLM-63/DS-20）

## 包定位

GNUjump 是 GNU 的下落方块跳跃街机游戏（XJump 复刻），上游 autotools + SDL 1.2 API +
桌面 OpenGL 固定管线，产物为可执行文件 `gnujump` 与随包 skins/sound 数据目录。

## W0 / 依赖

官方 URL `https://ftp.gnu.org/gnu/gnujump/gnujump-1.0.8.tar.gz`，
sha256 `13c3fe5f430eb0c010560c7e438123a573ca61a55c6708aa750cfbf56bf25e17`。
依赖四个均发布于 ohpcd 制品仓（conan install --build=never 逐个实测）：
`sdl12-compat/1.2.68`（run=True）+ `sdl-image/1.2.12` + `sdl-mixer/1.2.12` + `gl4es/1.1.6`。
历史阻塞说明：09-20 GLM-63 实测 `sdl/2.30.7` conan download 报 system acceleration policy
not enabled——本包走 SDL1.2 兼容链（sdl12-compat），不依赖 sdl 主包，不受该阻塞影响。

## 适配要点（与配方/补丁一一对应）

- **SDL 1.2 API** 由 sdl12-compat（SDL2 后端）满足；上游 configure 用 AM_PATH_SDL 探测
  sdl-config——generate() 生成包装脚本供其消费（lgeneral/1.4.4 同模式，方案级复用）。
- **桌面 OpenGL** 由 gl4es（GL→GLES 转译层）满足：AX_CHECK_GL 的头文件与链接探测经
  CPPFLAGS/LDFLAGS/LIBRARY_PATH 环境注入命中包内 gl4es。GL 检测失败非致命，但 gnujump
  真实使用 GL 固定管线渲染，GL 必须命中，否则 make 链接 undefined reference；
  GLU 全源码零调用，检测失败置空正好。
- **gettext/NLS**：--disable-nls 关闭（src/gettext.h 本地回退空实现），规避 OHOS sysroot
  `<libintl.h>` 空壳（lgeneral 0003 同源根因）；main.c 的 setlocale 调用加 ENABLE_NLS
  守卫（补丁 0002）。
- **上游随包 config.guess/config.sub 实测 timestamp = 2012-02-10**，不识别 OHOS triplet——构建期整文件替换为现代版（E007；实测替换件在本机直接输出 aarch64-unknown-linux-ohos，config.sub 亦接受）。
- **-j1**：GNU make jobserver 在 HMDFS 上创建 command FIFO 失败（既有先例）。
- **SHELL/CONFIG_SHELL=/bin/sh**：autoconf 用 CONFIG_SHELL re-exec 自己，conan buildenv
  指向的 hnp bash 在 HMDFS 下 getcwd 必挂（E386，§12.38）。
- 补丁清单：0001 configure 去 umask（E011/HMDFS）、0002 main.c setlocale NLS 守卫、
  0003 setup.c glGetString NULL 守卫（OHOS 上无 GL 上下文时上游直接解引用）。

## 上游测试账本（§10.1 五维，口径锁定）

| 维度 | 数值 | 依据 |
|---|---|---|
| N_static | 0 | grep TESTS / check_PROGRAMS 于全部 Makefile.am（src/ skins/ sound/ doc/ po/）无命中；automake 生成空 check 目标。2026-09-23 独立复核：解包官方 tarball 后 20 个 Makefile.am、命中 0 行 |
| N_registered | 0 | 同上（空 check 目标无可执行注册） |
| N_executed | 0 | `make check -j1` 在 build() 内真实执行（空跑，非跳过） |
| 未执行分类 | 0 | 无注册用例，无未执行项 |
| N_consumer | 1 | test_package/test_gnujump.py：**2 组断言真实执行**（ELF 结构 + DT_NEEDED 白名单）+ 1 组条件启动/运行断言按 R34 留证跳过（见下） |

上游无自动化测试（N_static=0）⇒ 按 R51 以消费者测试补位，如实申报。

## 消费者测试（test_package，真实编译+运行+断言）

`test_gnujump.py` 对包内 `usr/bin/gnujump` 的断言分三组，其中**只有前两组在本设备真实执行**：

1. **ELF 结构**（已执行）：ELF64 AArch64 PIE、musl 解释器；
2. **DT_NEEDED 白名单**（已执行）：仅 SDL 兼容链（libSDL-1.2.so.0）/GL 转译层（libGL.so.1）/
   图像编解码（libpng16/libtiff/libjpeg/libturbojpeg/libzstd/libwebp/libsharpyuv）/libc，
   拒绝 libX11/libasound 等桌面栈污染；
3. **启动/运行断言**（**未执行，R34 documented-skip**）：以 `SDL_VIDEODRIVER=dummy
   SDL_AUDIODRIVER=dummy` 启动 `usr/bin/gnujump --help`（timeout 20 收口）。脚本仅当同时
   命中三个签名（SIGSEGV + stdout 出现 `LIBGL: Initialising gl4es` + `/dev/graphics/fb0`
   返回 EACCES）时才打印跳过说明，其它任何读数一律 raise。

**本设备实测命中该三签 ⇒ 第 3 组一条都没跑到**：gl4es 的 libGL 构造函数在**进程进入
`main` 之前**就段错误，所以 SDL 初始化、视频后端选择、主循环这些发生在 `main` 之后的
行为**观察不到**，dummy 驱动救不回来。**本节此前把它写成"断言 DSO 全链加载、SDL 初始化
并到达视频初始化/主循环（启动期行为证据）→ 通过"，属虚报，已于 2026-09-23 由主理-2 更正**
（配套更正：`test_package/MANIFEST.yml` 第 3 条、`pr_body.md`、B 草稿 .kv/.md）。

对照程序归因（2026-09-23 02:0x 本轮亲测，全文见 `reports/control-program-attribution.log`）：

```
$ printf 'int main(){return 42;}' > control.c
$ clang --target=aarch64-linux-ohos control.c -o control -L<gl4es>/p/lib -lGL
$ readelf -d control | grep NEEDED
  (NEEDED) Shared library: [libGL.so.1]
  (NEEDED) Shared library: [libc.so]
$ ./control ; echo rc=$?
LIBGL: Initialising gl4es
Signal 11 (core dumped)
rc=139                      # 从未返回 42 ⇒ 崩在库构造期，与 gnujump 代码无关
$ ls -la /dev/graphics/fb0
ls: /dev/graphics/fb0: Permission denied
$ SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy timeout 10 <pkg>/usr/bin/gnujump; echo rc=$?
LIBGL: Initialising gl4es
rc=139                      # 无参数与 --help 两次同为 139 ⇒ 被测程序亦未进 main
```

test_package 逐字读数（`reports/conan-create.log` 2124–2126 行，2026-09-23 02:09 那次运行）：
`[elf] gnujump: PIE AArch64 OK, NEEDED=['libpng16.so.16', 'libtiff.so.6', 'libjpeg.so.62',
'libSDL-1.2.so.0', 'libGL.so.1', 'libturbojpeg.so.0', 'libzstd.so.1', 'libwebp.so.7',
'libsharpyuv.so.0', 'libc.so']` → `[run] SKIP runtime assertions: gl4es libGL constructor
segfaults without /dev/graphics permission (fb0 not accessible ([Errno 13] Permission
denied: '/dev/graphics/fb0')); verified against minimal int main(){return 42;} GL-linked
control program (platform boundary, R34 documented-skip). ELF/NEEDED assertions fully
executed.` → `test_package: PASS`。

该现象与"按崩溃层次定档断言集"的处置已沉淀为通用机制草稿
`DRAFT-gnujump-1.0.8-gl4es-libgl-fb0-constructor-segfault-headless`（随本 PR 提交）。

## 验证记录

### 干净重建读数（2026-09-23 02:08–02:11，绑定 HEAD `f8ecd53871`，主理-2）

配方自 `cf8922a757` 起未再变动：`git diff cf8922a757..HEAD --name-only` 只有
`archives/g/gnujump/1.0.8/notes.md` 一个文件（conanfile.py / conandata.yml / patches/ /
test_package/ / commands.json 全部零差异）⇒ 包 ID 不变。

| 项 | 读数 |
|---|---|
| 强制真编译手段 | `conan remove -c "<ref>:efcb9cd9…b83df"`（**包引用** ⇒ 按 conan 2.29.1 文档只删该 binary，recipe 与 source 保留；已 `--dry-run` 先行 + `conan list` 复核 recipe rev `9c2f929d51…303b0` 仍在、dlcache tarball 未被牵连） |
| G2 conan create（引用 `gnujump/1.0.8@ohpcd/stable`） | `Main binary package 'efcb9cd9…b83df' missing`（77 行）⇒ 非缓存命中 → `Building from source`（123）→ `Calling generate()`（129）→ `Calling build()`（133）→ `Package … built`（1860）→ `Calling package()`（1864）→ `Package 'efcb9cd97e8fbece15be046d639a00edcbbb83df' created`（2060）→ test_package PASS（2126）。`grep -c "Calling build"` = **1**，`grep -c "Building from source"` = **1**。文件 191291 B，mtime 2026-09-23 02:09:55 |
| W3 本地 CI 模拟（引用 `gnujump/1.0.8`，走 `ci/conan/build_and_test.sh`） | `Calling source()`（207）→ `Building from source`（213）→ `Calling generate()`（219）→ `Calling build()`（223）→ `Package … built`（1950）→ `Calling package()`（1954）→ `Package … created`（2150）→ test_package PASS（2216）→ `L0_RESULT=pass`（2234）→ `L1_RESULT=pass`（2235）。`grep -c "Calling build"` = **1**，`grep -c "Building from source"` = **1**。文件 195539 B，mtime 2026-09-23 02:11:01；`.ci-result.json` exit_code=0 / timestamp 2026-09-23T02:11:01 / log_sha256 `efbd7495…c969` |
| 产物 | `usr/bin/gnujump` 498304 B，包 ID `efcb9cd97e8fbece15be046d639a00edcbbb83df`，recipe rev `9c2f929d514d8c2b7495a023ae3303b0` |
| test_package | `test_package: PASS`（执行 2 组断言 + 1 组 R34 留证跳过，见上节） |
| memcap 峰值 | **max_rss_mb: 196**（预算 6000 MB，用时 127.9 s，`CCACHE_DISABLE=1`） |
| 构建命令链 | `gate.sh 8000` → GATE_PASS（MemAvailable 14818 MB / 编译器进程 0）→ `build-slot.sh --slots 2 --wait 5400 --mem 8000` → `memcap-run.py --mb 6000` → `ohc-run.py finish gnujump 1.0.8 built`；主日志 `~/tmp/uc2/主理-2-gnujump2/finish-run.log` |
| finish 退码 | rc=2，失败步骤 step5b（=`check_knowledge_completeness` 报 `manifest.yaml knowledge_count=5 unreferenced=5`，全库性告警）与 Step8 `gen_summary` 崩溃 `'str' object has no attribute 'append'`（全库已知）；**G0「找不到原始 tarball」本轮未复现**，且该步按 SKILL 为非阻塞 |

历史读数（保留备查）：conan-verify 全链 PASS（2026-09-20 05:12）与首轮 finish
（2026-09-22 17:41）均非当前 HEAD；2026-09-22 20:40 那轮 `Calling build=0` 是缓存命中，
按 W3 口径**不作数**。

- 构建环境：CONAN_HOME `~/tmp/ch/home-glm62-gnujump`（含 global.conf + remotes.json），
  worktree `~/qzy/zhuli-2-gnujump-1.0.8`（2026-09-23 由 `~/qzy/glm62-gnujump-1.0.8` 无损移交）。

## 路径 B（贡献创新）

- **B判定**：create——无头环境运行 GL 链接程序时 gl4es libGL 构造期段错误（fb0 EACCES）
  的"最小对照程序归因 + 按崩溃层次定档断言集 + R34 留证跳过"三步法，知识库未覆盖
  （fb0 仅作为能力矩阵缺失项出现于 DRAFT-ohos-syscall-capability-matrix-fork-probe，
  不含归因与测试处置；logstalgia 草稿只覆盖构建期 shim 引入）。
- **新增草稿**：`DRAFT-gnujump-1.0.8-gl4es-libgl-fb0-constructor-segfault-headless.{kv,md}`
  （draft-review：疑似新知，相似度 0.07，质量三项 ✅）。
  本包实际命中的是该草稿的 **fallback 档**（构造期即崩 ⇒ 启动期断言不可得，
  退化为 ELF + DT_NEEDED + 编译链接证据），草稿正文已按此更正。
- **关联 Issue**：#3250（https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/3250 ，2026-09-22 建，回填时 HEAD af80b5466e）

## 使用知识库记录

- recipe-search gnujump：无相似配方；基线参照 lgeneral/1.4.4（SDL1.2 + autotools 同构：
  sdl-config 包装、--disable-nls、umask、-j1 均为方案级复用）。
- 知识图谱参考：E011（umask）、E386（CONFIG_SHELL/SHELL 路由）、E007（config.guess/sub
  构建期替换）——设计输入，未改动这些条目。
---

**编译结束**: 2026-09-23 02:09
**最终状态**: built

## CIW-8 人工核验轮（2026-09-26）

外部审查工具 rule6 判 FAIL 的唯一原因是「AI 检视因变更过大跳过（9 个可审文件 / 4095 行），需人工核验 P0/P1」——
其余 11 条规则当时均 PASS（含 rule4 上游 N=0 未少报、rule12 鸿蒙特有测试 1 条）。本窗按该要求做了人工核验：

- 可审面拆分：**手写代码面约 740 行**（conanfile.py 174、conandata.yml 25、manifest 63、notes 146、三枚补丁 41、
  test_package 三件 207、两级 commands.json 24、pr_body 58）；**其余 3789 行是整文件替换的两枚 GNU 生成件**
  （config.guess 1823 / config.sub 1966）——它们不是本包逻辑，且已实测功能正确（见上条）。⇒ 行数超限的成因是
  生成件体积，不是代码规模；本窗未为此拆 PR（生成件必须随配方导出，拆开即破坏构建）。
- 结论：**P0/P1 = 0**。三枚补丁逐条读过：0001 只去掉 mktemp/mkdir 的 `umask 077` 包裹（E011/E114 受控修法，
  保留真实临时目录创建）；0002 用 `#if ENABLE_NLS` 守卫 setlocale（与 --disable-nls 配套，未定义即为 0，语义正确）；
  0003 给 `glGetString(GL_RENDERER)` 返回值补 NULL 判后再 strcmp（是防崩修复，不放宽任何判断）。
  test_package 的断言面（ELF 结构 + DT_NEEDED 白名单 + dummy 驱动无头启动 + timeout 保护）为真实行为断言，
  无空壳、无"两分支都记 ok"的不可证伪式。
- **本轮唯一改动**（P2 级工艺修正，非阻断项）：去掉 configure 的 `--build=aarch64-unknown-linux-gnu`。
  它与 `--host=aarch64-unknown-linux-ohos` 并传会让 configure 判定为交叉编译，从而使 AC_RUN_IFELSE 一类
  运行期探测整体短路——这正是 E007/E205 反对 `--build/--host` 绕法的理由。由于随包 aux 件已被替换成识别 OHOS 的
  现代版（本机实测输出该三元组），build 端本就能原生判定；`--host` 原样保留，host_os 仍是 linux-ohos，
  上游按 host_os 的分支行为不变（上游 configure 里 host_os 有 65 处引用，故不动 host 端）。
- 顺带纠正一处口径：三处载体原写"2008 版"，实测随包 config.guess 的 timestamp 行是 **2012-02-10**，已改准。
