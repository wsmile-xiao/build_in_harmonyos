# courier-unicode 2.6.0 适配笔记

## 基本信息

- 三方库名称: courier-unicode
- 上游版本: 2.6.0 (2026-06-18 发布)
- 上游仓库/主页: https://www.courier-mta.org/unicode/
- 源码包: https://downloads.sourceforge.net/project/courier/courier-unicode/2.6.0/courier-unicode-2.6.0.tar.bz2 (707445 字节)
- 构建系统: autotools (configure + make, 发布包已含 Autoconf 2.72 生成的 configure 与 Makefile.in)
- 许可证: GPL-3.0-only
- 依赖: Linux 无外部依赖; OHOS 上依赖 libiconv/1.17.1 (GNU iconv,
  修复 musl 回退语义, configure 以 LIBS="-liconv" 自动选用)
- 编译日期: 2026-09-08
- 状态: built (配方已完成, 待真机预检实测后更新验证数字)

## 编译步骤

标准 Autotools 配方流程 (conanfile.py):

```bash
conan create archives/c/courier-unicode/2.6.0 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing
```

1. `source()`: 下载源码包并按 sha256 校验解包。
2. `generate()`: AutotoolsToolchain, 默认静态 (`--enable-static --disable-shared`)。
3. `build()`:
   - OHOS 上先打构建脚本补丁 (见下)。
   - `configure`, `make -j1`, `make check` (上游测试, 见审计)。
4. `package()`: `make install`, 删除 `*.la`, 安装 COPYING 到 licenses。
5. `test_package`: CMake 消费者测试, 14 个真实 API 断言。

## 上游测试审计

结论: 上游存在测试, 必须接入, 不得声明 no_tests。

- 测试入口: `Makefile.am` 的自定义 `check-am` 目标 (注意: 上游没有注册
  automake `TESTS`, 因此 `make check` 无 PASS/TOTAL 汇总行, 任一断言失败
  即以非零退出码中断)。
- 构建的测试程序 (`noinst_PROGRAMS`, 共 9 个):
  unicodetest, graphemetest, linebreaktest, wordbreaktest, enttest,
  scripttest, biditest, biditest2, normalizetest。
- `make check` 实际执行 (发布包内可运行部分):
  - 直接运行: `./unicodetest`, `./enttest`, `./normalizetest` (3 项)。
  - shell `test` 断言: unicodetest 驱动 28 项 (含 8 项1023 字节长串边界),
    graphemetest 驱动 34 项 (GB3-GB999), biditest 驱动 3 项, 共 65 项。
  - 合计 68 项可执行检查。配方在构建时从生成的 Makefile 实时计数
    (`test "\`./` 出现次数 + 裸 `./unicodetest|enttest|normalizetest` 行数),
    数字来自构建产物而非硬编码。
- 上游自跳过 (所有平台一致, 非 OHOS 特有):
  - linebreaktest / wordbreaktest 完整回归需 `LineBreakTest.txt` /
    `WordBreakTest.txt`, biditest / biditest2 完整回归需 `BidiTest.txt`,
    上述数据文件未随发布包提供 (需从 unicode.org 另行下载,
    见 Makefile.am `update-www-*` 目标), check-am 以
    `test -f ... || exit 0` 跳过。
  - scripttest 构建但未被 check-am 调用 (上游行为)。
- 计数口径: counting unit 为一个 check-am 检查
  (直接执行或单条 test 断言), 共 68 项; 4 个数据驱动套件按上游自跳过
  口径在补充说明中声明, 不计入通过数。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 2026 年版 config.guess/config.sub 不识别 HarmonyOS 三元组, OHOS 上 configure 可能报 `cannot guess build type` / `OS ohos not recognized` | config.guess 无 HarmonyOS 分支, config.sub 无 ohos-linux (知识库 E007) | 在 `build()` 中 OHOS 条件下补齐: config.guess 在 `*:NetBSD:*:*)` 前插入 HarmonyOS 分支; config.sub 加 ohos-linux 三元组、KERNEL-OS 列表与内核列表三处。全部按锚点条件替换, 锚点缺失则告警跳过。参考 `scripts/patch-autotools-ohos.pl` 与 cppi 先例 |
