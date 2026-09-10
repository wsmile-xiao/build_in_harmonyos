# enigma 1.3 适配笔记

## 上游身份（选型审计）

- 任务口径：包名 `enigma`，版本 `1.3`，目录 `archives/e/enigma/1.3/`，分支 `feat/enigma-1.3`。
- 经全网检索（CPAN / metacpan / GitHub / SourceForge / GNU / Repology / PyPI / npm /
  crates.io / Hackage），**唯一**名为 enigma 且版本恰为 1.3 的官方源码分发是
  CPAN 的 `Crypt-Enigma-1.3.tar.gz`（作者 Alistair Francis，2002-04-24）：
  - `https://cpan.metacpan.org/authors/id/A/AL/ALIZTA/Crypt-Enigma-1.3.tar.gz`
  - 同文件亦见于 `https://www.cpan.org/authors/id/A/AL/ALIZTA/`，双源字节一致。
- 排除项：Enigma 棋盘游戏（仅 0.92/1.00/1.01/1.20/1.21/1.30，无 1.3）；
  SourceForge `enigma` 工程（最新 0.55）；GNU 无此包；npm `enigma.js`（JS，
  语言门禁不适用）；Rust/Haskell 同名包（CI 无对应工具链）。
- 结论：本配方 `enigma/1.3` = 上游 CPAN 分发 `Crypt-Enigma 1.3`
  （Perl 模块 `Crypt::Enigma`，`$VERSION='1.3'`）。名称映射沿用 clips-6.3
  前例（任务口径版本 ≠ 上游文件名），此处为任务口径包名 ≠ 上游分发名，
  特此记录。

## 源码包审计（本地解包实测，2026-09-09）

- 文件：`Crypt-Enigma-1.3.tar.gz`，6.4K，
  sha256 `e6f343c268d0a54eb403f9d9000470c557a933183df3bba53036a3e9cc90c587`
  （cpan.metacpan.org 与 www.cpan.org 双源同值）。
- 包内清单（`tar -tf` 全量）：
  - `Enigma.pm`（21495 字节）：`Crypt::Enigma` 主类 + 内嵌
    `Crypt::Enigma::Rotors::*` / `Crypt::Enigma::Reflectors::*`，纯 Perl。
  - `Makefile.PL`（238 字节）：`WriteMakefile(NAME => 'Crypt::Enigma',
    VERSION_FROM => 'Enigma.pm')`，无依赖声明。
  - `t/01.t`（493 字节）：`use Test; plan tests => 1; use Crypt::Enigma; ok(1);`
    ——上游测试共 **1 个**用例（仅模块加载烟雾测试）。
  - `examples/enigma1.pl` … `enigma4.pl`：用法示例（非测试框架）。
  - `README`（安装四步 + `DEPENDENCIES: none`）、`Changes`、`MANIFEST`。
- 许可证：README 声明 "under the same terms as Perl itself"（Artistic/GPL 双许；
  配方 license 字段取 `Artistic-1.0`）。
- 上游测试框架：`make test` → `Test::Harness` 跑 `t/*.t`。

## W0 — 依赖发布检查

- 零依赖：README 明确 `DEPENDENCIES: none`；`Makefile.PL` 无 PREREQ_PM；
  配方 `requirements()` 为空（L0i 自动通过）。
- 构建只需真机基础环境的 `perl` + `make`（同仓 `perl-net-ip/1.26-r7`
  已验证模式，不经过 conan requires）。

## API 行为审计（Enigma.pm 源码级，测试设计的依据）

- `Crypt::Enigma->new([\%args])`：默认 rotors
  `[RotorI,RotorII,RotorIII]`、startletters `[Z,A,A]`、rings `[0,0,0]`、
  reflector `ReflectorB`、空 stecker。**注意：`_init` 只填充 `_settings`，
  不预存 rotor 对象。**
- `cipher($text)`：每调用开头按 `_settings` 调 `setRotor` 重建 rotor。
  上游 1.3（1.4 亦同）原文为 `setRotor($_->[0], , $_->[1], $_->[2], $count)`
  （双逗号，第二个参数为空洞）：`rotorNumber` 实际取到 ring 值，默认全零
  ring 下全部因 `rotorNumber=0` 校验失败返回 0，`_rotorObjects` 保持 undef，
  后续 `_getRotorObjects`（Enigma.pm:283）解引用直接崩溃——真机预检已复现。
  本配方以 `patches/0001-fix-cipher-rotor-setup.patch` 修复：去掉空洞使
  调用与 `setRotor(名,起始字母,ring,号)` 对齐，并将 `_rotorObjects` 初始为
  `[]`。修复后默认装配为 RotorI/Z/0/1、RotorII/A/0/2、RotorIII/A/0/3。
- 确定性向量（补丁后，Git-for-Windows perl 5.42 实测）：
  `cipher('HELLO')='ZPEZR'`、往返 `cipher(cipher('HELLO'))='HELLO'`、
  `cipher('AAAAA')='UIZBM'`、`cipher('A B-1C')='UVW'`（非字母丢弃）。
