# inform6 6.44-r7 适配笔记

## 上游与产物

- 上游发行包 `inform-6.44-r7.tar.gz`（IF Archive，2026-01 David Griffith 维护的
  Unix 一体化包 r7）：编译器 Inform 6.44（C 源码 `src/`，21 个翻译单元，
  `inform.c`+`lexer.c`+`syntax.c`+`asm.c`+`verbs.c` 等）、标准库 6.12.8
  （`std/`）、PunyInform 6.6（`punyinform/`）、演示与教程源（`std-demos/`、
  `std-tutor/`）。sha256=3e1f94e5...e4bdb 实测。
- 许可证：Artistic License 2.0（`ARTISTIC`、`COPYING` 随包分发）。
- 官方开发仓库 github.com/DavidKinder/Inform6；发行渠道为 IF Archive
  （Inform 社区权威镜像体系，R39 官方源）。

## OHOS 适配

- **零补丁**。平台差异全部收敛在 `src/header.h` 的宏分支：LINUX 分支只定义
  `MACHINE_STRING`/`HAS_REALPATH`/`FN_SEP '/'`/`PATHLEN 8192`/`USE_C11_TIME_API`
  （C11 时），均为 OHOS 支持的 POSIX 语义。构建机 `uname -s`=Linux → 自动
  `-DLINUX`，无需干预。
- **构建**：`make CC=<conan conf 编译器> inform`。上游 Makefile 的 CC 默认值
  被注释（`#CC ?= gcc`），必须显式传入（R33 取 conf）。`inform` 目标只编译
  编译器本体；`all` 目标还会编译演示 `.z5`/`.z3`——该步骤要用刚交叉编译出
  的 aarch64 二进制在构建机上运行，交叉场景不可行，跳过，库数据原样安装。
- **打包布局**：`bin/inform6`（上游以 `inform-6.44` 构建 + `ln -sf` 软链
  `inform`；本包以包名直接落盘规避 R5）、`share/inform6/std/{lib,include,
  demos,tutor}`、`share/inform6/punyinform`、`share/inform6/docs`、
  `licenses/`。上游 `fixlinks.sh` 的 5 个大小写别名（`English.h`→`english.h`
  等，旧游戏源码用大写头）以**文件副本**实现，同样规避软链（R5）。
- **库搜索路径**：编译器默认 `Include_Directory` 在编译期烘焙（Makefile
  `DEFINES` 注入，PREFIX 默认 /usr/local）。鸿蒙上该路径不存在；消费者可用
  命令行 `+目录` 参数（上游 PunyInform 规则 `-v3 +lib` 同款语法，测试用例
  [6/6] 将在真机按此验证）或源内 `+include_path` 指令指向包内
  `share/inform6/std/`。
- 构建期防漂移：build() 前核对 5 个关键文件 + 5 个数据目录文件计数
  （std=15、std-include=19、std-demos=9、std-tutor=11、punyinform=229），
  kicad-demos 先例范式。

## 测试口径

发行包根目录无 tests/、顶层 Makefile 无 test/check 目标，但 **PunyInform
6.6 自带官方测试套件 `punyinform/tests/`：56 个 .inf 测试游戏**（各配 .cmd
转录命令 + .txt 期望转录 + Makefile + compile_all.rb ruby 运行器）。加上 4
个根测试（minimal/cloak/library_of_horror/testbench）与 howto/ 13 个，完整
编译矩阵 = 73 文件 × 6 配置（v3/v4/v5 × release/debug）= 438 次编译，判据
= 零告警（输出含 Warning/Error/(no output) 即失败）。

上游执行链两阶段：①编译阶段（.inf→.z5）适配产物可执行——已按上游
compile_all.rb 同款命令完整执行 **438/438 零告警**（2026-09-25 本地 MinGW
构建 6.44 预验 + 真机 HarmonyOS PC 适配产物复跑）；②转录回放阶段——需
外部 Z-machine 解释器（frotz）回放 .cmd 比对 .txt，解释器不属于本包、
适配环境未集成，未执行（环境限制），测试源码随包安装于
share/inform6/punyinform/tests/ 供有解释器的消费者复现。
适配后另补鸿蒙特有消费者测试（test_package/test_inform6.sh）：

1. 二进制可执行 + std/lib(20/15)/std/include(19)/std/demos(9) 清单与大小写
   别名在位——lib 计数按文件系统自适应：大小写敏感文件系统 20（15 原件
   + 5 个大写别名副本），大小写不敏感（OHOS 真机）15（别名即原文件）；
2. 编译最小游戏 min.inf（Story/Headline 常量 + `Include "parser"/
   "verblib"/"grammar"` + `[ Initialise; ]` 入口——6.12.8 parser.h 自带
   默认 Main 不可重定义，v5）；
3. Z-code 版本字节断言（产物首字节 = 5）；
4. 编译上游标准演示 advent.inf（全库特性，v5；`$DEMOS` 全路径，编译器
   从 cwd 打开源文件不走 Include_Path）；
5. 负向用例：语法错误源必须被拒绝（证明编译器真正解析输入，非空壳）；
6. PunyInform 入口编译（官方最小序言 `!% -~S` + globals.h 先于 puny.h +
   `[ Initialise; ]`，-v3 单 `+目录`），验证 `+目录` 参数生效。
   `+目录` 语义注意（源码实证）：多 `+目录` 是替换语义、最后一个生效，
   一次编译只传一个；多路径用单值逗号分隔。

## 真机验证记录（2026-09-25）

- 设备：HarmonyOS PC（aarch64，非 root 用户 file_manager），Conan 2.29.1，
  profile ci/conan/profiles/ohos-aarch64（clang 15.0.4）。
- `python3 scripts/ohc-run.py conan-verify inform6 6.44-r7` 全门禁通过
  （G0-G4 全 PASS；L2/L4/L5 框架报"无 cache 路径"跳过——其冒烟/产物
  检查意图已由 test_package 实跑二进制覆盖）。
- `conan create` 干净构建：make CC=clang 21 个翻译单元 + 链接 inform-6.44
  一次成功，零补丁、零告警拦截。
- test_package **6/6 全过**：编译器 banner "Inform 6.44 for Unix
  (11th September 2025)" 实跑；min.inf→min.z5（首字节=5）、advent.inf→
  advent.z5（首字节=5）、负向用例拒绝、puny.h→puny.z3（首字节=3）。
- 真机特有适配点：文件系统大小写不敏感 → 大小写别名副本在 package()
  中以 shutil.SameFileError 容忍跳过（别名即原文件），测试计数自适应；
  /tmp 只读 → 消费者测试临时文件全部落在 conan build_folder（R10），
  运行时 TMPDIR 指向 ~/tmp。

## 参考

- IF Archive 源目录: https://ifarchive.org/indexes/if-archive/infocom/compilers/inform6/source/
- DavidKinder/Inform6: https://github.com/DavidKinder/Inform6
- Debian inform6-compiler 源码包（r7 同源打包线）: https://packages.debian.org/source/sid/inform6-compiler
