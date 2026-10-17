# ayatana-ido 0.10.4-v2 适配笔记

## 版本说明

- 上游版本：0.10.4（https://github.com/AyatanaIndicators/ayatana-ido，tag 0.10.4，commit f968079）
- 适配版本：0.10.4-v2（与已合入的 0.10.4 同上游源码 revision，配方级改进）
- 构建系统：cmake（上游 CMakeLists.txt）
- 状态：待真机预检（本轮仅完成未提交工作树，未验证前不 commit/push）

## W0b 历史经验核验（必做）

已研读 `archives/a/ayatana-ido/0.10.4/notes.md`（PR #8294，已合入）：

| # | v1 结论 | v2 核验 |
|---|---------|---------|
| 1 | codeload URL 需 `filename` 声明，否则 BadZipFile | 沿用，URL/sha256/filename 原样保留；sha256 已于 2026-09-09 重新下载验证一致 |
| 2 | 遍历 dependencies 注入全部 libdir（E429） | 沿用（`CMAKE_SHARED/EXE_LINKER_FLAGS` + soname 注入保留） |
| 3 | `GLIB_MKENUMS` 指向 glib 包内真实脚本（E543） | 沿用 |
| 4 | test_package 给 glib-2.0.pc 追加 -lintl | 沿用 |
| 5 | broadwayd + GDK_BACKEND=broadway 无头运行 | 沿用，并扩展到配方 build() 内的上游测试 |
| 6 | 注入 `-Wl,-soname,libayatana-ido3-0.4.so.0` + 复制 `.so.0` 文件 | 沿用 |

环境语义可迁移性：v1 成功取得于 HarmonyOS PC 真机（与官方 CI 同源），结论可迁移；
本轮未偏离 v1 的绕坑结论，差异项见下节。

## v2 相对 v1 的改动

1. `ENABLE_TESTS` 由 OFF 改为 ON：上游 gtest 套件在配方 `build()` 内真实构建并运行，
   不再依赖适配期手动 side build（满足“只要上游存在测试就必须接入并完整执行”）。
2. 上游 gtest 源码随配方 vendor（`conandata.yml: gtest_source`，URL/sha256
   复用本仓 `gtest/1.17.0.1` 条目），`build()` 内先构建安装到本地前缀再
   满足上游 `find_package(GTest REQUIRED)`；图中无 gtest conan 节点。
3. `build()` 新增 `_run_upstream_tests()`：broadwayd 无头后端运行
   `tests/gtest-menuitems`，解析 gtest 摘要（`[ PASSED ] N tests` /
   `[ FAILED ] N tests`），输出 `HMBS_UPSTREAM_TEST_RESULT` 机器证据行；
   非全过则抛 `ConanException` 使构建失败（退出码 0 不等于测试真跑了）。
   发现数来自 `--gtest_list_tests` 实测计数（静态审计值 4 仅作交叉校验与回退）。
4. `test_package/test()` 捕获消费者二进制 stdout 并计数 `menu item OK` 行，
   输出 `HMBS_TEST_PACKAGE_RESULT`（`discovered=2/passedCount=实测`），计数不符即失败。
5. 其余（依赖版本、-L 注入、soname、-lintl、broadway 流程）与 v1 一致。

## 上游测试清点（源码审计，2026-09-09）

- `tests/gtest-menuitems.cpp`：4 个 `TEST_F`（BuildCalendar、BuildEntry、
  BuildScaleDefault、BuildScaleSmall），gtest 框架；每个用例 6 个 `EXPECT_TRUE`。
- `tests/CMakeLists.txt`：`find_package(GTest REQUIRED)`，`add_test("gtest-menuitems"
  "gtest-menuitems")`，链接 `-no-pie`。
- 上游测试需显示服务（`gtk_init`/`gtk_widget_realize`），无头环境必须配 broadway 后端。
- `example/` 目录在 `ENABLE_TESTS=ON` 时一并构建（仅构建，不运行）。

## 依赖版本（R36，对齐 gtk/3.24.43 已发布依赖图）

- glib/2.84.0.1（transitive_headers/libs）
- gtk/3.24.43（transitive_headers/libs）
- gtest 上游源码 v1.17.0 随配方 vendor（见 conandata gtest_source；v1 无此项）
- 传递：cairo/1.18.4、cairo-gobject、pango、gdk-pixbuf、harfbuzz、atk、
  libepoxy、fribidi 等（由 gtk 依赖图拉入，-L 由配方自动注入）
- 传递对齐（override，不新增直连依赖）：pixman/0.46.4、fontconfig/2.18.1.1、
  freetype/2.14.3、zlib/1.3.1.1、libpng/1.6.58、expat/2.8.2.1
  （2026-09-09 预检：conancenter cairo 拉 pixman/0.43.4+fontconfig 范围+
  新版 expat/2.8.4，与 ohpcd cairo/1.18.4 + cairo-gobject/1.18.4.2 的
  OHOS 闭包冲突；首轮仅对齐 pixman/fontconfig 后暴露 expat 次生冲突，
  本轮改为一次性原子对齐完整闭包，而非逐个追叶节点；
  同 awf-gtk/avahi 的 expat override 先例）
- 提供者去重（2026-09-09 预检 Provide Conflict：libjpeg/9f 与
  libjpeg-turbo/3.2.0 同供虚拟包 libjpeg）：gdk-pixbuf/2.44.6 直连
  turbo，而 conancenter libtiff/4.7.2 默认 `jpeg="libjpeg"` 拉入 9f；
  同名 override 无法统一两个不同包名的提供者，改在 `configure()` 对齐
  `libtiff:jpeg=libjpeg-turbo`（选项对齐，非版本 override），全图只剩
  一个 libjpeg 提供者（conan-center-index libtiff 配方实证：
  jpeg=[False,libjpeg,libjpeg-turbo,mozjpeg]，默认 libjpeg）

## 源码修改

本轮无源码补丁（patches/ 为空）；全部适配在配方 generate()/build()/test_package 内完成。
patches/ 与 conanfile 新增行均不含 `__OHOS__` 平台宏。

## 证伪计划（真机 evidence 轮执行）

1. 确认 `HMBS_UPSTREAM_TEST_RESULT` 中 `discovered=4/executed=4/passed=4`，
   且 `--gtest_list_tests` 计数与静态审计一致。
2. 确认参照逻辑非空跑：gtest 输出含 4 个 `[ OK ]` 用例行；必要时用桩二进制
   （`exit 1`）重跑，确认 harness 能抓到失败。
3. 确认 `HMBS_TEST_PACKAGE_RESULT` 中 `discovered=2/passedCount=2`，
   且 stdout 含两行 `menu item OK`。
4. 分清“通过”与“静默跳过”：任何 `failed/skipped != 0` 或执行数小于发现数即判失败。

## 待真机验证

- `conan create` 全链路（含上游 4 用例 + test_package 2 项检查）
- 上游测试与新增测试的真实通过率数字（以预检日志为准，回填 PR 正文前不写结论）

---

**笔记更新**：2026-09-09（工作树阶段，真机未跑）

## 2026-09-09 E002 最小适配（未验证）

