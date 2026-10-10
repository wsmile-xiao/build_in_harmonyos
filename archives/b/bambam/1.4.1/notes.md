# bambam 1.4.1 适配笔记

## 任务与结论概览
- 任务：bambam 1.4.1（porridge/bambam，GPL-3.0，纯 Python pygame 幼儿键盘敲击/涂鸦
  游戏）适配为 HarmonyOS PC arm64 Conan 包 + 本地可做验证
- 结论：路径 A 基础适配；配方级验证全部通过（py_compile / conan export / conan
  graph info / conan create 本地实跑含 test_package）；上游单元测试 4/4 通过；
  端到端 1 例 OHOS 无 X11 栈不可运行（具体原因见 R51 一节）；待 CI 端 W3/finish 定级

## R47 语言预检与覆盖决策（用户决策，必须写明）
- 实测：`ohc-run.py lang-preflight` 判定 `detected_language=python`（manifest=
  setup.cfg 存在；source_stats：源文件 4 个 python:4 bash:3，主体占比 100%），
  按 R47 协议本应 `env_unsupported` 终态并上报平台 lang_hold。
- **用户明确指示**：走完整适配+PR 流程（覆盖 R47）。依据：
  1. 本仓库有成熟纯脚本包适配先例——`archives/p/pyjson5/0.15.0`（纯 Python JSON5）、
     `archives/a/alot/0.12`（纯 Python CLI）、`archives/b/blendsel/0.11`（纯 Perl），
     均以解释器为运行时依赖交付可安装可验证的 Conan 包；
  2. bambam 上游自带可运行的 unittest（test_e2e_test.py 4 用例，不依赖 pygame），
     端到端测试亦有明确的环境前提，适配质量可验证；
  3. 本机即 HarmonyOS PC（aarch64），conan python/3.12.9 + pygame/2.6.1 预编译
     制品可直接实跑验证（非伪造）。
- 故按用户决策覆盖 R47，走成功路径适配。lang-preflight 已写入
  `$HOME/ohpcd-ai-worker-result.json`（env_unsupported），为预检记录，不改变
  本任务的适配执行；本包交付后由平台侧最终判定。

## 编译环境
- 构建系统: python（纯 Python 无编译，无构建族，参考 pyjson5/0.15.0 打包范式）
- 编译日期: 2026-10-04
- 解释器/图形栈: python3.12（conan python/3.12.9）+ pygame/2.6.1（ohpcd 预编译制品）
- 状态: built（finish 后由工具更新；R29：未 upload 前不标 published）

## W0/R36 依赖发布检查
- `conan download python/3.12.9 -r=ohpcd --only-recipe` → revision d8eda770... ✅
- `conan download pygame/2.6.1 -r=ohpcd --only-recipe` → revision dfd4fb23... ✅
- 二进制包本地实拉（ohos-aarch64 profile）：python/3.12.9 包 6c7db42... 已装；
  pygame/2.6.1 包 ac576360... + 依赖链（freetype/libpng/sdl2-image/sdl2_ttf 等）
  已装并实跑验证（import pygame 2.6.1 OK）✅

## 源码
- 官方 GitHub tag v1.4.1：`https://github.com/porridge/bambam/archive/refs/tags/v1.4.1.tar.gz`
- 本地 tarball sha256 = `eb519ac628900056641e70c5c8f69b44e107b83bdc09d20a996f48da660518dc`
  （与任务给定一致；curl 直连官方 URL 实测 HTTP 200 size=6863571 与本地逐字节同大小；
  gh-proxy 镜像兜底 HTTP 200）
- 源码形态：bambam.py 单文件 804 行（无 C/C++），data/ 24 个图片声音，
  extensions/alphanumeric-en_US/（event_map.yaml + 36 个 ogg），COPYING（GPL-3.0）

## 适配要点（配方设计）
1. conanfile.py：name=bambam version=1.4.1 package_type=application，
   settings=os,compiler,build_type,arch；requirements(): python/3.12.9 + pygame/2.6.1；
   layout basic_layout；source() 用 conandata sources 的 get()（官方 https URL，
   gh-proxy 兜底，R39 合规）；build() 无编译（仅 apply_conandata_patches，无补丁）。
2. 数据目录发现（上游 run() 逻辑）：`program_base=dirname(realpath(argv[0]))`，
   依次检查 `<program_base>/data`、`dirname(program_base)/share/bambam`
   （即 `<prefix>/share/bambam/data`）、`$XDG_DATA_HOME 或 ~/.local/share/bambam`。
   因此 bin/bambam 放 `<prefix>/bin`，data/ 放 `<prefix>/share/bambam/data`，
   extensions/ 放 `<prefix>/share/bambam/extensions`，即被自动发现（test_package
   以 Bambam()._add_base_dir 实测验证）。
3. package()：bambam.py → lib/python3.12/site-packages/bambam.py（import bambam
   可用，main() 模块级可调用）；data/、extensions/ → share/bambam/；
   COPYING → licenses/；bin/bambam 包装器（shebang env python3，相对路径前置
   site-packages 入 sys.path，`from bambam import main; sys.exit(main())`）。
4. package_info()：includedirs=[] libdirs=[] bindirs=["bin"]；
   runenv_info PYTHONPATH=site-packages、PATH=bin。
5. R38：产物含 CLI → 软件级 commands.json（type=tool，ref bambam/1.4.1，
   commands=[bambam]）。R32 不适用（无 C 编译 settings.os 分支）。R8 无补丁无平台宏。
6. 版本号 1.4.1（R37 首次适配无后缀）。

