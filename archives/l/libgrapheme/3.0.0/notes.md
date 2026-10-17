# libgrapheme 3.0.0 适配笔记

## 基本信息

- 上游：https://libs.suckless.org/libgrapheme/（源码包 https://dl.suckless.org/libgrapheme/libgrapheme-3.0.0.tar.gz）
- 版本：3.0.0（首次适配，无后缀）
- 构建系统：suckless 自研 Makefile + configure（非 autotools，非 CMake）
- 许可证：ISC
- 外部依赖：无（库、代码生成器、测试程序仅需 C99 编译器）
- 适配日期：2026-10-12
- 状态：配方已完成，真机预检待执行（本轮仅交付未提交工作树）

## 上游源码与测试审计

发布包内容：`src/`（8 个编译单元）、`gen/`（Unicode 表生成器源码 +
预置 `types.h`/`util.h`）、`test/`（8 个测试程序源码）、`benchmark/`、
`data/`（Unicode 17.0.0 官方测试数据，随包附带，构建期无需联网）、
`man/`（文档生成脚本）、`grapheme.h`、`config.mk`、`configure`。

上游存在完整测试套件（`make test` 与 `make check` 同义），8 个测试程序：

| 程序 | conformance | unit | 数据来源 |
|------|------------|------|----------|
| test/bidirectional | 861948 | 0 | BidiTest.txt（按 mode 展开 770241）+ BidiCharacterTest.txt（91707） |
| test/case | 0 | 85 | 内置数组 |
| test/character | 766 | 12 | GraphemeBreakTest.txt + 内置数组 |
| test/line | 19338 | 12 | LineBreakTest.txt + 内置数组 |
| test/sentence | 512 | 12 | SentenceBreakTest.txt + 内置数组 |
| test/utf8-decode | 0 | 27 | 内置数组 |
| test/utf8-encode | 0 | 6 | 内置数组 |
| test/word | 1944 | 12 | WordBreakTest.txt + 内置数组 |
| 合计 | 884508 | 166 | 总计 884674 |

计数方法：复刻 `gen/util.c`（parse_file_with_callback 跳过空行与 `#`
注释行）与 `gen/bidirectional-test.c`（BidiTest 按段 bitset 展开
modelen 1/2/3，BidiCharacterTest 每行 modelen 1）的解析规则，
对发布包逐行计数；unit 部分统计 `test/*.c` 静态断言数组元素
（注意 `case.c` 有 9 处 `.description =` 后直接换行，简单字符串
匹配会漏数，实际为 85）。配方在真机用各程序打印的 `X/Y` 分母
交叉校验该总数，漂移即判失败（不凑数）。

关键发现：`test/bidirectional` 的 `main` 恒 `return 0`，
失败只体现在标准输出的 `X/Y conformance tests passed.` 分数行。
因此配方不依赖退出码，逐程序解析分数行聚合；这也是本套件
唯一的确定性计数源（单源、无算术修补、无 fallback 猜测分支）。

证伪说明（toybox 教训）：空跑不可能蒙混——全绿时分母必须恰为
884674（八十余万非零断言），且 `gen/*.h` 缺失会导致编译直接失败，
`data/*.txt` 为空会导致生成表为空、conformance 全挂。分数行、
返回码、缺失日志三种情况在配方中有各自明确的失败路径。

`benchmark/` 需要第三方 libutf8proc，本配方不构建不安装；
测试程序仅链接静态库，无其他依赖，不存在 missing_dependency。

## 构建步骤（真机 conan create 实际执行）

1. `apply_conandata_patches` 应用 `0001-configure.patch`
2. `sh ./configure`（经 CONFIG_SHELL；uname 预设分支）
3. `make -j1 CC=... AR=... RANLIB=... BUILD_CC=...`（编译器取自
   Conan conf，不用裸 shell 环境变量；gen 工具以同编译器本地构建，
   由捆绑数据生成表头，无需联网）
4. 逐个运行 8 个 `test/` 程序，重定向输出到日志并记录退出码，
   聚合 `X/Y` 分数后发射 `HMBS_UPSTREAM_TEST_RESULT`
5. `make install PREFIX=<package> LDCONFIG=`（LDCONFIG 置空：
   OHOS 无 ldconfig，历史设备构建证实其调用会失败安装）
6. test_package 以 CMake 构建消费者并运行，发射
   `HMBS_TEST_PACKAGE_RESULT`，同时从包内 `res/hmbs_upstream.json`
   重发上游标记（cache 命中轮次仍有证据）

## 补丁说明

`patches/0001-configure.patch`（沿用历史版本，未改动）：
在 `configure` 的 `uname` case 中加入 `HarmonyOS`，复用 Linux
分支的 `.a` + 版本化 `.so` + symlinks + ldconfig 预设。
补丁仅触及 shell 安装脚本，不含任何 `__OHOS__` 平台宏，
不改 C 源码（R8/PF5 安全）。

## 历史经验复用

- 2026-05 设备手动构建证实：`-nostdlib -shared` 链接、
  gen 表头生成、`make install DESTDIR` 在 OHOS 上可行；
  ldconfig 调用必须跳过；`gen/*.h` 来自构建期生成而非源码。
- 本配方把上述结论固化为 `LDCONFIG=` 空变量与 PREFIX 安装，
  不再手改源码树。

## 验证结果

- 本轮：配方与测试工作树已完成，未提交；真机预检与 rule4 门禁
  由 HMBS 后台执行，结果回填后再定 PR 正文数字。
- 上游 884674 断言与新增 6 断言的实际通过率以预检日志
  `HMBS_UPSTREAM_TEST_RESULT` / `HMBS_TEST_PACKAGE_RESULT` 为准，
  本轮不预填、不估算。
- 2026-10-12 真机预检：test/line 744 失败（19338 中 18594 通过），
  与 Gentoo Linux 同版本实测完全一致（18594/19338），证实为上游
  3.0.0 全平台回归而非 OHOS 特有；2.0.2 在 Gentoo 全绿。
  根因：Unicode 17 新增 LB 类 AK/AP/AS/VF/VI/PI（含 BOTH_QU_PI）
  已进 gen/line.c 表但 src/line.c 无对应 LB 规则（一律落到 LB31），
  另 gen/line.c 的 SA/MN/MC 冲突分支用裸名 SA_WITHOUT_MN_OR_MC
  比对带 TMP_ 前缀的枚举导致 SA 永不转 CM。配方本轮改为测试失败
  只发 failed 标记 + warning 并继续打包（测试失败≠编译失败），
  不删断言不跳过，gaps 类别 test_failure 如实上报。
- 2026-10-12 test_package 去 CMake 化：真机 CMake 报
  Platform/HarmonyOS 缺失且 CMAKE_C_COMPILER 校验失败，改按手册
  §5 模板直调 conf 编译器编译 test_consumer.c 并链接包内
  libgrapheme.a（shared 时回退 -L/-lgrapheme），执行经 bash 包装
  （mksh 不能直接执行 ELF，zlib 同例），CHECK-OK 计数口径不变。