| 2 | configure 首行 `#! /bin/sh` 在 OHOS 上可能无法执行, 且 profile 的 `/data/service/hnp/bin/bash` 在预检机缺失导致 configure[139] 失败 | OHOS 无固定 shell 路径 (知识库 E165, cppi 先例; 预检 shell 为 /bin/sh) | OHOS 上探测实际存在的 shell 改写 shebang, 清理 configure 内硬编码的 profile bash 路径, 并经 os.environ+conanbuild 脚本覆盖 SHELL/CONFIG_SHELL (conan 无 environment_append) |
| 3 | `make check` 无标准 PASS/TOTAL 汇总, 无法直接摘录通过数 | 上游 check-am 为自定义目标 | 配方从生成的 Makefile 实时统计检查项数量 (68), `make check` 退出码为 0 即全部通过, 经 HMBS_UPSTREAM_TEST_RESULT 上报 |

## 源码修改

- 无 `patches/` 补丁。OHOS 构建脚本适配在 `build()` 内按锚点条件完成
  (仅涉及 configure/config.guess/config.sub 生成脚本, 不触及库源码,
  无 `__OHOS__` 平台宏, R8/PF5 安全)。

## 依赖版本

- OHOS 上 conan 依赖: libiconv/1.17.1 (GNU strict-EILSEQ iconv,
  修复 musl '*' 回退导致的 unicodetest test1 失败; Linux 仍无 conan
  依赖, 用 libc iconv)。构建期需要: perl (configure 硬性检查), C++17 编译器
  (`AX_CXX_COMPILE_STDCXX_17`), iconv (configure 探测, 缺失自动回退)。

## 验证结果

- 首轮: 配方与测试已完成, 待 HMBS 真机预检 (`conan create` + `make check`
  68 项 + test_package 14 项) 后回填实测数字。
- test_package 断言 (14 项, 全部调用真实 API):
  大小写转换 uc/lc/tc, HTML 实体命名/数字查询, 字符分类
  (isspace/isalpha/isdigit/ispunct), 东亚宽度与 wcwidth,
  latin1 与 UTF-8 双向转换往返, 默认字符集非空,
  通用分类 Lu/Nd 查询。

## 真机预检记录

- Round 1 (2026-09-08): compile 失败 `C compiler cannot create executables`
  (+ preflight.sh `/tmp/... Read-only file system`, HMBS 诊断 readonly_tmp)。
  初版修复做 TMPDIR 定向 (toolchain env + os.environ + conanbuild.sh 补丁)
  与 configure `ac_tmp=$tmp` 重定向 (E114)。复检失败指纹完全相同。
- Round 2 审计 (本机下载官方 tarball 实测, 707445 字节, 与配方 sha256 一致):
  - `ac_tmp=$tmp` 位于生成 configure 约 22308 行, 仅在 configure 末尾
    config.status 生成阶段运行, 与 CC 检查无关, 且其退出 trap
    (`rm -fr "$ac_tmp"`) 会删掉共享任务 tmpdir —— 初版 ac_tmp 重定向
    属错误目标, 已回退 (deliberately left alone)。
  - 本包 config.guess/config.sub 为 2022 版: E007 三处锚点中
    KERNEL-OS 列表与 kernel-OS 列表命中, 但 ohos-linux 三元组块实际为
    2-TAB 缩进, 配方原 3-TAB 锚点静默跳过 —— 已修正 (2-TAB 主锚点 +
    3-TAB 回退)。
  - configure.ac 在 CC 检查前无特殊逻辑 (LT_INIT/AC_PROG_CC/AC_PROG_CXX/
    AX_CXX_C++17-mandatory/PERL 顺序常规), 失败应在编译器调用本身。
  - 本轮策略与 Round 1 不同 (diagnostic-first): 保留 TMPDIR 定向与
    PWD/E007/shebang/umask, 不再覆盖 hmbs 自有的
    HMBS_AUTOCONF_MKTEMP_FALLBACK, 新增失败前 `$CC --version`
    非致命探针与 configure 失败时 config.log 尾部转储
    (`_probe_ohos_compiler`/`_dump_config_log`, 纯诊断, 失败仍抛异常),
    下轮以 config.log 真实编译器错误为依据。
- Round 3 结论 (2026-09-09, 与前两轮不同策略): Round 2 预埋的
  `$CC --version` 探针在真机输出
  `/bin/sh: /data/service/hnp/bin/clang: inaccessible or not found`
  (Error 127), 证实失败根因为 profile 钉死的编译器路径在该预检机上
  根本不存在 —— "C compiler cannot create executables" 只是表象,
  HMBS 的 readonly_tmp 诊断是误报 (源于 preflight.sh 自身写 /tmp)。
  本轮改用编译器发现策略: conf 路径存在即零改动 (健康 CI 机无感知);
  缺失时回退到 PATH 的 clang/clang++, 仅覆盖 CC/CXX 导出,
  不碰 CFLAGS/LDFLAGS (--target/--sysroot); 两者皆无则抛明示环境故障,
  便于后端按 infra 路由而非配方问题。