- 真机失败：compile 阶段 brotli cmake compiler 检查失败 + preflight.sh /tmp 只读（HMBS readonly_tmp）。
- 上一策略（全闭包 override + libtiff jpeg 对齐）未能阻止依赖源码构建首叶失败，改走 E002 环境传播路线。
- 本轮改动：generate()/build()/test_package 复用 HMBS 注入 TMPDIR，有效则用，否则建 build_folder/hmbs-tmp 并经 Environment 定义 TMPDIR/TMP/TEMP；package() copy2 改 copyfile 以避 chmod=0 能力。
- 未跳过任何上游测试（仍 ENABLE_TESTS=ON + 4 用例 + test_package 2 检查）。

## 2026-09-09 第三轮：依赖图剪枝 with_brotli=False（未验证）

- 前两轮无效原因：第二轮 E002 传播（generate/build/test_package 定义 TMPDIR + copyfile）只影响本包自身构建环境，
  而失败点是依赖 brotli/1.1.0（conancenter 配方）在其独立 conan 上下文中 cmake.configure() 失败，
  本包 env 无法触及，故同一指纹第三次复现。
- 新路线（图剪枝，非环境传播）：brotli/1.1.0 仅由 conancenter freetype 经 with_brotli=True 拉入
  （requirements() 写死 requires("brotli/1.1.0")，已用 conan-center-index 现行配方原文核实选项名与默认值）；
  OHOS freetype/2.14.3 本就 --with-brotli=no 且无 brotli 依赖。
- 本轮改动：configure() 新增 try/except self.options["freetype"].with_brotli = False，
  解析到 conancenter freetype 时摘除 brotli 节点，解析到 OHOS freetype 时 except 吞掉（无此选项）。
- 安全性：brotli 仅用于 WOFF2 字体解压，GTK 菜单构件不需要；上游测试 4 用例与 test_package 2 检查保持全量。
- 风险：若图中另有未知节点直连 brotli，本轮剪枝不充分，需按下轮预检日志确认。

## 2026-09-09 第四轮：压缩特性闭包一次性对齐（未验证）

- 上一方案为何无效：第三轮单选项剪枝（仅 with_brotli=False）对其目标有效——
  本轮日志中 brotli 已消失、失败指纹转移到 bzip2/1.0.8（conancenter 配方，
  cmake 4.4.3 "System is unknown to cmake" + CMAKE_C_COMPILER 自检失败，
  HMBS 诊断 readonly_tmp）。逐轮单叶子剪枝无法收敛：conancenter freetype
  的压缩可选依赖是一个集合（brotli/bzip2/png/harfbuzz/zlib），每次只关一个，
  下一轮必然暴露下一个。
- 新路线（闭包对齐，非逐叶追打）：OHOS freetype/2.14.3 本就是零依赖叶子
  （manifest 实证：--with-zlib=no --with-bzip2=no --with-png=no
  --with-harfbuzz=no --with-brotli=no），本轮在 configure() 中一次性对齐
  conancenter freetype 全部五个压缩特性选项；另对 conancenter libtiff 仅在
  存在 bzip2 后端选项时关闭（OHOS libtiff 固定集合无 bzip2，其余后端保持
  与 OHOS 一致的启用状态）。全部 try/except：解析到 OHOS 配方时（无此类
  选项）自动跳过。
- 未采用的路线：① 版本外科手术（freetype 改 2.14.3.1 / gdk-pixbuf 改
  2.44.6.1.1 等 OHOS 独占版本以强制命中 ohpcd 配方）——两版本在制品仓的
  发布状态无法在本地验证，引入 dependency_missing 风险；② 回滚全部
  override 回到 v1 最小图——会复活已确认致命的 pixman/expat 版本冲突与
  libjpeg 提供者冲突。
- 上游测试 4 用例与 test_package 2 检查保持全量；preflight.sh 首行 /tmp
  只读报错属 harness 侧环境上下文（hmbs 统一注入 TMPDIR，已复用），不属
  配方可改范围。

## 2026-09-09 第五轮：gtest 改仓库独有版本，逐出 cmake 工具边（未验证）

- 上一方案是否有效：有效——本轮日志中 bzip2 已消失（压缩闭包对齐达成了
  目标），失败指纹转移到 cmake/4.4.2 工具包：`build() line 35 ... KeyError:
  'OHOS'`（CCI cmake 配方的 conandata 无 OHOS 源码条目）。
- 新失败根因（与上一轮不同策略）：裸 `gtest/1.17.0` 与 conancenter 同版本
  共存，预检 remote 顺序 conancenter 优先即解析到 CCI 配方，其
  tool_requires 拉入 cmake/4.4.2 触发 KeyError。证据链：① 同仓
  asterisk-flite/3.0 注释明确记载同机制同报错（libxml2 案），解法是改用仓
  库独有版本；② atracdenc/0.2.3 为同版本共存问题给 gtest/1.17.0 打了 RREV
  pin（注释写明"Bare 版会被优先解析到 CCI"）；③ 本仓 OHOS 闭包内已核查的
  配方（freetype/autotools、fontconfig/meson、cairo/meson、gdk-pixbuf/meson、
  gtk/meson、libtiff/裸cmake、bzip2/Makefile、gtest/1.17.0.1/CMake）均无
  cmake tool_requires，唯独外部 CCI 配方会引入该边。
- 本轮改动：`tool_requires("gtest/1.17.0")` 改为 `"gtest/1.17.0.1"`（PR #8612
  CI test_package/L0/L1 通过，conancenter 无此版本，自动落 ohpcd 本仓适配
  配方：零依赖、零 tool_requires，CMAKE_PREFIX_PATH 接线逻辑与版本无关，
  无需改动）；manifest.yaml 依赖清单同步；第四轮 freetype/libtiff 对齐保留
  （bzip2 已证伪通过，移除即回归）。
- 未采用：RREV pin（如 atracdenc）——ohpcd RREV 无法在本地合规查询，
  硬写属编造；freetype/libtiff 的版本外科手术——发布状态不明，风险更高。

## 2026-09-10 第六轮：删除 conan gtest 边，vendor 上游源码在配方内构建（未验证）

- 上一方案为何无效：第五轮把 `tool_requires("gtest/1.17.0")` 换成仓库独有
  `gtest/1.17.0.1` 后，真机仍以同一指纹失败（`cmake/4.4.2 build() line 35
  KeyError: 'OHOS'`），且本轮日志明确出现
  `gtest/1.17.0.1: Not found in local cache, looking in remotes...`——即新
  版本已进入被测依赖图，cmake 工具边依然存在。结论：继续在 conan 图内换
  版本/加选项（第三轮 with_brotli、第四轮压缩闭包、第五轮 gtest 换版本）
  属同一根因假设，已连续三轮不收敛；真正的风险是“只要图中存在任何可能
  解析到 CCI 配方的测试节点，就可能引入无 OHOS 条目的 conan 工具包”，
  逐个版本号追打无法证伪。另核实：已合入的 v1（0.10.4，无 gtest 边、无
  override）CI 为绿，cmake 边是 v2 引入 gtest 节点后才出现的。