## R51 上游测试三步法（清点 → 实测 → 回填）
### 清点（已写入 notes 申报表）
| 类型 | 文件 | 用例数 | 说明 |
|---|---|---|---|
| 单元测试 | test_e2e_test.py（TestStreamChecker） | 4 | check_stream 正/反断言，纯 Python，不 import pygame |
| 端到端 | test_e2e.py（main/test_functionality） | 1 | 需 X11/Xvfb + xdotool + sox + ImageMagick + 黄金截图对比 |
| 辅助脚本 | test/find-freetype.sh、test/redirect-stderr-and-run.sh、run_e2e_test.sh | 0 | 非测试用例（xvfb-run 包装/工具） |
| ctest | 无 | 0 | 上游无 CTest |

### 实测（R51 可运行环境实际运行）
- **单元测试 4/4 通过**：本机 python3（3.12.9）在源码根
  `python3 -m unittest test_e2e_test -v` → Ran 4 tests, OK（日志
  .scratch/bambam-subtask/upstream-tests/test_e2e_test.log，源文件 sha256 已录）。
- **端到端 1 例不可运行**（具体技术原因，非"没环境"泛化）：
  1. OHOS CI/本机无 X11 栈：Xvfb/xvfb-run 缺失（实测 command -v 全 MISSING），
     无 DISPLAY 环境；test_e2e.py 依赖 Xvfb `-fbdir` 的 XWD framebuffer 截屏
     （`take_screenshot`→`xwd`），SDL dummy 驱动无真实 framebuffer；
  2. xdotool 缺失：test 需 `xdotool key`/`mousemove` 注入键盘/鼠标事件驱动游戏；
  3. sox 缺失：test 用 `sox -r 44.1k -e signed ...` 分析 SDL disk audio 输出
     （`check_audio`），SDLAudio dummy 无真实音频数据；
  4. ImageMagick convert/import 缺失：黄金截图归一化/裁剪/对比不可用。
  5. 该套件设计为 Debian autopkgtest 专用（AUTOPKGTEST_* 环境变量），非本平台可搬移。
- **test_package 内嵌验证**（对已安装制品，R34 实质执行）：
  ① bin/bambam --help → argparse 在 pygame.init 之前解析，退出 0；
  ② import bambam 冒烟 + 包布局断言（data 图片声音 / extensions event_map.yaml /
     bin/bambam 可执行）；
  ③ 上游 run() 数据目录发现逻辑（Bambam()._add_base_dir(<pkg>/share/bambam)）；
  ④ boot 冒烟（可选）：SDL dummy 短超时运行 bin/bambam，进程存活到超时=进入事件
     循环即通过；SDL dummy 无系统光标（set_cursor 报 pygame.error）如实上报为
     已知 dummy 限制；HNP AppSpawn 拒 dlopen（E212）时降级静态制品校验并如实
     标记 e212Fallback；
  ⑤ 上游 4 个 StreamChecker 单元测试（test_e2e.py+test_e2e_test.py 复制入
     test_package，python3 -m unittest test_e2e_test -v）。
- **通过率回填**：上游 4/4（100%），端到端 1 例不可运行（X11 栈缺失，原因如上），
  非占位符、非伪造。

## HarmonyOS 专项测试（test_package/test_bambam_ohos.py）
- 6 项独立检查（cli_help_exit0 / import_bambam / package_data_layout /
  bin_bambam_present_exec / data_dir_discovery / boot_smoke），全部通过时 exit 0；
  输出 HMBS_TEST_PACKAGE_RESULT=<json> 可审计；E212 时降级静态 5 项校验。

## 本地验证证据（均可复核）
- py_compile：conanfile.py + test_package/conanfile.py + test_bambam_ohos.py PASS
- conan export：bambam/1.4.1 recipe 导出成功（revision 见验证日志）
- conan graph info（ohos-aarch64 ×2）：python/3.12.9 + pygame/2.6.1 解析无冲突
- conan create（W3 轻量版，纯 Python 无大编译）本地实跑通过：
  源码下载（官方 URL）→ package() → test_package 三连全过（--help /
  test_bambam_ohos.py / unittest 4/4）→ exit 0（日志+sha256 见 .scratch/bambam-subtask/）
- 上游 unittest 4/4：日志 .scratch/bambam-subtask/upstream-tests/test_e2e_test.log

## 环境坑位（沿用 SKILL §7）
- /tmp 为只读：临时文件走 $TMPDIR/$HOME/tmp
- 本机常驻 23G 内存应用、可用 <1G：禁止大型 C/C++ 全量编译；bambam 纯 Python，
  conan create 仅装不编，实测完成
- SDL dummy 无系统光标（见上）
- **L1d 假测试误报**：test_package/conanfile.py 的注释/文档字符串里同时写
  "self.run" 与 "(echo|print|true)" 会被 L1d 行内子串匹配误判 fake test——
  不要在 conanfile.py 里"描述 L1d 规则本身"（知识草稿
  DRAFT-bambam-1.4.1-l1d-docstring-self-trigger）
- conan create/py_compile 会在配方目录生成 __pycache__/conan*.sh/metadata 等
  junk：交付前清理（本任务已清理，全树仅 11 个交付文件）

## 待 CI 事项
1. conan create（W3，CI 端完整执行）终态定级（built/published）
2. test_package 在 CI worker（HNP AppSpawn）下验证（E212 降级路径是否触发）
3. finish → submit（W4 审计）→ PR
4. 端到端 1 例在 OHOS 平台不可运行由 PR 说明 + 本 notes 承担
