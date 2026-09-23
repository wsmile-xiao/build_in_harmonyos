# libfbclient 5.0.4 适配笔记

## 目标与范围

- 软件：**libfbclient 5.0.4**（Firebird 5.0.4 的客户端库 `libfbclient.so.2`）
- 上游：https://github.com/FirebirdSQL/firebird ，tag `v5.0.4` → commit `f6d83a28c009ab039ea40ffdb4ccc58f190dfbe6`
- 版本头：`PRODUCT_VER_STRING "5.0.4.1812"`（`src/jrd/build_no.h`）
- 构建模式：**`--enable-client-only`**（= Y-Valve + remote client + common 组成客户端库本体；不含引擎/工具，与 Debian 二进制包 `libfbclient2` 对应）
- 产物：`libfbclient.so.5.0.4`（SONAME `libfbclient.so.2`）+ 客户端 WireCrypt 插件 `plugins/libChaCha.so` + 头文件 + `tzdata/`

## 编译环境

- 构建系统：autotools（上游 `configure` + `builds/posix` makefile 体系）
- 编译日期：2026-09-21
- 编译器：`/data/service/hnp/bin/clang` / `clang++`（OHOS SDK 15.0.4，target `aarch64-unknown-linux-ohos`）
- Conan：2.29.1（OHOS 适配版），remote `ohpcd`
- profile：`ci/conan/profiles/ohos-aarch64`（os=OHOS / os.version=6.0 / arch=armv8 / clang 15 / libc++ / cppstd 17）
- 状态：**published**（conan-verify 全绿）

## 编译步骤（真实命令）

```zsh
# 1) 源码：官方 release source tarball（自带生成好的 configure）
#    sha256=5041b97b480c9fe241c92ad0adf89e36faad0a8f0e21f1371dfbcc96a6f38e12
get  → Firebird-5.0.4.1812-0-source/

# 2) 依赖（全部来自 ohpcd 制品仓，W0 已验证可消费）
conan install --requires=icu4c/78 --requires=zlib/1.3.2 \
              --requires=libtommath/1.3.0 --requires=libtomcrypt/1.18.2 -r=ohpcd

# 3) 打补丁（3 个，见 patches/）
apply_conandata_patches

# 4) configure（in-source：Firebird 的构建体系把 gen/、temp/ 写在源码树内）
./configure --enable-client-only --without-editline --disable-rpath

# 5) 构建 + 上游测试
make -j4
make -f Makefile TARGET=Release gen/Release/firebird/tests/common_test   # 在 gen/ 下执行
gen/Release/firebird/tests/common_test --log_level=test_suite --report_level=detailed

# 6) 打包（不使用上游 make install，见下）
#    package() 复制安装镜像 gen/Release/firebird/{lib,include,plugins,tzdata,plugins.conf}
```

## 遇到的问题与解决方案