- 新路线（删边，非换版本）：配方的 `build_requirements()` 整体删除，图中
  不再有任何 gtest conan 节点；`conandata.yml` 新增 `gtest_source`
  （URL/sha256 一字不改复用本仓 `archives/g/gtest/1.17.0.1/conandata.yml`
  的上游 tag v1.17.0 条目，非编造），`source()` 解到
  `<source_folder>/googletest`，`build()` 先用裸 cmake（HMBS_CMAKE /
  user.hmbs:cmake_path / PATH 顺序解析，与 libtiff 裸 cmake 先例一致）以
  同一 `conan_toolchain.cmake` 配置并安装到
  `<build_folder>/gtest-install`（静态 + PIC + C++17，与本仓 gtest 配方
  旗标一致；`gtest_build_tests=OFF`——只跑 ayatana-ido 的 4 个 TEST_F），
  `generate()` 的 `CMAKE_PREFIX_PATH` 改指该本地前缀。上游
  `find_package(GTest REQUIRED)` 在无 conan 节点的前提下得到满足。
- 上游测试 4 用例与 test_package 2 检查保持全量；host 侧已有
  override/对齐（pixman/expat 冲突、libjpeg 提供者、压缩闭包）保持不动，
  它们修复的是各不相同的已证伪失败指纹。
- 证伪信号（下轮预检判定）：① 若 cmake KeyError 消失→删边有效，继续看
  上游 4 用例实测数；② 若 cmake KeyError 仍在→证明工具边来自 gtest 之外
  的基础图节点（非本配方可改范围，需上报环境/基线问题），不再重复换版本。
- manifest.yaml 依赖清单移除 gtest（改为 vendor 注释），其余与第四轮一致。

## 2026-09-10 第七轮：vendor 分支被证伪，收敛到基线/父链缺失（待全量图日志）

- 输入归属判定：16:15Z 预检（= 本地 9-10 00:15）测试的正是第六轮 vendor
  树——其 stdout/stderr 尾部已无任何 gtest 行（15:19 旧日志还有
  `gtest/1.17.0.1: Not found in local cache, looking in remotes`），而
  `cmake/4.4.2 build() line 35 KeyError: 'OHOS'` 原样复现。结论：vendor
  消除了一个 CCI 向量，但 cmake 工具边的父节点不是 gtest。
- 决定性差分证据：第四轮 bzip2/1.0.8 在其独立上下文中跑到了 cmake
  configure（"System is unknown to cmake" 即 configure 已启动）——当时
  conan cmake 工具必有可用二进制；而第五/六轮同一位置变为 cmake 工具包
  源码构建 KeyError。图内请求集合的变化解释不了这一点：第四→六轮只做
  删节点（brotli/bzip2 剪枝）与 gtest 替换（1.17.0.1 经审计零 tool 边），
  删节点不可能新增工具请求。唯一自洽的解释是两次预检之间工具与主机二
  进制可用性同时失效——本轮全闭包 `Main binary package missing` 且 11 种
  cppstd 兼容配置在服务端一个都找不到，连 harfbuzz/14.2.0.1.1.1 这类
  ohpcd 独有版本也无二进制，即 profile/缓存基线变化，而非版本号写错。
- 已审计排除：本仓 gtk 闭包内 glib、gtk、libtiff、freetype、gdk-pixbuf、
  fontconfig、harfbuzz、cairo、pango、atk、fribidi、libepoxy、pixman、
  libffi、pcre2、zlib 共 16 个配方均无 `tool_requires`（grep 全覆盖），
  故 cmake 工具边只能来自 CCI 侧解析节点；但其精确父链在截断摘要中不可
  见，凭记忆指认具体 CCI 配方属编造，不做。
- 本轮动作：不再做推测性版本替换（brotli→闭包→gtest换版本→vendor 四轮
  已穷尽该路线）；保留 vendor（正确方向，减一 CCI 向量）；host 侧
  override/对齐保持（防 pixman/expat/libjpeg 等已证伪冲突复活）。继续推
  进需要的唯一输入：全量依赖图日志中 `cmake/4.4.2` 的父链（或基线侧恢复
  conan cmake 工具二进制/profile 稳定）。测试口径不变：上游 4 用例 +
  test_package 2 检查，零跳过、无断言删除。

## 2026-09-10 第八轮：gdk-pixbuf 子树消除，移出 libtiff 整枝（未验证）

- 为何是不同路线：前五轮（brotli 单剪枝、压缩闭包、gtest 换版本、gtest
  vendor）都是围绕“测试节点引入工具边”做文章；16:15/16:42 两次预检
  （vendor 树，无 gtest 行）同指纹复现，已证伪该方向。本轮转向 host 侧：
  一次 override 消除整个 libtiff 子树，而非逐个追叶节点版本号。
- 根因定位（本地可审计证据）：① 失败图含 `libtiff/4.7.2`，而 gtk/pango/
  cairo/cairo-gobject 的本仓配方均不依赖 tiff；② gtk/3.24.43 pin 的
  `gdk-pixbuf/2.44.6.1` 按其 manifest R37 是开 tiff 版（2.44.6/2.44.6.1
  均启用 libtiff），是 libtiff 及其 tiff-only 伴随依赖（zstd/webp/lerc/
  jbig/xz/libdeflate）的唯一入口；③ 本仓已合入 `gdk-pixbuf/2.44.6.1.1`
 （2026-08-31，`-Dtiff=disabled`，同 glib/libpng/turbo pin，零
  tool_requires），其 manifest 明确记载与 2.44.6.1 的差异就是关 tiff。
- 本轮改动：`self.requires("gdk-pixbuf/2.44.6.1.1", override=True)` 一行
  （复用本配方已有的 override 机制）；libtiff 的 jpeg 对齐保留（guarded
  no-op，防回退）；manifest 依赖清单补齐 override 项。菜单构件库不需要
  TIFF 符号（tiff 是运行时 loader 模块非链接期依赖），无头 PNG 路径不受
  影响；上游 4 用例 + test_package 2 检查保持全量。
- 证伪分支（下轮预检判定）：① 日志中 libtiff 消失且 cmake 边消失→命中，
  继续看上游 4 用例实测数；② cmake 边仍在但 libtiff 消失→父节点在剩余
  裸版本集合（libpng/pcre2/turbo 等），下轮对其中本地有独有 Revision
  者（libpng→1.6.58.1、pcre2→10.45.1.1）逐个 override；③ 若报
  `gdk-pixbuf/2.44.6.1.1 not found`→该 Revision 未发布到制品仓，立即回退
  本行并上报需发布。

## 2026-09-10 第九轮：libffi 锁仓内独有 3.5.2，替换 CCI 3.4.4（未验证）

- 上一方案为何不再沿用：第八轮 gdk-pixbuf 子树消除已生效（本轮日志 cmake
  KeyError 消失，libtiff 整枝移出依赖图），失败指纹转移到
  libffi/3.4.4 configure Error 127；上一轮零改动等待环境恢复后同指纹
  第二次复现，证明被动等待不收敛，必须换主动路线。
