# inform6-compiler 6.42 适配笔记

## 上游与产物

- 上游发行包 `inform-6.42-r9.tar.gz`（IF Archive，David Griffith 维护的
  Unix 一体化包，6.42 发行线的最终修订 r9）：编译器 Inform 6.42（C 源码
  `src/`，20 个翻译单元，`inform.c`+`lexer.c`+`syntax.c`+`asm.c`+`verbs.c`
  等）、标准库 6.12.7（`std/`）、PunyInform 5.14.1（`punyinform/`）、演示与
  教程源（`std-demos/`、`std-tutor/`）。sha256=687623aa...f7b34 三路径
  （programming/old、mirror、infocom/old）实测字节一致。
- 版本选择说明：任务版本为 6.42；IF Archive 的 6.42 发行线包含 r1–r9 九个
  打包修订（当前主目录只保留最新发行 6.44-r7，历史发行归档于 `old/`），
  本包采用**最终修订 r9**（官方分发渠道的最后一次 6.42 打包）。Debian 源码包
  inform6-compiler 6.42-1 的 orig 为 GitHub 仓库快照 e528e48（仅编译器源码、
  无 Makefile 与库），本包按官方 Unix 发行包结构适配（与已按同路线适配的
  inform6 6.44-r7 保持同构）。
- 许可证：Artistic License 2.0（`ARTISTIC`、`COPYING` 随包分发）。
- 官方开发仓库 github.com/DavidKinder/Inform6；发行渠道为 IF Archive
  （Inform 社区权威镜像体系，R39 官方源）。

## OHOS 适配

- **零补丁**。平台差异全部收敛在 `src/header.h` 的宏分支：LINUX 分支只定义
  `MACHINE_STRING`/`HAS_REALPATH`/`FN_SEP '/'`/`PATHLEN 8192`/
  `USE_C11_TIME_API`（`__STDC_VERSION__ >= 201112L` 时），均为 OHOS 支持的
  POSIX 语义。构建机 `uname -s`=Linux → 自动 `-DLINUX`，无需干预。
- **构建**：`make CC=<conan conf 编译器> inform-6.42`。6.42 的 Makefile 中
  编译器目标名为 `$(BINNAME)`=`inform-6.42`（与 6.44-r7 的 `inform` 目标名
  不同）；上游 Makefile 的 CC 默认值被注释（`#CC ?= gcc`），必须显式传入
  （R33 取 conf）。`all` 目标还会编译演示 `.z5`/`.z3`——该步骤要用刚交叉
  编译出的 aarch64 二进制在构建机上运行，交叉场景不可行，跳过，库数据原样
  安装。
- **打包布局**：`bin/inform6`（上游以 `inform-6.42` 构建 + `ln -sf` 软链
  `inform`；本包以包名直接落盘规避 R5）、`share/inform6/std/{lib,include,
  demos,tutor}`、`share/inform6/punyinform`、`share/inform6/docs`、
  `licenses/`。上游 `fixlinks.sh` 的 5 个大小写别名（`English.h`→`english.h`
  等，旧游戏源码用大写头）以**文件副本**实现，同样规避软链（R5）。
- **库搜索路径**：编译器默认 `Include_Directory` 在编译期烘焙（Makefile
  `DEFINES` 注入，PREFIX 默认 /usr/local）。鸿蒙上该路径不存在；消费者可用
  命令行 `+目录` 参数（6.42 的上游演示/教程规则 `%.z5`/`%.z3` 即
  `+std`/`-v3 +punyinform/lib` 语法，测试用例 [2/6][4/6][6/6] 同款）指向
  包内 `share/inform6/std/`。
- **6.42 的 `+目录` 实为替换而非文档所述前插**（源码实证）：`main()` 选项
  循环以 `set_path_command(p+1)` 调用（`+` 已被剥掉），而该函数靠
  `command[0]=='+'` 判断前插 → prepend 分支不可达。本地 A/B 实验证实：
  命令行多 `+目录` 时**最后一个生效**（`+LIB +INC` 只剩 INC → 失败；
  `+INC +LIB` 只剩 LIB → 成功）。因此一次编译只传一个 `+目录`——上游
  `%.z5`/`%.z3` 规则本身即如此，测试脚本对齐；需要多目录时用
  `+include_path=dir1,dir2` 单值逗号分隔形式（替换语义正常迭代，本地实测
  编译通过）。
