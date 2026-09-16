# pachi 12.9 适配笔记

## 编译环境
- 构建系统: makefile（Makefile + Makefile.linux + Makefile.lib）
- 编译日期: 2026-09-10
- 编译器: clang/clang++
- 状态: built（待真机预检确认）
- 上游: https://github.com/pasky/pachi，tag pachi-12.90（12.90 Jowa，2026-04-15）
- 版本说明：任务版本 12.9 为上游 12.90 的任务归一化写法，源码即上游 pachi-12.90（version.h PACHI_VERNUM 12.90），sha256 见 conandata.yml

## 编译步骤

nodcnn 构建（OHOS 无 Caffe/Boost/OpenBLAS/KataGo，不支持 dcnn/josekifix）：

1. `get` 解包 `pachi-12.90.tar.gz`（strip_root=True）
2. `make DCNN=0 JOSEKIFIX=0 BUILD_KATAGO=0 GENERIC=1 OPT=-O1 NO_FRENAME_REGISTERS=1 CC=clang CXX=clang++ AR=llvm-ar XCFLAGS=-g0 -j1`
   - CC/CXX/AR 取自 Conan `tools.build:compiler_executables`（R33），回退 clang/clang++/llvm-ar
   - GENERIC=1 避免 `-march=native`，保证分发可移植
   - OPT=-O1 + XCFLAGS=-g0 + NO_FRENAME_REGISTERS=1：上游默认 -O3 -ggdb3 -frename-registers，
     真机 compile 曾报 Signal 9（SIGKILL，典型 OOM），降优化/去调试信息降内存与磁盘占用，功能不变（纯 MCTS）
   - BUILD_KATAGO=0 显式关闭 KataGo 构建（JOSEKIFIX=0 时本应关闭，双保险）
   - -j1（R9）
3. 上游测试见下节（build() 内真实运行后输出 HMBS_UPSTREAM_TEST_RESULT）
4. 安装：`bin/pachi` + 数据文件（patterns_mm.gamma/patterns_mm.spat/joseki19.gtp/opening.dat）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 默认构建拉起 Caffe/KataGo | Makefile 默认 DCNN=1 JOSEKIFIX=1 BUILD_KATAGO=1，需 Boost/caffe/cmake+Eigen+在线模型 | 关闭：DCNN=0 JOSEKIFIX=0，仅纯 MCTS 引擎，零外部依赖 |
| 2 | t-unit/run_tests 在归档包中无用例 | 该脚本用 `git ls-files *.t` 枚举，tarball 无 .git，结果为空，仅跑 blank.t | 配方用 glob 直接枚举 t-unit/*.t，逐个经 `./pachi --kgs -d2 -u` 运行；blank.t 最后单独跑 |
| 3 | gtp 测试含 dcnn/josekifix 用例 | nodcnn 二进制不支持 dcnn 命令；JOSEKIFIX=0 构建不支持 `pachi-external_engine_mode`/`external_engine_mode`/`gogui-josekifix_*`（gtp.c 均 `#ifdef JOSEKIFIX`，回 `? unknown command` 中断 gtp_check） | 过滤含 dcnn/josekifix/external_engine 行后喂给 t-unit/gtp_check（上游 test_gtp 只过滤 dcnn，因默认 JOSEKIFIX=1；本配方 JOSEKIFIX=0 需多滤后两类，仍为单个真实 gtp_check 用例） |
| 4 | 防假阳性 | exit 0 不等于真跑（空 fixture/静默跳过类坑） | 计数来自真实返回码；.t 非空校验；genmove 用 =500 playouts 真跑并断言含 = 应答，桩二进制必失败 |
| 5 | -t =200 被拒（minimum 500 playouts） | ownermap.h GJ_MINGAMES=500，timeinfo.c 低于下限直接 return false | test_package 与上游 genmove 统一用 =500（=1000 亦可，=500 最快） |
| 6 | dcnn_blunder.t / first_line_blunder.t 在 nodcnn 下必失败 + 4 个 auto-run off 文件 | t-unit/test.c 的两个命令均仅 #ifdef DCNN 注册，DCNN=0 构建报 Syntax error: unknown command；另 board_undo.t/moggy_1lib.t/moggy_semeai.t/moggy_lifedeath.t 头含 `auto-run off`，上游 run_tests 本就 `grep -q 'auto-run off' && continue` 不跑 | 与上游 runner 同口径排除（非 skipped）：前者类比上游 test_gtp 的 `grep -v dcnn`（nodcnn 默认套件无 dcnn），后者与 run_tests 一致直接不枚举；harness 打 HMBS_UPSTREAM_EXCLUDE 明示，JSON skipped=0，discovered/executed 仅计默认套件 |
| 7 | gtp_check 直接执行报 ENOENT rc=127 | gtp_check 为 #!/usr/bin/perl 脚本，真机缺该路径解释器；且 HMBS_CAP_CHMOD=0 不能依赖 +x 位 | 经 PATH 中 perl 显式解释执行（shutil.which("perl")），绕过 shebang/+x |
| 8 | test_package TC3 报 Joseki file joseki19.gtp missing | pachi 按 cwd→$DATA_DIR→exe 目录找数据；包内数据在 share/pachi-go，三者皆不命中 | test.sh 按二进制路径导出 DATA_DIR；package_info 经 runenv_info 声明 DATA_DIR |

## 源码修改

无源码修改，无补丁。

## 依赖版本

无外部依赖（nodcnn 构建仅 libc/libm/pthread/dl）。工具链 clang。

## 上游测试审计

- 来源目录：t-unit/（*.t 脚本 + gtp_check + gtp_test.gtp）、gtp/genmove.gtp
- 接入方式：conanfile build() 内 `_run_upstream_tests()` 真实运行：
  - t-unit/*.t（默认套件：排除与上游 runner 同口径的 6 个非默认用例——2 个需 #ifdef DCNN 命令 + 4 个含 auto-run off，harness 打 HMBS_UPSTREAM_EXCLUDE 明示，不计 skipped/discovered）逐个 `./pachi --kgs -d2 -u`
  - t-unit/gtp_check（nodcnn 过滤，经 PATH perl 显式执行，规避 /usr/bin/perl 缺失与 +x 不可用）
  - GTP genmove smoke（9x9，=500，上游 GJ_MINGAMES=500 下限）
- 标记：build() 末尾打印 HMBS_UPSTREAM_TEST_RESULT（framework=make），数字来自真实返回码聚合
- test_package：test.sh 三个真实用例（--version/--help/GTP genmove），打印 HMBS_TEST_PACKAGE_RESULT

## 验证结果

待 HMBS 真机预检（conan create 全量日志）回填执行数/通过数。预检通过前不提交、不推送。

## 交付物

| 文件 | 说明 |
|------|------|
| bin/pachi | GTP 围棋引擎可执行文件 |
| share/pachi-go/* | patterns/joseki/opening 数据文件 |

## 注意事项

- DCNN/josekifix/KataGo 在 OHOS 上不支持是预期裁剪，不是缺陷；PR 补充说明已声明
- 12.9 即上游 12.90，版本号差异仅为任务归一化，源码同一