- 根因定位（本地可审计证据）：① 预检应用的补丁为 CCI 专属
  patches/0008-3.4.4-invalid-CFI-advance_loc.patch（与 CCI conandata.yml
  的 3.4.4 patch 列表逐项一致，本仓 3.4.4 配方仅有 0001-port-for-ohos +
  0002-umask-fix），故失败节点是 conancenter 配方，非本仓配方；
  ② 直连抓取 CCI conandata 实证其 libffi 仅有 3.3/3.4.4/3.4.6/3.4.8，
  无 3.5.x；③ 本仓顶层 manifest 载明 libffi/3.5.2 status published，
  且 3.5.2 配方位静态库硬化（禁 autoreconf 再生、HMDFS/umask/
  trampoline 补丁、OHOS AArch64 CFI 门禁），manifest 载明靶机执行通过。
- 本轮改动：requirements() 新增 self.requires("libffi/3.5.2",
  override=True) 一行（复用本配方既有 override 机制）＋ manifest 依赖
  清单同步；vendor gtest、压缩闭包对齐、pixman/expat 等已有对齐保持不动。
  glib 链接静态 libffi，上游 4 用例与 test_package 2 检查保持全量。
- 证伪分支（下轮预检判定）：① 日志出现 libffi/3.5.2 且 configure 通过→
  命中，继续看上游 4 用例实测数；② 同一 bash 不可达在 3.5.2 复现→
  证明属工具链/基线环境故障（不同配方同 infra 失败），停手上报；
  ③ 若报 libffi/3.5.2 not found→该版本未发布到制品仓，立即回退本行。

## 2026-09-10 第十轮：libjpeg-turbo 锁仓内独有 3.0.4，替换 CCI 3.2.0（未验证）

- 上一方案是否有效：有效——本轮日志中 libffi 失败消失（9th 锁 3.5.2
  生效，依赖图继续推进），失败指纹转移到 libjpeg-turbo/3.2.0
  cmake.configure()（"System is unknown to cmake" + CMAKE_C_COMPILER
  自检失败）。故本轮换不同叶子、沿用已证实的独有版本机制，不重复旧改动。
- 根因定位（本地可审计证据）：① 本仓 3.2.0 配方共 125 行，build()
  直接 run 裸 cmake（自带 ohos.toolchain），根本没有 cmake.configure()
  调用，而失败是 "build() line 145, cmake.configure()"，故失败节点是
  CCI 配方；② 直连抓取 CCI config.yml 实证其 turbo 版本仅
  3.2.0/3.1.4.1/3.0.2/3.0.1/3.0.0/2.1.5，无 3.0.4；③ 本仓 3.0.4
  manifest 载明 status built，2026-09-05 验证 conan create rc=0 +
  test_package dlopen ok，与 3.2.0 同硬化家族（自带 ohos.toolchain、
  WITH_SIMD=OFF、so 签名），专治"System unknown"类失败。
- 本轮改动：requirements() 新增 self.requires("libjpeg-turbo/3.0.4",
  override=True) 一行＋ manifest 同步；其余对齐（libffi 3.5.2、
  gdk-pixbuf 关 tiff、压缩闭包等）保持不动。libjpeg 仅为 pixbuf
  运行时 loader 依赖，上游 4 用例与 test_package 2 检查保持全量。
- 证伪分支（下轮预检判定）：① 日志出现 libjpeg-turbo/3.0.4 且 configure
  通过→命中，继续看下游与上游 4 用例；② 同一 unknown-system 在 3.0.4
  复现→停手上报基线；③ 若报 3.0.4 not found→未发布到制品仓，立即回退。

## 2026-09-10 第十一轮：回退 3.0.4 pin，改回图默认 3.2.0（未验证）

- 上一方案为何无效：第十轮 pin 3.0.4 的前提被本轮日志证伪——日志显示
  `libjpeg-turbo/3.0.4: Checking remote: conancenter … Downloaded recipe
  revision`，且失败在 `build() line 141, cmake.configure()`；而本仓
  `archives/l/libjpeg-turbo/3.0.4/conanfile.py` 的 build() 只 run 裸 cmake
 （自发现 ohos.toolchain），全文件无 cmake.configure() 调用、
  无 141 行可言。故图中实际使用的是 CCI 配方，不是本仓硬化配方。
- 本地审计证据：① 顶层 `archives/l/libjpeg-turbo/manifest.yaml`
  （HEAD 原样）versions 仅列 3.2.0/3.1.4.1/2.1.5.1，无 3.0.4——
  3.0.4 有版本目录但未发布/未登记，图内无法落到本仓配方；
  ② 3.0.4 版本 manifest 的 `status: built` 只是单包裸 create 验证，
  不代表制品仓有 recipe/binary；③ 同属"built 未发布"的 3.2.0 至少是
  gdk-pixbuf 配方的 pin 版本（`requires("libjpeg-turbo/3.2.0")`），
  跟随图默认比 pin 一个未发布版本更不坏。
- 新路线（回退有害 pin，非再换版本）：按策略周期规则，不得沿用
  "版本号替换"同一根因假设。本轮删除 requirements() 的 3.0.4 override
  一行＋ manifest 同步，改回图默认；保留已证有效的 libffi/3.5.2
  （published，失败消失已复现两轮）、gdk-pixbuf 关 tiff 子树消除、
  压缩闭包对齐、vendor gtest（删 conan 边方向正确）。
- 未采用：继续 pin 其他 turbo 版本（如 3.1.4.1 无 conanfile、
  2.1.5.1 同为 cmd-pkg）——均无 conan 配方，必报 not found；
  给 gdk-pixbuf 关 jpeg——其 recipe 硬 requires 无选项位，不可配。
- 上游 4 用例＋test_package 2 检查保持全量；零跳过、无断言删除。
- 证伪分支（下轮预检判定）：① 图默认 3.2.0 若落到本仓/ohpcd 配方且
  configure 通过→继续看上游 4 用例；② 仍是 CCI cmake.configure()
  同指纹→证明属远端/基线域（全闭包 Main binary missing＋11 种
  cppstd 兼容配置无命中＋/tmp 只读），停手上报，不再做版本 pin；
  ③ 若全闭包二进制恢复→以实测数为准回填通过率。

## 2026-09-10 第十二轮：RREV pin 强制命中 ohpcd 硬化配方（未验证）

- 上一方案（第十一轮回退）是否有效：部分有效——本轮日志证实 3.0.4
  已消失、依赖图回到 3.2.0；但 3.2.0 仍以同一 CCI 指纹失败
  （`CMakeToolchain generated` ＋ `build() line 145, cmake.configure()`，
  而本仓 3.2.0 配方 125 行、无 cmake.configure() 调用）。结论：
  裸版本 pin/回退都赢不了远端顺序竞争，必须换路线。
- 根因定位（本地可审计证据）：① 预检同时连 conancenter 与 ohpcd，
  而 CI 的 setup.sh 明确 disable conancenter——同名版本在预检被 CCI
  优先劫持，在 CI 则不会，这解释了"同配方 CI 可过、预检必败"；
  ② 本仓 atracdenc/0.2.3 notes 实证：同机制（CCI 劫持＋cmake
  KeyError 'OHOS'）已用 RREV pin 解决，日志显示 pin 后命中 ohpcd；
  ③ ohpcd Conan API 实测
  `v2/conans/libjpeg-turbo/3.2.0/_/_/revisions` 返回唯一 revision
  `5ed08e7ff848da8fdf6b7bca74354560`（2026-07-11），与本仓 3.2.0
  硬化验证日期一致；cnb.cool 不支持同版本多 revision，故该值即
  发布时的真实 recipe 内容（非本地复算，避开 atracdenc 第一轮
  "复算 RREV 在 remotes 不存在"的坑）。