| # | 问题（首个错误） | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `config.guess: unable to guess system type`（rc=1） | OHOS `uname -s` 返回 `HarmonyOS`，stock config.guess 无该分支（E007） | 补丁 0001：config.guess 增加 `*:HarmonyOS:*:*` → `aarch64-unknown-linux-ohos`；不做 `--build/--host` 伪造，保持 `cross_compiling=no` |
| 2 | `config.sub: Invalid configuration 'aarch64-unknown-linux-ohos': Kernel 'linux' not known to work with OS 'ohos'` | config.sub 的 OS 列表与 kernel-OS 校验表缺 ohos/linux-ohos | 补丁 0002：补 `ohos*` 到 OS 列表、`linux-ohos*` 到 kernel-OS 校验表、`ohos-linux` 映射分支 |
| 3 | `./config.status: line 1005: ./confKJginB/subs1.awk: Permission denied`（`config.status: error: could not setup config files machinery`） | config.status 用 `umask 077` 建临时目录 → HMDFS 下目录为 `drwx--S---`(2700)，连属主都无法写入（E114） | 补丁 0003：生成的 `configure` 中两处 `umask 077` → `umask 000`（与 acl/abiword/air-quality-sensor 先例一致） |
| 4 | `configure: error: termcap support not found` | aarch64 平台分支默认 `EDITLINE_FLG=Y`，强制探测 termcap（isql 行编辑用），而 client-only 不含 isql，镜像亦无 ncurses/termcap | 使用上游文档化开关 `--without-editline`（不改源码） |
| 5 | `ld.lld: error: unable to find library -ltomcrypt / -lgmp / -ltommath / -licuuc ...`（链接 `extern/cloop` 时） | `extern/cloop/Makefile` 链接只用 `$(LIBS)`，不传 `$(LDFLAGS)`，依赖系统库默认搜索路径 | `generate()` 中把 conan 依赖的 `lib/` 目录导出为 `LIBRARY_PATH`（clang 链接期搜索路径），不改上游 makefile |
| 6 | `make install` → `./install.sh: inaccessible or not found`（Error 127） | 上游缺陷：`builds/install/arch-specific/linux/Makefile.in` 里 `install.sh` 只在 `CLIENT_ONLY_FLG=N` 时拷入打包目录，`install:` 目标却无条件执行；且该目标还有 `cp -r $(DebugDir)/* /`（向文件系统根写调试符号） | **不使用 `make install`**：`package()` 复制上游安装镜像 `gen/Release/firebird`（与真实 Debian recipe `override_dh_auto_install: true` + `cp -a ./gen/Release/firebird debian/firebird-image` 同口径） |
| 7 | `ThreadStart.cpp:213: error: use of undeclared identifier 'pthread_cancel'`（在手工把 `src/include/gen/autoconfig.auto` 还原为 tarball 内容后出现） | release tarball 预置的 `autoconfig.auto` 是 **glibc 宿主**上生成的（`HAVE_PTHREAD_CANCEL`/`HAVE_DLINFO` 为 defined），OHOS musl 无这些接口；该文件必须由 configure 在本机重新生成 | 不还原该文件；将其 tracker 基线更新为 configure 生成态，避免误纳入补丁（该文件是 configure 产物，不是人工修改） |
| 8 | `make tests` 在 ENGINE_TEST 阶段失败：`gen/Release/firebird/bin/gpre_current: No such file or directory`（Error 127，make.rules:102） | `--enable-client-only` 不构建 gpre_full/引擎，engine 测试的 `.epp` 无法预处理 | 只构建并执行客户端侧 `common_test`（13 用例）；engine_test 在 client-only 下结构性不可用（见下"上游测试"） |

## 上游测试（R51 三步法）

### 1) 清点（真实命令）

```zsh
for f in src/common/tests/*.cpp src/common/classes/tests/*.cpp src/jrd/tests/*.cpp; do
  printf '%-52s %s\n' "$f" "$(grep -c 'BOOST_AUTO_TEST_CASE' $f)"; done
# → common/classes/tests/AlignerTest.cpp            3
#    common/classes/tests/ArrayTest.cpp              5
#    common/classes/tests/ClumpletTest.cpp           2
#    common/classes/tests/DoublyLinkedListTest.cpp   3   （客户端侧合计 13）
#    jrd/tests/CompressorTest.cpp                    1
#    jrd/tests/RecordNumberTest.cpp                  1   （引擎侧合计 2）
#    jrd/tests/EngineTest.cpp                        0   （BOOST_TEST_MODULE 主模块）
make -C gen -f Makefile tests     # 目标 = common_test + engine_test
```

| 测试二进制 | 源文件 | 用例数 | client-only 可用性 |
|---|---|---|---|
| `common_test`（COMMON_TEST） | `src/common/tests/CommonTest.cpp`（BOOST_TEST_MODULE）+ `src/common/classes/tests/{Aligner,Array,Clumplet,DoublyLinkedList}Test.cpp` | **13** | ✅ 可构建可运行 |
| `engine_test`（ENGINE_TEST） | `src/jrd/tests/EngineTest.cpp`（BOOST_TEST_MODULE 主模块，0 用例）+ `{Compressor,RecordNumber}Test.cpp` | **2**（Compressor `PackAndUnpackTest` + RecordNumber `IsValildTest`） | ❌ 需引擎 + gpre_full（不在 client-only 配置内） |

### 2) 实际运行（真实命令与结果）

```zsh
make -f Makefile TARGET=Release gen/Release/firebird/tests/common_test   # 在 gen/ 下
gen/Release/firebird/tests/common_test --log_level=test_suite --report_level=detailed
# Test module "CommonTest" has passed with: 13 test cases out of 13 passed / 61 assertions out of 61 passed
# rc=0   （conan create 内执行结果一致，见 reports/conan-create.log）
```

13 个用例全部通过、0 失败、0 跳过（用例名单见 `reports/test-report.md`）。

### 3) 如实申报