- 构建期防漂移：build() 前核对 6 个关键文件 + 5 个数据目录文件计数
  （std=14、std-include=19、std-demos=9、std-tutor=11、punyinform=222），
  kicad-demos 先例范式。

## 测试口径

发行包**不含自动化测试套件**（无 tests/ 目录、无 make check 目标，R51
清点证据）。上游等效验证 = Makefile 演示编译目标（`stddemos`/`stdtutor`/
`punyhowto`/`punytests`，即用编译器编译全部演示与教程源 → .z5/.z3），交叉
编译无法执行该方式。适配后消费者测试（test_package/test_inform6.sh）：

1. 二进制可执行 + std/lib(19=14+5 别名)/std/include(19)/std/demos(9) 清单
   与大小写别名副本在位；
2. 编译最小游戏 min.inf（Story/Headline 常量 + parser/verblib/grammar 全库
   + Initialise 例程入口，v5——6.12.7 库 parser.h 自带默认 Main 不可重定义，
   游戏入口是 Initialise，上游 advent.inf 同款写法）；
3. Z-code 版本字节断言（产物首字节 = 5）；
4. 编译上游标准演示 advent.inf（全库特性，v5）；
5. 负向用例：语法错误源必须被拒绝（证明编译器真正解析输入，非空壳）；
6. PunyInform 入口编译（globals.h 先于 puny.h 的官方序言，-v3 +lib，
   不定义 Main——puny.h 自带小写 main 主循环），验证 `+目录` 语义。

## 本地预验（Windows MinGW，2026-09-25）

- gcc 13.2 MinGW 以与上游 Makefile 等价的编译行复现构建
  （`-DLINUX -DDefault_Language -DInclude_Directory -DTemporary_Directory`，
  `-std=c99` 走 OLD_TIME_API 分支——MinGW 的 <time.h> 不声明 C11
  timespec_get，本地验证特例；OHOS clang gnu17 正常走 C11 分支）；
  另因 MinGW msvcrt 无 realpath 补了本地 shim（仅验证用，不进配方）。
  产物 banner：`Inform 6.42 for Linux (10th February 2024)`。
- 按 conanfile package() 布局复制出模拟包，test_inform6.sh 六组断言全部
  通过（6/6）。
## 真机验证（OHOS PC 真机，2026-09-25）

- 环境：conan 2.29.1 + 真机 clang（/data/service/hnp/bin）；真机家目录
  默认无 build profile → 先 `conan profile detect` 生成，再
  `conan create . -pr:h ci/conan/profiles/ohos-aarch64 --build=missing`。
- 结果：`** Done building compiler.` → `Package
  '6b129b068851896169fae42d399fa922d239ce8a' created` → 消费者测试
  `inform6-compiler 消费者测试全部通过（6 组断言）`，`EXIT=0`。
  产物 banner：`Inform 6.42 for Unix (10th February 2024)`。
- 真机实跑暴露并修复的两处配方问题（CI Linux 上不会出现）：
  1. 裸 `shutil.copy2` 不自建目标目录 → package() 落盘二进制前先
     `os.makedirs(bin_dir, exist_ok=True)`；
  2. OHOS 真机 /storage 为**大小写不敏感**文件系统（探针实证：CaseProbe.x
     可被 caseprobe.X 访问），5 个大小写别名副本与原名同文件 →
     copy2 抛 `shutil.SameFileError`，按 6.44-r7 同款 `except
     SameFileError: pass` 容错；test [1/6] 的 std/lib 文件数断言放宽为
     19（大小写敏感系统）/14（塌缩）双值。CI Linux 大小写敏感，仍产出
     19 文件全量副本。
- 上游 55 个 punyinform/tests/*.inf 的编译阶段已在本机宿主以等价编译行
  实跑 55/55（运行阶段需 frotz 解释器，交叉场景未执行）。

## 参考

- IF Archive 源目录: https://ifarchive.org/indexes/if-archive/programming/inform6/source/
- DavidKinder/Inform6: https://github.com/DavidKinder/Inform6
- Debian inform6-compiler 源码包（同源打包线）: https://packages.debian.org/source/trixie/inform6-compiler