- 本轮改动：requirements() 加
  `self.requires("libjpeg-turbo/3.2.0#5ed08e7f…", override=True)` 一行
  ＋ manifest 同步；其余（libffi 3.5.2、gdk-pixbuf 关 tiff、压缩闭包、
  vendor gtest）保持不动。上游 4 用例＋test_package 2 检查保持全量。
- 未采用：再换 turbo 版本（3.1.4.1/2.1.5.1 无 conanfile，必 not found）；
  本地复算 RREV（atracdenc 已证伪，须取 ohpcd 实测值）。
- 证伪分支（下轮预检判定）：① 日志出现
  `libjpeg-turbo/3.2.0#5ed08e7f` 且用本仓配方构建（bare cmake＋
  ohos.toolchain，无 cmake.configure()）→命中，继续看上游 4 用例；
  ② 报 `Unable to find 'libjpeg-turbo/3.2.0#…' in remotes`→RREV
  失配，立即核对 API 值；③ 仍是 CCI cmake.configure() 同指纹→
  RREV pin 未生效，上报并停手。

## 2026-09-10 第十三轮：父节点 cairo RREV pin，整枝消除 lzo（未验证）

- 上一方案（第十二轮 turbo RREV）尚未被测——本轮日志仍是裸
  `libjpeg-turbo/3.2.0` 双远端查询（不带 RREV），即测的是第十一轮树；
  且失败指纹已转移到 lzo/2.10（`System is unknown to cmake`＋
  `build() line 53, cmake.configure()`；本仓 lzo 配方强制
  `CMAKE_SYSTEM_NAME=Linux`，无 unknown-system 可言，故仍是 CCI 节点）。
- 根因定位（本地可审计证据）：① 逐字核对 CCI master 的 cairo 配方：
  `with_lzo` 默认 True，requirements() 含
  `self.requires("lzo/2.10")`；② gtk/3.24.43（本仓）requires 的正是裸
  `cairo/1.18.4`，两远端同名共存，预检优先命中 CCI（与 turbo 同机制）；
  ③ 本仓 `archives/c/cairo/1.18.4/conanfile.py` 实测：requires 仅
  pixman/0.46.4、libpng/1.6.58、freetype/2.14.3、fontconfig/2.18.1.1、
  zlib/1.3.1.1（与本图闭包完全一致），且 `lzo=disabled`——即 lzo
  只是 CCI cairo 的附带叶子，本仓 cairo 根本不需要它；
  ④ ohpcd API 实测 `v2/conans/cairo/1.18.4/_/_/revisions` 返回唯一
  revision `3894814f2279392f808090c9f3d8f200`（2026-08-20）。
- 新路线（父节点消除，非叶子追打）：pin cairo 整枝而非 pin lzo——
  lzo 随 CCI cairo 整枝移出，附带的 meson/pkgconf 工具边一并消失；
  同 override=True 机制（atracdenc RREV 先例）。cairo-gobject
  不直连 cairo（仅 pixman/libpng/freetype/fontconfig/zlib/glib），
  无版本冲突风险。
- 本轮改动：requirements() 加
  `self.requires("cairo/1.18.4#3894814f…", override=True)` 一行＋
  manifest 同步；turbo RREV pin 保留（未经验证，不得回退未证伪的改动）。
  上游 4 用例＋test_package 2 检查保持全量。
- 未采用：pin lzo/2.10 自身——只能救叶子，CCI cairo 的 meson 工具边
  仍在，下轮必爆；仅给 cairo 关 with_lzo 选项——技术上可行
  （`self.options["cairo"].with_lzo=False`，与 libtiff:jpeg 同机制），
  但只能摘除 lzo 叶子，CCI cairo 本体＋meson/pkgconf 工具边仍在，
  不如父节点整枝替换彻底。
- 证伪分支（下轮预检判定）：① 日志出现 `cairo/1.18.4#3894814f` 且
  lzo 整段消失→命中，继续看下游与上游 4 用例；② 报 cairo RREV
  `Unable to find in remotes`→核对 API 值；③ lzo 仍以 CCI 指纹出现→
  pin 未生效，上报停手。

## 2026-09-10 第十四轮：残留双远端版本原子闭包（未验证）

- 上一方案为何无效：第十三轮 cairo 父节点 pin 生效后（lzo 整段消失），
  失败沿工具边转移到 ninja/1.13.2 源码构建（`System is unknown to cmake`
  ＋ `build() line 44, cmake.configure()`）。逐叶 pin（turbo→cairo→…）
  永远追不上：失败不是某个库，而是“任一 CCI 节点源码构建必挂”
  （ hardened 配方注释共识：conan CMakeToolchain 在 os=OHOS 下生成
  cmake 不认的 system 名，必须走自发现 ohos.toolchain＋裸 cmake；
  CCI 配方无此适配）。必须换路线：不再追构建顺序叶子，一次性举证
  并关闭图中全部残留双远端版本。
- 根因定位（全部本地可审计＋双远端实测证据）：① 本轮日志首个从源码
  构建的 conan 包即 ninja/1.13.2（本仓仅有 ninja/1.12.1，故必为 CCI），
  且它以 conan 包身份出现→必有某 CCI 配方的 tool_requires 把它拖入；
  ② 逐字核对 CCI master 当日配方：CCI libepoxy/1.5.10
  `tool_requires("meson/1.3.1")`、CCI pixman/0.46.4
  `tool_requires("meson/[>=1.4.0 <2]")`、CCI fribidi
  `tool_requires("meson/[>=1.2.1 <2]")`，而 CCI meson
  `self.requires("ninja/[>=1.10.2 <2]")`（ninja backend 默认）→
  恰好解析到 ninja/1.13.2，父链闭环；③ 双远端共存核对（CCI master
  config.yml 当日值）：libepoxy/1.5.10 有、pixman/0.46.4 有、
  freetype/2.14.3 有（meson 目录）、libpng/1.6.58 有——四者裸版本
  预检必落 CCI；反之 glib/2.84.0.1（CCI 无 2.84 系）、gtk/3.24.43
  （CCI 仅 3.24.51/4.18.6/system）、fribidi/1.0.16（CCI 仅 1.0.13）、
  pcre2/10.45（CCI 仅 10.47/10.43/10.42）、fontconfig/2.18.1.1
  （CCI 最高 2.17.1）均无 CCI 同版本，自动落 ohpcd，无需处理；
  ④ 本仓 libepoxy/1.5.10 实测零 tool_requires 且禁用 glx/egl/x11，
  本仓 fribidi/1.0.16 同样零 tool_requires——pin 后工具边整枝消失。