- `setSteckerBoard([...])` / `setReflector(...)` 直接更新运行对象，
  cipher 立即生效；非法 reflector 名回退 `ReflectorB`。
  stecker `[A,B]` 时 `cipher('A')='E'`（补丁后实测）；含板往返成立。
- `getRotorNames/getStartLetters/getRingSettings` 在新鲜对象上返回空列表
  （补丁后不再崩溃；rotor 对象在 cipher/setRotor 成功后存在）；`setRotor`
  合法返回 1，非法 rotor number 返回 0。注意须按号升序安装，单个
  `setRotor(...,2)` 会在索引 0 留 undef 空洞，测试按 1,2 顺序安装。
- **测试禁区**：`ReflectorC` 接线不是对合（`N` 出现两次），往返会失败。
  测试只用 ReflectorB、全零 ring 与偶数 stecker，與上游 examples enigma1
  路径一致。

## 配方设计

- 照搬同仓已合入 `perl-net-ip/1.26-r7`（同为纯 Perl + MakeMaker）：
  `perl Makefile.PL` → `make -j1` → `make test` →
  `make install DESTDIR` → glob 拾取 `Crypt/Enigma.pm` 到
  `lib/perl5/`，`package_info` 置空 `cpp_info.libs` 并追加 `PERL5LIB`。
- 差异点（相对 perl-net-ip 的加强）：
  1. `generate()` 注入 `TMPDIR/TMP/TEMP=<build_folder>`（E002：鸿蒙 /tmp 只读）。
  2. `build()` 用 `stdout=True` 捕获 `make test TEST_VERBOSE=1`，
     用 `Tests=N` + `Result: PASS`/`All tests successful` 解析出真实计数，
     写入 `upstream_test_result.json`；无证据直接抛错，绝不假设通过。
  3. `package()` 把该 JSON 随包发布到 `res/`，供 test_package 原样重发
     `HMBS_UPSTREAM_TEST_RESULT`（balloon-1.1.1 前例）。
  4. `validate()` 做 R32 平台检查；`package_type = "application"`（纯 Perl 无编译产物，沿同仓纯 Perl 惯例；`library` 类型在 Conan 2 图计算时强制要求 `shared` 选项）。
- R26：无 `.so` 产物，不适用。R33：`self.run` 仅 `perl`/`make`，无裸 shell
  编译变量。R38：纯库、无 `bin/`，不需要 `commands.json`。
  R40：纯 Perl 密码学玩具，无图形/多媒体/外设/系统底层交点；唯一补丁为
  上游转子装配缺陷修复（bugfix，见上）。
- `patches/`：仅 `0001-fix-cipher-rotor-setup.patch`（真机 line 283 崩溃，
  本地 perl 5.42 复现并验证 18/18 通过）。

## 测试设计（test_package，R34 实质调用）

- `test_crypt_enigma.pl`（18 断言，TAP 输出 + `1..18` 计划 +
  `ENIGMA_TEST_RESULT passed=N total=N`）：
  - 模块加载与 `$VERSION='1.3'`（防包错版）。
  - 默认 `getReflector='ReflectorB'` + 三个 getter 为空（新鲜对象语义，
    杀死"返回 canned rotor 名"的桩）。
  - 精确向量 `HELLO→ZPEZR` / 往返 `cipher(cipher(HELLO))→HELLO` /
    `AAAAA→UIZBM` / `A B-1C→UVW` / 小写归一 / 空输入（杀死"恒等返回"的桩——
    恒等桩过不了精确向量；空文件比空文件式自欺在此无处藏身）。
  - stecker 配置生效（`A→E`）与含板往返；非法 reflector 回退；
    `setRotor` 按 1,2 顺序合法返回 1 且 rotor 可见、非法 number 返回 0。
- `test_enigma.py`（L0c 的 `.py` 测试源）：在包目录下步行定位
  `Crypt/Enigma.pm`（找不到即 FAIL，L1e 破坏性验证即依赖此），
  以 `PERL5LIB` 指向它执行 `.pl`，原样透传输出并传播退出码。
- `test_package/conanfile.py`：`self.run(perl test_enigma.py <pkg>)` 后解析
  真实计数发出 `HMBS_TEST_PACKAGE_RESULT`（discovered/passedCount 均来自
  输出），再重发包内 `res/upstream_test_result.json` 为
  `HMBS_UPSTREAM_TEST_RESULT`；计数不符或上游证据缺失即抛错。
- 上游测试接入：`build()` 内真实执行 `make test`（t/01.t，1 用例），
  不做 `no_tests` 替代。

## 当前状态

- 编译状态：配方与测试完稿，**尚未真机验证**（manifest 状态 `built` 诚实标记）。
- 待真机预检回填：`make test` 在 perl 5.42 下行为（含核心 `Test.pm`
  可用性）、`upstream_test_result.json` 实测计数、18 断言执行结果、
  PR 正文通过率。本轮不提交、不推送、不建 PR。

## 验证结果（预留，真机 evidence 轮填写）

- `conan create`（ohos-aarch64，`--build=missing` + `--build=enigma/*`）：待预检。
- 上游 `make test`：待预检（审计值：t/01.t 共 1 测试）。
- test_package 18 断言：待预检。