- 上游客户端侧测试：**13/13 通过**（61/61 断言）。
- 上游引擎侧测试：**结构性不可构建**（2 用例：Compressor `PackAndUnpackTest` + RecordNumber `IsValildTest`），原因与实测错误见上表第 8 条；本包不构建引擎，故不属于本包可执行范围。
- 上游样例（`examples/api/makefile`，上游自带构建入口）：**17 个可执行样例 + 1 个 UDF 共享库全部编译链接成功**；17 个样例实际运行均返回 1 并打印 `Unable to complete network request to host "localhost"`（客户端库完整初始化 + 远程 provider 生效后因无服务端而终止，属预期）。`api14` 需 `gpre`、`api9f` 的最后一步需 `isql` 向数据库声明 UDF，二者不在 client-only 范围。
- `make examples` / `examples/build_unix` 需要 `isql` 与引擎（`gen/examples/isql: No such file or directory`，Error 127），client-only 下不可用。

## 源码修改（补丁）

| 补丁 | 目标文件 | 内容 | 类型 |
|---|---|---|---|
| 0001-builds-make.new-config-config.guess.patch | `builds/make.new/config/config.guess` | 增加 `*:HarmonyOS:*:*` 识别分支，输出 `aarch64-unknown-linux-ohos` | portability |
| 0002-builds-make.new-config-config.sub.patch | `builds/make.new/config/config.sub` | 接受 `ohos` OS、`linux-ohos` kernel-OS 组合与 `ohos-linux` 映射 | portability |
| 0003-configure.patch | `configure`（autoconf 生成物） | 两处 `umask 077` → `umask 000`（HMDFS 下 2700 目录不可写） | portability |

补丁中**不包含任何平台宏**（无 `__OHOS__` 注入），全部为三元组/umask 类可移植性修复。

## 依赖版本

| 依赖 | 版本 | 说明 |
|---|---|---|
| icu4c | 78 | `unicode/ucnv.h` + `-licuuc`，configure 硬检查；POSIX 无内嵌开关 |
| zlib | 1.3.2 | 构建期 `zlib.h`；运行期 `dlopen("libz.so.1")`（线缆压缩） |
| libtommath | 1.3.0 | `-ltommath`（BigInteger / SRP） |
| libtomcrypt | 1.18.2 | `-ltomcrypt`（TomCryptHash / WireCrypt），传递 gmp/6.3.0 |

四者均从 ohpcd 制品仓 recipe + 二进制可下载（`conan download ... -r=ohpcd` 全部 exit 0）。
实际链接结果：四个依赖**静态链入** `libfbclient.so`，产物 `DT_NEEDED` 仅 `libc.so`（自包含，无运行时依赖解析问题）。

## 验证结果

```zsh
# 配方验证（8 道门禁）
python3 $SKILL_ROOT/scripts/ohc-run.py conan-verify libfbclient 5.0.4
# → G0 PASS / G1 PASS / G2 PASS(conan create 成功) / G3 PASS / G4 PASS / L2 PASS / L4 PASS / L5 PASS
# → ✅ 配方验证通过: libfbclient 5.0.4

# 上游测试（conan create 内自动执行）
# → Test module "CommonTest" has passed with: 13 test cases out of 13 passed / 61 assertions out of 61 passed

# test_package（conan create 内自动执行）
# → 1/1 Test #1: test_libfbclient .................   Passed    0.60 sec
#   含 3 个鸿蒙特有断言：OHOS-1 工具链/架构、OHOS-2 打包产物 ELF 校验、OHOS-3 OHOS 上 ICU 时区编解码

# 产物确认
readelf -d gen/Release/firebird/lib/libfbclient.so.5.0.4 | grep -E 'NEEDED|SONAME'
# → NEEDED libc.so ; SONAME libfbclient.so.2
```

## 注意事项

- 本包为**纯库包**（无 `bin/` 可执行文件），故软件级目录无 `commands.json`（R38 不适用）。
- 构建必须 in-source（`self.folders.build = "."`）：Firebird 的 makefile 体系把 `gen/`、`temp/` 写在源码树内，且 `configure` 以 `./src/misc/writeBuildNum.sh` 相对路径调用脚本，out-of-tree 会在 configure 阶段失败。
- `TARGET=Release` 与上游 `TARGET?=$(DefaultTarget)` 等价（未启用 `--enable-developer`）。
- tzdata 随包安装（`tzdata/*.res`）：ICU 时区功能（`decodeTimeStampTz` 等）需要 `$(root)/tzdata`。
---

**编译结束**: 2026-09-21 03:32
**最终状态**: published