- 新路线（原子闭包，非叶子追打）：requirements() 一次性 pin 死全部
  四个残留双远端版本（pixman/freetype/libpng 加 RREV、新增 libepoxy
  RREV），meson＋ninja＋xorg-system 工具边随 CCI 整枝移出；RREV 全部
  取 ohpcd `GET /v2/conans/{name}/{version}/_/_/revisions` 实测值
  （libgsf R48 教训：本地复算不可信）：
  libepoxy/1.5.10#92f7e70c459ed2e6a96cd82549e82391、
  pixman/0.46.4#09f648ede446f6abf85a98da455c7562、
  freetype/2.14.3#7e95a2b2401fd12dcbdd2bf748f56b19
  （与 graalvm/pycairo 已验证 pin 前缀一致）、
  libpng/1.6.58#d25df07aba0399181f60ee377e83d701
  （与 pycairo 已验证 pin 前缀一致）。
- 本轮改动：conanfile.py requirements() 四处 RREV＋注释、manifest.yaml
  dependencies 同步；turbo/cairo RREV pin 保留；test_package 仅引用
  tested_reference，无需同步。上游 4 用例＋test_package 2 检查保持全量。
- 证伪分支（下轮预检判定）：① 日志出现 `ninja`/`meson` 整段消失且进入
  ayatana-ido 自身构建→命中，继续看上游 4 用例；② 报某 RREV
  `Unable to find in remotes`→该 RREV 系 API 实测单值，如仍不命中则属
  远端/基线域，上报停手；③ 又出现新的 CCI 源码构建节点→说明闭包仍有
  遗漏，按本轮同样方法（CCI config.yml＋配方原文核对）补 pin。

## 2026-09-10 第十五轮：glib 二进制 miss 溯源与 libffi 发布 identity 恢复（未验证）

- 上一方案是否有效：第十四轮原子闭包对其目标有效——本轮日志中四个
  RREV 全部命中 ohpcd（pixman 09f648ed/libpng d25df07a/freetype
  7e95a2b2/libepoxy 92f7e70c 均 Downloaded recipe revision），ninja/meson
  工具边整段消失。但失败转移到 glib/2.84.0.1 自身源码构建：
  `meson.configure()` 报 `Unknown compiler(s):
  [['/data/service/hnp/bin/clang']]`（Errno 2），gtk/3.24.43 同样报
  主二进制 miss。旧 “追构建顺序叶子” 假设至此终结：新失败点是发布过
  二进制的本仓硬化配方，不是 CCI。
- 根因定位（v1 对照＋服务端实测）：① 已合入的 0.10.4（~09-03 预检通过）
  requirements 仅 glib/gtk 两行、零 override，即其 glib 节点以发布 identity
  （libffi/3.4.4）解析；本轮 v2 把 libffi 切到 3.5.2、gdk-pixbuf 切到
  .1.1，恰好对应两个 miss（glib/gtk），其余版本未动的包无 miss 证据；
  ② gtk 笔记与 libgsf R50 实证 ohpcd 存在 glib shared 二进制且近期可下载，
  故 miss 只可能来自 ID 计算差异，而非远端缺包；③ 本仓 cairo/cairomm
  注释证实 house 配方需显式声明 minor_mode 才能保 ID 稳定，即默认模式会
  嵌入依赖版本——版本切换必然扰动下游 ID；④ 09-04 起 profile 仅加
  LD_LIBRARY_PATH（buildenv，不进 ID），settings 无漂移，排除 profile 因素。
- 新路线（发布 identity 恢复，非叶子追打）：libffi 改回 glib 原生声明的
  3.4.4，并以 ohpcd 现行 RREV（API 实测单值 ca8b0eb4，2026-07-17，与
  libgsf 已验证值一致，刚复核仍有效）锁定硬化配方——CCI 防护不变
  （ohpcd 3.4.4 无 autoreconf 再生，正是第 9 轮失败根因），glib 依赖集
  回到发布 identity。gdk-pixbuf .1.1 保留（回退 .1 会重引 libtiff CCI
  子树，负收益更大；gtk 若仍 miss 则走源码构建，其配方健康）。
- 本轮改动：conanfile.py libffi 行＋注释重写、manifest.yaml 同步；
  test_package 仅引用 tested_reference，无需同步。上游 4 用例＋
  test_package 2 检查保持全量。
- 证伪分支（下轮预检判定）：① 日志出现 glib 二进制复用（无 glib build
  段）→命中，继续看 gtk/上游 4 用例；② glib 仍 miss 但 clang 可用→
  说明另有 ID 差，届时逐项比对 settings/options；③ glib/meson 仍报
  clang ENOENT→工具链在该 worker 不可见，结合第 9 轮 bash ENOENT 与
  v1 通过对照，应上报为真机环境域（停止改配方等恢复）。

## 2026-09-10 第十六轮：gdk-pixbuf 版本回退恢复 gtk 发布 identity（未验证）

- 上一方案为何无效：第十五轮 libffi 恢复发布 identity 对其目标有效（glib 推进，RREV 命中且 ninja/meson 工具边消失），
  但失败转移到 gtk/3.24.43 自身源码构建：generate() 第 110 行 _prepare_glib_build_tools 第 255 行
  _sign_elf 第 492 行 FileNotFoundError（binary-sign-tool 不在此 worker）。逐叶 pin
  假设至此终结：新失败点是发布过二进制的本仓硬化配方，不是 CCI。
- 根因定位（本地可审计）：1）已合入 v1（零 override，~09-03 预检通过）证明发布态 gtk
  二进制存在；2）v2 唯一的版本号切换是 gdk-pixbuf .1 -> .1.1（其余均为同版本 RREV，
  不计入 package_id），恰好对应 gtk miss；3）gtk 配方本身就是不一致的证据：
  package 步 _sign_installed_elfs 缺 signer 时 warn-skip，而 generate 步 _sign_elf 直接 raise，
  即上游预期源码构建环境始终有 signer，正常路径是二进制复用而非源码构建。
- 新路线（发布 identity 恢复，非叶子追打）：删除 8th-round .1.1 override 一行，gtk 直连版本集回到
  发布态；保留全部同版本 RREV（pixman/freetype/libpng/epoxy/turbo/cairo/libffi）、vendor gtest、
  压缩闭包对齐、libjpeg 提供者对齐。libtiff 随 .1 回归，但二进制命中则不构建、不签名。
- 证伪分支（下轮预检判定）：1）gtk/gdk-pixbuf 无 build 段、直接进入本包构建→命中，继续看上游 4 用例；
  2）libtiff 以 CCI 指纹出现→下轮 pin libtiff RREV（需取 ohpcd 实测值）；3）gtk 仍 miss 但不同原因
  →比对 settings/options；4）全闭包仍无二进制（profile 域）→停手上报环境域。

## 2026-09-10 第十七轮：tiff 子树同版本 RREV 闭包（未验证）

- 前次为何无效：第十六轮回退（gdk-pixbuf .1）本身生效（19:09Z 预检日志显示测的正是回退树，
  2.44.6.1 回来了），但失败指纹退回到多轮前的 cmake/4.4.2 KeyError OHOS，且 libtiff/4.7.2 +
  gdk-pixbuf/2.44.6.1 + gtk/3.24.43 全报 Main binary missing。纯回退恢复了 gtk identity，
  却重引入了裸版本 tiff 子树的 CCI 劫持面。
- 根因定位（双远端实测）：CCI master config.yml 当日值证实 libtiff/4.7.2、zstd/1.5.7、
  libwebp/1.6.0 均双远端共存（zlib/1.3.1.1: CCI 仅 1.3.2；expat/2.8.2.1: CCI 仅 2.8.4/2.8.3，
  后两者仓内独有无需 pin）；其中某 CCI cmake 配方的 tool_requires 即 cmake 工具边父链。
