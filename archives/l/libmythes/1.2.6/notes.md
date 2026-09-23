# libmythes 1.2.6 适配笔记

## 编译环境

- 构建系统: autotools（configure + make，libtool）
- 编译器: clang/clang++（OHOS SDK，conan profile 注入）
- 状态: built（配方首轮，待 HMBS 真机预检）
- 上游: https://github.com/hunspell/mythes ，tag v1.2.6

## 上游结构审计（测试判定依据）

- 源码根文件: mythes.cxx / mythes.hxx（库本体）、example.cxx（示例/检查程序）、
  th_gen_idx.pl（索引生成脚本）、th_en_US_new.idx/.dat（12MB 英语同义词库）、
  morph.idx/.dat/.lst/.aff/.dic（小规模形态学示例数据）、checkme.lst（待查词表）。
- 构建文件: configure.ac + Makefile.am。Makefile.am 定义
  `check_PROGRAMS = example`，但**无 TESTS 变量**，故 `make check` 只构建
  example 二进制，不运行任何自动化断言（automake 语义：无 TESTS 即零测试）。
- 全仓扫描（GitHub master + v1.2.6 tag）：
  `TEST(`/`TEST_F`（gtest）0 命中；`def test_`（pytest）0 命中；
  `enable_testing`/`add_test`（ctest）0 命中；`meson test` 无 meson.build；
  `tests/`/`test/` 目录不存在。唯一可执行验证是 example 手动调用：
  `example idx dat wordlist [aff dic]`。
- 结论：上游无自动化测试套件（test_package/MANIFEST.yml 记
  upstream_tests_exist: false + upstream_test_audit）。

## 编译步骤

1. `get()` 解压 `mythes-1.2.6.tar.xz`（strip_root）。
2. `generate()`：PkgConfigDeps + VirtualBuildEnv + AutotoolsToolchain；
   OHOS 下注入 SHELL/CONFIG_SHELL/CC/CXX/LD/AR/RANLIB/STRIP/NM 与
   --build/--host=aarch64-unknown-linux-gnu，configure 参数
   `--disable-werror --disable-dependency-tracking` + shared 开关。
3. `build()`：`configure` → `make -j1` → `make check -j1`
  （check 仅链接 example，验证 libmythes + hunspell 联合链接）。
4. `package()`：`make install` → COPYING 进 licenses/ →
   .so 别名链解引用为实文件 → 删 .la → .pc prefix 可重定位。

## 依赖版本

- hunspell/1.7.3（configure PKG_CHECK_MODULES 强制要求；example 需 hunspell.hxx）。
- 工具链：OHOS SDK clang 15 + libc++（profile 提供）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游要求 hunspell，但制品仓 hunspell/1.7.3 为 built 未 published | 依赖链断裂风险（R36/PF4） | 首轮仍声明 requires hunspell/1.7.3，由 HMBS 预检/PF4 实证；若缺失下轮改为可选 hunspell 补丁（库本体不依赖，仅 example 需要） |
| 2 | -Werror 在 clang 15 下误杀 legacy 告警 | 上游默认 enable_werror=yes | configure 加 --disable-werror（MSYS2 同款） |
| 3 | .so 符号链接在 HMDFS 上无法解析 | OHOS 动态链接器限制 | package() 内 rm + cp -a 解引用（hunspell 1.7.3 同款） |
| 4 | configure 临时目录 umask 077 + /bin/sh 缺失 | OHOS 沙箱限制 | build() 内 umask 077→022、shebang 重写为设备 shell（libXext 同款） |

## 验证结果

- 本地未跑 conan（按任务守则，验证交 HMBS 真机预检）。
- test_package：自研最小同义词库（test_thes.idx/.dat，单条 hello 记录），
  真实调用 MyThes::Lookup/CleanUpAfterLookup/get_th_encoding，
  覆盖命中/未命中/编码断言（6 断言，见 test_mythes.cpp）。
- 待 HMBS 回填：HMBS_TEST_PACKAGE_RESULT / HMBS_UPSTREAM_TEST_RESULT（no_tests）。

## 注意事项

- th_gen_idx.pl 为 dist_bin_SCRIPTS（perl 脚本），随包安装到 bin/，
  但包仍为 library 类型（主产物为 lib），故不建 commands.json（R38）。
- 大词库 th_en_US_new.dat（11MB）不进 test_package，自研最小数据避免臃肿。
- 若真机 config.guess 不认 HarmonyOS（uname -s），下轮按 hunspell/ezstream
  先例补 config.guess/config.sub 补丁并重验。