- Round 4 结论 (2026-09-09, 与前轮"仅 requirements()" 不同策略):
  编译已通但 `make check` 在 `./unicodetest` 以
  `Unexpected result from convert()` 失败 (discovered 68/executed 68/
  passed 0/failed 1)。审计上游 unicodetest.c test1: 输入 UCS-4BE
  (A/U+0414/U+0430/B) 转 ISO-8859-1, 期望 34 字节 `<..>` 转义输出 +
  errflag;musl iconv 以 `*` 替代且不置 EILSEQ, 故输出 `A**B` 无 errflag。
  前轮仅 `requirements("libiconv/1.17.1")` 未真正生效
  (真机编译行无 libiconv 的 -I, 测试仍 musl 语义)。
  本轮改用 recode 先例显式接线: `generate()` 内取 libiconv prefix,
  经 `extra_cflags/extra_cxxflags/extra_ldflags` 注入 -I/-L, 并生成
  `AutotoolsDeps`, 使 configure 的 `LIBS="-liconv"` 探针真正链上 GNU
  libiconv 且 unicode.c 用其 iconv.h;Linux 零改动。

- Round 5 (2026-09-09, package fallback): build + `make check` 68/68 已通,
  失败后移到 `package()` 的 `install-libLTLIBRARIES`:
  `install -c .libs/libcourier-unicode.a .../p//lib/...` 后
  `chmod 644` 报 `No such file or directory`。同机能力为
  `hardlink:0, chmod:0, install_shim:true`，shimmed install 退出 0 但文件
  未落盘，属不支持的文件系统子能力（非 readonly_tmp，HMBS 该条为误报）。
  本轮新增最小兜底：预建 `package/lib,include` 目录，`autotools.install()`
  照常优先；仅当能力信号明确缺失（HMBS_PLATFORM_CAPABILITIES 或
  HMBS_CAP_HARDLINK/CHMOD 为 0）且 install 抛异常时，才用纯 Python
  （copy/shutil，无 ln/chmod）补装 `.a`（.libs 优先）+ 顶层 `*.h` +
  `courier-unicode/*.h` + `*.pc`（shared 时附带非链接 `.so*`），之后照常
  清 `.la` 并装 COPYING。上游测试与断言零改动。
- Round 6 (2026-09-09, test_package compiler): 主包 install 兜底生效后，
  失败移到 `test_package` 的 `cmake.configure()`：
  `CMAKE_C_COMPILER: /data/service/hnp/bin/clang` 在该预检机不存在。
  与主包 Round 3 同因、不同位置。改用 file/5.48.1 先例的适配版：
  存在即用 profile 路径（健康 CI 机零改动），缺失才回退到 PATH 的
  clang/clang++，同步补 `conanbuild.sh` 的 CC/CXX 导出、
  `conan_toolchain.cmake` 中不存在路径的替换，并经
  `cmake.configure(variables={CMAKE_C_COMPILER,CMAKE_CXX_COMPILER})`
  显式传入；test 口径（14 断言）与标记不变。
- Round 7 (2026-09-09, upstream evidence on cache-hit): test_package 14/14
  passed but gate reported `incomplete / missing HMBS_UPSTREAM_TEST_RESULT`
  (discovered 0). Root cause: the marker was emitted only in build(), so a
  `conan create` that hits the package cache ("Already installed!") skips
  build() and the marker never appears in that round's log. Fix follows the
  abuild-sudo precedent: build() persists the marker JSON to
  `upstream_test_result.json`, package() ships it as `res/` in the package,
  test_package re-emits it on every run. Upstream test logic untouched.

## 注意事项

- 本机 Windows 无 Python/Conan, 未在本机运行任何构建; 所有验证留待真机。
- sha256 (`0aed2349...8a08`) 为本机经 SourceForge 官方下载链实测,
  bzip2/tar 完整性校验通过, 与官方 691K 大小一致。
- 分支名按仓库 L0n/L0m slug 规范使用 `feat/courier-unicode-2.6.0`
  (任务描述中的 `feat/courier-unicode-2.6.0` 含首字母与库名间的
  展示空格, 实际分支与归档目录均去空格以通过门禁)。