- 新路线（与 8th 版本交换、16th 纯回退均不同）：保持 .1 发布 identity，同时以同版本
  RREV 锁死 tiff 子树全部 7 个节点（libtiff/libdeflate/zstd/libwebp/lerc/jbigkit/xz，版本与
  libtiff 要求一致，gdk-pixbuf/gtk 的 ID 不变；RREV 均为 ohpcd v2 API 今日实测单值）。
- 证伪分支：1）cmake KeyError 消失→命中，继续看上游 4 用例；2）某 RREV报 in remotes
  not found→核对 API 值；3）又出现新 CCI 源码构建节点→按同方法补 pin。

## 2026-09-10 第十八轮 vendor gtest 改用 ohos.toolchain.cmake（未验证）

- 前次是否有效：第17轮tiff RREV闭包完全有效（19:14Z预检libtiff/xz/zstd/libwebp均Downloaded ohpcd RREV，cmake KeyError消失，依赖图贯通并进入本包build）。新失败在配方自身：_build_vendored_gtest以conan_toolchain.cmake配置googletest，cmake 4.4.3报System is unknown to cmake且CMAKE_C/CXX_COMPILER sanity失败。
- 根因（仓内实证）：libjpeg-turbo配方注释明确os=OHOS下conan_toolchain发cmake不认的CMAKE_SYSTEM_NAME值（ML-0035），必须用NDK官方ohos.toolchain.cmake（自发现，同libtiff/glfw法）；E550草稿同理。主库configure保持不动（v1预检通过已证主路径可用）。
- 本轮改动：新增_ohos_toolchain()自发现（user_toolchain conf、OHOS_NDK_HOME、真机SDK glob）；_build_vendored_gtest改传官方toolchain加OHOS_ARCH=arm64-v8a，去掉conan_toolchain依赖；其余旗标不变。
- 证伪分支：gtest configure通过则命中，继续看主库配置与上游4用例；主库若同错则下轮再切；toolchain找不到则属环境域停手。

## 2026-09-10 第十九轮：toolchain硬失败改三级回退＋gtest镜像fallback（未验证）

- 前次是否有效：18th的ohos.toolchain切换方向正确但在新worker上硬失败
 （`ohos.toolchain.cmake not found`，profile无user_toolchain、OHOS_NDK_HOME
  未设、SDK glob为空即raise）；gtest官方URL另有两次connect-timeout重试
  （后成功），属下载抖动。
- 根因（本地可审计）：CI profile（ci/conan/profiles/ohos-aarch64）[conf]
  根本无user_toolchain项，主库CMakeToolchain靠OHOS适配版conan隐式映射
  成功generate，故自发现不能hard-raise；build_and_test.sh的GitHub映射
  （gh-proxy.com优先、官方兜底）可直接复用。
- 本轮改动：_ohos_toolchain容忍string型conf、增探OHOS_SDK_HOME等env与
  多glob，找不到回None不再抛；新增_conan_toolchain_file（复用已生成
  的conan_toolchain.cmake）与_native_compilers（conf compiler_executables
  或PATH clang回退）；_build_vendored_gtest按NDK→conan_toolchain→
  原生显式编译器三级回退；conandata gtest_source改有序URL列表
  （gh-proxy首、官方尾，sha256不变）。上游4用例＋test_package 2检查不变。
- 证伪分支：1）日志见fallback warning后gtest configure通过→命中；
  2）仍System unknown→主库同错则属cmake/toolchain基线域，上报停手；
  3）某URL报sha256 mismatch→镜像字节不一致，撤镜像保留官方。

## 2026-09-10 第二十轮：vendored gtest改无cmake直编（未验证）

- 前次（19th三级回退）为何无效：回退链仍全经cmake做系统检测——日志证实
  fallback命中conan_toolchain.cmake后仍报`System is unknown to cmake,
  create: Platform/HarmonyOS`＋CMAKE_C/CXX_COMPILER sanity失败（cmake 4.4.3
  无HarmonyOS平台模块）。换toolchain文件属同一根因假设，按策略必须换路线。
- 新路线（去cmake，非换toolchain）：gtest是纯C++静态库、无平台configure步骤，
  改用原生clang++直接编译（gtest-all.cc/gmock-all.cc单TU聚合，-std=c++17
  -fPIC -O2 -pthread，与本仓gtest配方旗标一致；test无main故另建gtest_main；
  上游仅用gtest头，gmock按需提供），llvm-ar归档，手写最小GTest包配置
  （imported targets＋上游实际链接的GTEST_LIBRARIES/GTEST_BOTH_LIBRARIES等
  legacy变量；主发现仍走cmake自带FindGTest模块经CMAKE_PREFIX_PATH）。
  上游tests/CMakeLists原文已核实（raw.githubusercontent 0.10.4）：
  链接${GTEST_LIBRARIES} ${GTEST_BOTH_LIBRARIES} ${GMOCK_LIBRARIES}、
  仅#include <gtest/gtest.h>、4个TEST_F无main。主库Conan CMake helper路径
  保持v1原样（09-03预检绿，有证可用）。
- 本轮改动：删除_cmake_bin/_ohos_toolchain/_conan_toolchain_file/
  _native_compilers（cmake路线整体移除），新增_native_cxx_tools
  （conf compiler_executables优先、缺失回PATH，复用经验1模式）与
  _write_gtest_config；_build_vendored_gtest不再调用cmake。
  上游4用例＋test_package 2检查不变。
- 证伪分支：1）直编成功且主库configure通过→进入上游4用例实测；
  2）主库configure同报System unknown→证伪“v1路径可用”假设，属cmake/
  基线域（worker cmake无HarmonyOS模块），停手上报环境域；
  3）直编报编译器缺失→环境域停手。

## 2026-09-10 第二十一轮：优先选用支持HarmonyOS平台的cmake（未验证）

- 前次（20th直编）是否有效：有效——失败从_build_vendored_gtest推进到主库
  cmake.configure()（build line 416，CMakeLists.txt:2 project()），指纹同为
  System unknown/Platform/HarmonyOS＋编译器sanity失败。直编绕过了helper的
  cmake，主库仍经Conan CMake helper＋conan_toolchain走同一坏点，证伪分支2命中。
- 根因（本地可审计＋日志）：v1主configure曾绿（09-03），同一v1路径今败，
  差值只能在基线（HMBS托管cmake 4.4.3无平台模块）；配方侧toolchain已穷尽
  （NDK缺失、conan_toolchain坏、新toolchain不可造），剩唯一配方域变量是
  cmake二进制本身。test_package的conan_toolchain同理必撞同点，一并处理
  （同校验同回退，经验1一致性要求）。
- 本轮改动：主配方新增_preferred_cmake()扫描在机cmake并优选带
  Platform/HarmonyOS.cmake者（目录前置PATH供helper取用），无则沿用原顺序
  并明示后继失败属环境域；test_package新增_prefer_harmonyos_cmake()同逻辑。
  不改测试口径、不改依赖图。
- 证伪分支：1）日志见选中某HarmonyOS-capable cmake且project()通过→命中，
  继续看上游4用例；2）扫描无一支持、仍同错→基线域（在机cmake全缺平台模块），
  停手上报等恢复；3）选中后报其他错→按新指纹独立诊断。

## 2026-09-10 第二十二轮：E092 Linux平台别名替代HarmonyOS名（未验证）

- 前三轮为何无效：19th三级回退、20th直编、21st优选HarmonyOS-capable cmake属同一根因假设（必须保留CMAKE_SYSTEM_NAME=HarmonyOS并找能识别它的cmake/toolchain）。21st日志证伪：扫描在机全部cmake（/usr/local/bin与.harmonybrew各一）均无Platform/HarmonyOS.cmake，fallback后主库仍以System unknown/Platform/HarmonyOS加编译器sanity失败告终。按13策略周期规则必须换实现路线。
- 新路线（E092知识库与lzo/2.10在仓先例）：主配方与test_package的CMakeToolchain显式设CMAKE_SYSTEM_NAME=Linux（HarmonyOS与Linux同内核，Linux模块提供SONAME等平台逻辑；ayatana-ido上游CMake仅pkg_check_modules无平台分支，别名行为不变）。主build()改回v1原生CMake(self)，删除整条_preferred_cmake/_prefer_harmonyos_cmake扫描链；vendored gtest直编保留（20th已证有效，失败已推进过该点）。另按经验1加编译器守卫：conf绝对路径优先，仅其含分隔符且非文件/不可执行时告警并回退PATH解析clang，缺省时仅历史绝对路径缺失才pin PATH值（主与test_package一致）。
- 未采用：继续找NDK ohos.toolchain或换cmake版本（基线域，前三轮已穷尽）；CMAKE_SYSTEM_NAME设OHOS/HarmonyOS（E092明确禁止，会致更多错误）。
- 上游4用例加test_package 2检查保持全量；零跳过、无断言删除。
- 证伪分支：1）project()通过并进入上游4用例则命中；2）仍compiler sanity失败则看是否/dangling编译器路径未被守卫覆盖，按新指纹诊断；3）若Linux别名下链接/SONAME异常则对比v1产物。

## 2026-09-10 PkgConfig可执行文件缺失注入（未验证）

- 前次Linux别名有效：本轮日志编译器检测已通过（Detecting CXX compile features done），失败推进到CMakeLists.txt:49 find_package(PkgConfig)报Could NOT find PkgConfig（missing PKG_CONFIG_EXECUTABLE）。属新指纹，非重复旧补丁。
- 根因：v1与本轮均无pkg-config的conan节点，依赖系统PATH；该worker的HMBS工具探测仅列cmake/make/ninja/python3，构建env无pkg-config可执行文件。
- 本轮改动：主配方与test_package在generate内探测PATH加依赖bindir的pkg-config/pkgconf并pin入PKG_CONFIG_EXECUTABLE，同时经buildenv前置其目录；无新conan节点、无CCI引入面、不改测试口径。找不到则告警并交由configure显式失败（环境域）。
- 证伪分支：1）configure越过PkgConfig进入pkg_check_modules与上游4用例则命中；2）仍缺可执行文件则需确认worker是否预装；3）若后续报某pc缺失则按新指纹独立诊断。

## 2026-09-10 PkgConfig改探HNP预装绝对路径加可运行校验（未验证）

- 前次为何无效：通用PATH加依赖bindir探测在真机返回空（日志WARN no pkg-config/pkgconf on PATH），同指纹第二次复现；按规则不得原样重复，必须换策略。
- 新路线（pcre2/10.47在仓先例）：HNP工具链在固定绝对路径预装pkg-config（/data/service/hnp/pkg-config.org/pkg-config_0.29.2/bin/pkg-config），候选经--version可运行校验后pin入PKG_CONFIG_EXECUTABLE；主配方与test_package各加_pkg_config_exe helper。无新conan节点、无CCI引入面、不改测试口径。
- 证伪分支：1）日志出现using pkg-config且configure越过49行则命中；2）该绝对路径亦缺或不可运行则属worker环境域，届时考虑tool_requires pkgconf/3.0.5（burp2/ekg2等多包先例）并pin ohpcd RREV防CCI劫持。

## 2026-09-10 第二十三轮：主库链接补 -lintl（未验证）

- 前次（Linux 别名+shim）有效：configure 已贯通，失败推进到本包 build 93% example/menus 链接：ld.lld --no-allow-shlib-undefined 报 g_libintl_ngettext 未定义（libayatana-ido3-0.4.so 自身缺 DT_NEEDED）。新指纹，非重复旧补丁。
- 根因：gtk 图内无 .pc 输出 -lintl；glib 的 proxy-libintl（glib 包 libdir 下 libintl.so/.a，wv/harfbuzz/gtkspell3 均已实证）未被上游 PROJECT_DEPS_LIBRARIES 引入。test_package 早有同款 -lintl 追加先例并在 v1 通过。
- 本轮改动：generate() 在 -L 注入后统一追加 -lintl（SHARED 与 EXE 均覆盖，DT_NEEDED 写入共享库）；其余（Linux 别名、shim、vendor gtest、上游 4 用例+test_package 2 检查）不变。readonly_tmp 系 harness 首行环境噪声，配方已复用 HMBS TMPDIR，不另改。
- 证伪分支：1）menus 链接通过并进入上游 4 用例则命中；2）仍报 g_libintl_* 缺失则检查 -L 顺序/是否命中系统 libintl；3）报 libintl 找不到则按新指纹定位提供包。

## 2026-09-10 第二十四轮：上游 tests/CMakeLists 漏消费 GTEST_INCLUDE_DIRS，加 -I（未验证）

- 前次（23rd -lintl）有效：configure 贯通、主库 93% 链接推进，本轮失败是新指纹 tests/gtest-menuitems.cpp:3 fatal error: gtest/gtest.h file not found（4452 warnings + 1 error，make Error 1），非重复旧补丁。
- 根因（上游原文实证）：raw.githubusercontent 0.10.4 tests/CMakeLists.txt 仅 include_directories(src + PROJECT_DEPS_INCLUDE_DIRS)，链接用 GTEST_LIBRARIES/GTEST_BOTH_LIBRARIES/GMOCK_LIBRARIES 但从不消费 GTEST_INCLUDE_DIRS；故 CMAKE_PREFIX_PATH 能满足 find_package 链接变量，编译仍缺 -I<build>/gtest-install/include。vendor 直编与 config 文件均已生效（失败点已越过它们到达上游测试编译），缺的只是这一路头文件路径。
- 本轮改动：generate() 在 CMAKE_PREFIX_PATH 后新增 tc.variables[CMAKE_CXX_FLAGS] = -I<build>/gtest-install/include（前向引用安全：_build_vendored_gtest 在 cmake.configure 前建好该目录；无新 conan 节点、无 CCI 面、不改测试口径）。
- 证伪分支：1）gtest-menuitems 编译通过并进入上游 4 用例则命中；2）仍报头缺失则检查 gtest-install/include/gtest/gtest.h 是否实际落盘（cp -r 逻辑）；3）若报链接缺 -lgtest 则按新指纹定位 GTEST_LIBRARIES。
