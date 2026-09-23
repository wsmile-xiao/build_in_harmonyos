# xapian-core 2.0.0 适配笔记

## 编译环境

- 构建系统: autotools
- 编译日期: 2026-09-05
- 编译器: clang/clang++ 15.0.4（OHOS SDK，`/data/service/hnp/bin`）
- 目标三元组: `aarch64-unknown-linux-ohos`
- Conan profile: `ci/conan/profiles/ohos-aarch64`（os=OHOS, arch=armv8, cppstd=17）
- 状态: built（本地验证，未上传制品仓）

## W0 依赖核验

`configure.ac` 中与第三方库相关的检查只有两处硬依赖：

| 检查 | 位置 | 结论 |
|------|------|------|
| `zlib.h` / `zlibVersion()` | configure.ac:864-871，缺失即 `AC_MSG_ERROR` | 唯一第三方硬依赖 → `zlib/1.3.1.1` |
| `uuid/uuid.h` / `uuid.h` / `/proc/sys/kernel/random/uuid` | configure.ac:940-965 | OHOS sysroot 无 `uuid/uuid.h`、`uuid.h`，configure 选择 `USE_PROC_FOR_UUID`，**不需要 util-linux/libuuid** |

制品仓实测（R35 口径，`conan download --only-recipe`，不用 `conan list`）：

```text
conan download zlib/1.3.1.1 -r=ohpcd --only-recipe
  -> zlib/1.3.1.1#9a23e7d51311d0440b6e4d36cf44e4d9 (2026-07-14)   # 已发布
ci/scripts/preflight_check.sh xapian-core/2.0.0
  -> [OK] 已发布: zlib/1.3.1.1 ；[OK] 版本号未被占用: xapian-core/2.0.0
```

`-lrt` / `-lpthread` / `-lsocket` 一类只是 `AC_SEARCH_LIBS` 的探测，OHOS musl 无需额外库，不构成 conan 依赖。结论：**无未发布依赖，可以继续适配。**

## 源码与 SHA256 核验

- 官方源：`https://oligarchy.co.uk/xapian/2.0.0/xapian-core-2.0.0.tar.xz`（R39 官方源，`.asc` 同目录发布）
- 本机计算：

```text
sha256  6cea3f49952a47224439a40bdb3608f928d121ad8721b9921cc42802d548ecf8
sha512  b9205997ca05748b3dae1b669f428bc04c6a5bda41dcae1443869741e1bd6c24
        5e0e433c8c4afef021299a699fc4e4ed6ae82aae8541db613aa570a003afea43
blake2b 2032ae047312bdc03b1002cbc2a4f01a2e5d37c0859fd5a6013758d456d7642c
        07ca0d28141daf0eeb2ba33db41206df088ba2666efcd83d545d123d51e8cb6c
```

- 交叉核验（两个独立渠道 + 三次独立下载）：
  1. 同一官方 URL 两次独立下载 `cmp` 完全一致，且与 `init-build` 缓存的
     `/storage/Users/currentUser/tmp/builds/xapian-core-2.0.0.tar.xz` 字节一致；
  2. Arch Linux 打包仓库 `xapian-core` 提交 `74e7166236d1`（`upgpkg: 1:2.0.0-1`）
     公布的 `sha512sums` / `b2sums` 与本机计算值逐字符相同，该 commit 同时确认
     `pkgver=2.0.0` 是上游正式版本（`NEWS`：Xapian-core 2.0.0 2026-03-16）；
  3. 官方 `.asc` 的签发者指纹 `08E2400FF7FE8FEDE3ACB52818147B073BAD2B07`
     与 Arch `validpgpkeys` 中 Olly Betts `<olly@debian.org>` 一致。
     本机无 gpg/gpgv，因此签名只做了**指纹比对**而未做密码学验签，
     密码学强度由第 2 条的独立摘要承担。

版本自证：`configure.ac` 中 `AC_INIT([xapian-core], [2.0.0])`，生成的
`include/xapian/version.h` 中 `XAPIAN_VERSION "2.0.0"`、`XAPIAN_MAJOR_VERSION 2`。

## 编译步骤

```bash
source .build-context-xapian-core-2.0.0
cd $BUILD_SRC_DIR                       # /storage/Users/currentUser/tmp/builds/xapian-core-2.0.0.work

perl $SKILL_ROOT/scripts/patch-autotools-ohos.pl config.guess config.sub   # E007
# configure: umask 077 -> 022（E129）；version.h 的 sed 地址 0,/re/ -> 1,/re/
bash ./configure --prefix=$DEFAULT_PREFIX
make -j16
make install DESTDIR=$TEST_PREFIX       # staging 隔离，未写入 /usr/local
make check -j1
```

日志目录：`/storage/Users/currentUser/tmp/logs/xapian-core-2.0.0/`
（`01-configure.log` → `13-make-check-final.log`，每个文件末尾记录 `EXITCODE=`）。

最终 configure 关键判定（`04-configure.log`）：

```text
checking for zlib.h... yes
checking for library containing zlibVersion... -lz
checking for uuid/uuid.h... no
checking for uuid.h... no
checking if host platform supports /proc/sys/kernel/random/uuid... yes
checking whether clang++ supports C++20 features with -std=gnu++20... yes
```

后端：`XAPIAN_HAS_GLASS_BACKEND` / `XAPIAN_HAS_HONEY_BACKEND` /
`XAPIAN_HAS_INMEMORY_BACKEND` / `XAPIAN_HAS_REMOTE_BACKEND`。
**2.0.0 已移除 chert 后端**（1.4.x 有），配方与测试都按 glass/honey 编写。

安装产物（staging）：`lib/libxapian.so.45.0.0`（+ soname 链接）+ `bin/` 下 15 个可执行文件
（xapian-check、xapian-delve、xapian-compact、xapian-quest、xapian-pos、
xapian-metadata、xapian-replicate、xapian-replicate-server、xapian-progsrv、xapian-tcpsrv、
copydatabase、simpleindex、simplesearch、simpleexpand、xapian-config）
+ `include/xapian/*` + `lib/pkgconfig/xapian-core.pc` + `lib/cmake/xapian/`
+ `share/{man,doc,aclocal,xapian-core}`。
因为随库发布 CLI（15 个里按 1.4.x 同口径登记常用的 3 个：check/delve/compact），
`cpp_info.bindirs = ["bin"]`，并按 R38 在软件级
`archives/x/xapian-core/commands.json` 增补 `2.0.0` 条目；
`binary` 取 `false`（`ARCHIVE-SPEC §2.1`：适配中 `false`，发布到制品仓后才改 `true`，
本包 status=built 未上传）。

## 遇到的问题与解决方案

| # | 问题（首个真实错误） | 根因 | 最小修改 |
|---|----------------------|------|----------|
| 1 | `configure: error: cannot guess build type; you must specify one`（`01-configure.log`，`uname -s = HarmonyOS`，`config.guess timestamp = 2025-07-10`） | 上游随包发布的 GNU `config.guess`/`config.sub` 没有 HarmonyOS 分支，`uname -s` 无法映射（知识条目 E007） | `config.guess` 增加 `*:HarmonyOS:*:*` 分支输出 `aarch64-unknown-linux-ohos`、`config.sub` 接受 `linux-ohos`；禁用 `--build/--host` 绕过（E007 明令禁止，会导致 cross_compiling 误判）。**未采用 E007 脚本自带的 `__OHOS__` libc 探针**，理由见下方“补丁精简说明” |
| 2 | `./config.status[1105]: can't create ./confADLIMm/subs1.awk: Permission denied` → `config.status: error: could not setup config files machinery`（`03-configure.log`） | HMDFS 对新目录强制 setgid，Autoconf 用 `umask 077` 建的临时目录变成 `drwx--S---`，连属主都不能写（知识条目 E129） | 把 `configure` 建临时目录的 `umask 077` 改为 `umask 022`（2 处）。复现证据：`cd ~/tmp && (umask 077 && mktemp -d)` → `drwx--S---` 且写入 Permission denied；`umask 022` → `drwxr-s--x` 写入成功 |
| 3 | `./include/xapian/types.h:108:9: error: unknown type name 'XAPIAN_REVISION_TYPE'`（`05-make.log`：148 条 `error:` 行，其中 48 条是 `types.h` 缺宏，多个 TU 各报 "20 errors generated"） | `include/xapian/version.h` 是 **0 字节**。configure 用 `${SED-sed} '0,/const char \* dummy/d;…'` 生成该头文件，`0,/re/` 是 GNU sed 专用地址；本机 `/usr/bin/sed` 是 **toybox 0.8.12**，它不报错但把每一行都删掉，于是输出为空，而管道退出码仍是 0，configure 静默通过 | 把该 sed 脚本地址 `0,/const char \* dummy/d` 改为 POSIX 形式 `1,/const char \* dummy/d`（1 处）。实测：toybox sed 处理预处理结果，`0,` 形式输出 0 字节，`1,` 形式输出 3909 字节且 `XAPIAN_*` 宏齐全。这是纯可移植性修复，GNU sed 下行为等价 |
| 4 | `make check` 中 glass 后端 `lockfileumask1... FAILED`（`10-make-check.log`） | 测试硬编码期望锁文件权限 `0644`，而 HMDFS 会屏蔽 others-read 位，实际为 `0640` | 改测试：同目录先创建一个 `0666` 探针文件，用探针的实际权限作为期望值再比对锁文件（运行时探测，不引入平台宏） |
| 5 | （历史坑 1.4.26 #8 预防性沿用，本轮未产生原始失败日志）真机上所有需要新建数据库的用例会报 `Opening UUID generator failed (Permission denied)` | configure 选中 `USE_PROC_FOR_UUID`，但真机禁止普通用户读 `/proc/sys/kernel/random/uuid`；`/dev/urandom` 可读 | `backends/uuids.cc`：`/proc` 打不开时回退到 `/dev/urandom` 读 16 字节并按 RFC 4122 置 version/variant 位。运行时探测，无平台宏。本轮**在跑测试前**就打了该补丁，因此没有失败轮次存档；触发前提已独立复现（`cat /proc/sys/kernel/random/uuid` → `Permission denied`，`head -c 16 /dev/urandom` → 成功），并且 `unittest` 的 `uuid1`、`apitest` 全部建库用例、`test_package` 的 glass/honey 建库在真机通过 = 回退生效的正向证据 |

补充：1.4.26 记录的“`tests/runtest` 硬编码 `/bin/sh` 导致 bad interpreter”在本机型**不复现**
（`/bin/sh` 存在且可执行，`make check` 全程未出现该错误），因此没有沿用 shebang→`@SHELL@` 那半个补丁。

## 源码修改（补丁清单，`refresh-patch --auto` 生成）

| 补丁 | 类型 | 内容 |
|------|------|------|
| `patches/0001-backends-uuids.cc.patch` | portability | `/proc` UUID 不可读时回退 `/dev/urandom`（+18/-2） |
| `patches/0002-config.guess.patch` | platform | HarmonyOS 识别，输出 `aarch64-unknown-linux-ohos`（+11/-0，零平台宏） |
| `patches/0003-config.sub.patch` | platform | 在 `config.sub` 的 OS 归一化分支里新增 `ohos-linux)` → `basic_os=linux-ohos`（+4/-0）；conandata 的 `patch_description` 用概括说法“Accept linux-ohos target triplets”，实际实现是接受逆序写法 `ohos-linux` 并归一化为 `linux-ohos`，语义一致 |
| `patches/0004-configure.patch` | portability | toybox sed 地址兼容 + HMDFS 临时目录 umask（+3/-3） |
| `patches/0005-tests-api_backend.cc.patch` | test | `lockfileumask1` 改为运行时探测实际权限（+13/-1） |

### 补丁精简说明（PF5 / R8：本包补丁零平台宏）

`patch-autotools-ohos.pl`（E007 方案脚本）默认还会在 `config.guess` 的
`Linux|GNU|GNU/*` 分支里插入一段 libc 探针：

```sh
#elif defined(__OHOS__)
    LIBC=ohos
```

本包**主动去掉**了这一段，只保留 `*:HarmonyOS:*:*` 识别分支，理由是实测：

1. 只加 case 分支，`bash config.guess` 在本机型直接输出
   `aarch64-unknown-linux-ohos`（退出码 0）——见
   `/storage/Users/currentUser/tmp/cg-test/onlycase.guess` 的对照实验；
   本机型 `uname -s` 是 `HarmonyOS`，根本不会进入 `Linux|GNU` 分支，探针是死代码。
2. 该探针要求 `set_cc_for_build` 在临时目录里编译 `dummy.c`，
   而 HMDFS + `umask 077` 下这一步在本机型直接报
   `dummy.c: Permission denied`（对照实验中可见），即探针路径在本平台不可用；
3. 去掉后补丁新增行不再包含任何平台宏，**PF5/R8 无需申请例外**，
   修改面也更小（+11 行 → 原 +13 行）。

因此与归档 `1.4.26` 的做法（保留 libc 探针并靠 R8 例外说明）相比，
本版本走“零平台宏”路线；5 个补丁的新增行 `grep '^+.*__OHOS__'` 全部为空。
问题 #4/#5 同样采用运行时探测而非条件编译，未引入 `__OHOS__`。

## 与 1.4.26 历史方案的差异（W0b 偏离说明）

| 项 | 1.4.26 做法 | 2.0.0 做法 | 偏离原因与证据 |
|----|-------------|------------|----------------|
| 空 `version.h` | 配方里 `_fix_empty_version_header()` 手写整份头文件兜底 | 直接修 `configure` 的 sed 地址（补丁 0004），让上游逻辑自己生成 | 手写头文件会硬编码版本号与后端宏，2.0.0 后端集合已变（chert 移除、honey 新增），照搬会漏 `XAPIAN_HAS_HONEY_BACKEND`。改 sed 地址后 `configure` 自己产出 3909 字节的真实头文件，实测 `XAPIAN_HAS_HONEY_BACKEND` 等宏齐全 |
| `umask 077` | 配方内 OHOS 分支 `replace_in_file` | 并入补丁 0004 | 与 sed 修复同在 `configure` 一个文件，统一由 `apply_conandata_patches` 落地，避免补丁与 replace 两处改同一文件互相打断 |
| runtest shebang→`@SHELL@` | 补丁 0004 的一部分 | 未采用 | 本机型 `/bin/sh -c ok` 成功，`make check` 无 bad interpreter；按“最小修改”不带无关变更 |
| configure 工具链显式命名 | OHOS 分支设置 `CC/CXX=bash+wrapper`、`AR=llvm-ar`、`LD=ld.lld` | 保留 OHOS 分支（配方 `build()`） | 本机直接 `bash ./configure` 能自动找到 `ar`/`ld`，但 CI worker 的 PATH 与包装脚本形态按历史结论更稳，故沿用历史做法 |
| config.guess libc 探针 | 补丁含 `#elif defined(__OHOS__)`（靠 R8 例外说明过关 PF5） | **删除该探针**，只留 `*:HarmonyOS:*:*` 分支 | 见“补丁精简说明”：对照实验证明只保留 case 分支即可产出 `aarch64-unknown-linux-ohos`，且探针在本机型因 HMDFS 临时目录权限根本跑不通；删除后补丁零平台宏 |
| 2.0.0 后端集合 | 手写兜底头文件里写死 `XAPIAN_HAS_CHERT_BACKEND` | 不再兜底，由 configure 自己生成 | 2.0.0 移除 chert、新增 honey，兜底头文件会失真；`test_package` 相应改为“写 glass → 压实成 honey → 只读检索” |

## 上游测试

测试申报（R51 三步法第 1 步）：`make -n check` 注册的 4 个测试程序 + `tests/` 源文件；
执行命令 `make check -j1`（与 1.4.26 历史口径一致）。

### 上游测试申报（R51）

`make -n check` 注册的测试程序共 4 个（`tests/Makefile` check-TESTS）：
`apitest`、`internaltest`、`stemtest`、`unittest`（另有 `perftest`、`soaktest`
只在 `make perfcheck`/`make soakcheck` 下运行，不属于 `make check`）。
本机型实际执行 `make check -j1`（2026-09-05，日志
`/storage/Users/currentUser/tmp/logs/xapian-core-2.0.0/13-make-check-final.log`）。

### 实跑统计（修复补丁后、`make -j1` 单次完整运行）

| 测试程序 | 结果 | 用例数 | 通过 | 失败 | 跳过 | 预期失败 |
|----------|------|--------|------|------|------|----------|
| `apitest` | FAIL（仅 1 项计时用例） | 3482 | 3446 | 1 | 34 | 1 |
| `internaltest` | PASS | 7 | 7 | 0 | 0 | 0 |
| `stemtest` | PASS | 105 | 70 | 0 | 35 | 0 |
| `unittest` | PASS | 23 | 22 | 0 | 1 | 0 |
| **合计** | 3/4 程序全绿 | **3617** | **3545** | **1** | **70** | **1** |

`make check` 退出码 2，唯一失败项是计时用例 `qp_scale1`（见“已知问题”），
其余全部通过；`apitest` 按后端展开的 10 组逐项结果：

| # | apitest 后端 | 通过 | 失败 | 跳过 | 预期失败 |
|---|--------------|------|------|------|----------|
| 1 | `honey` | 344 | 0 | 0 | 0 |
| 2 | `none` | 151 | 0 | 0 | 0 |
| 3 | `inmemory` | 353 | 0 | 8 | 0 |
| 4 | `glass` | 444 | 0 | 3 | 0 |
| 5 | `singlefile_glass` | 344 | 0 | 0 | 0 |
| 6 | `multi_glass` | 401 | 0 | 5 | 1 |
| 7 | `multi_glass_remoteprog_glass` | 345 | 0 | 6 | 0 |
| 8 | `multi_remoteprog_glass` | 344 | 1 | 6 | 0 |
| 9 | `remoteprog_glass` | 356 | 0 | 3 | 0 |
| 10 | `remotetcp_glass` | 364 | 0 | 3 | 0 |

`internaltest` 逐项（7 项，全部通过）：
`exception1`、`refcnt1`、`refcnt2`、`stringcomp1`、`temporarydtor1`、
`pack_uint_preserving_sort1`、`chartype1`。

`unittest` 逐项（22 通过 + 1 跳过）：
`simple_exceptions_work1`、`class_exceptions_work1`、`resolverelativepath1`、
`serialisedouble1`、`packuint1`、`packstring1`、`packstring2`、`serialiseerror1`、
`sortableserialise1`、`tostring1`、`strbool1`、`closefrom1`、`shard1`、`uuid1`、
`movesupport1`、`addoverflows1`、`suboverflows1`、`muloverflows1`、`parseunsigned1`、
`parsesigned1`、`vec1`、`vecdeleter1` 通过；`ioblock1` 跳过。
其中 `uuid1` 通过即验证了问题 #5 的 `/dev/urandom` 回退生效。

`stemtest` 逐项（35 个词干器 × 3 项 = 105）：每个词干器执行
`stemrandom`、`stemjunk`、`stemdict`；前者 70 项全部通过，
`stemdict` 35 项**全部 SKIPPED**（上游 release 包不含 stemdict 语料样本，
与平台无关，`make check` 在源码树里才会跑该子集）。

### 与 1.4.26 历史测试对比

| 项 | 1.4.26（真机 old port r11） | 2.0.0（本次） |
|----|------------------------------|---------------|
| apitest | 4245 passed，13 expected failures，50 skipped | 3446 passed，1 expected failure，34 skipped，1 failed(计时) |
| internaltest/stemtest/unittest | 全部 PASS | 全部 PASS |
| 用例总数变化原因 | chert 后端在 2.0.0 移除、新增 honey，后端组合与用例集合不同 | — |

## 已知问题（未修改，如实上报）

- **`qp_scale1` 计时用例偶发失败（不影响功能，未打补丁）**。
  该用例断言 `time(large query) < time(small query) * 2.15`
  （`tests/api_queryparser.cc:2954`，`CPUTimer` 取 CPU 时间），
  在本机型 multi_* 远程合成后端上实测比值长期在阈值附近抖动：

  ```text
  完整 make check（13-make-check-final.log）: 10 组后端中 1 组失败
  单后端复跑 8 轮（留档 reports/qp_scale1-reruns.log，21:12 五轮 + 21:42 追加三轮）
  命令 ./apitest -b multi_remoteprog_glass qp_scale1   （-b 才是后端参数）:
    attempt 1,2,6,8 -> ok
    attempt 3 -> FAILED 子例2 small=0.397942 large=0.883609 ratio 2.220
    attempt 4 -> FAILED 子例2 small=0.394329 large=0.883229 ratio 2.240
    attempt 5 -> FAILED 子例2 small=0.402693 large=0.882799 ratio 2.192
    attempt 7 -> FAILED 子例2 small=0.333881 large=0.886327 ratio 2.655
  => 有档单后端 8 轮 = 4 通过 / 4 失败。
  失败集中在第 2 个子例（api_queryparser.cc:2985 那次 helper：开启 synonym flag
  但查询词 "baz" 自身不是 synonym）；第 1 个子例（:2981，不开 flag）比值恒 <1。
  全部可复算的触发比值共 8 个：留档单后端 2.192 / 2.220 / 2.240 / 2.655，
  完整 make check 轮：10-make-check.log 的 :2659=2.353、:3016=2.732、:3751=2.359，
  13-make-check-final.log 的 :2808=2.527（该值属第 3 子例 :2988），
  即 **2.192-2.732**；审计方独立复跑另见 2.173 / 2.182 / 2.188 / 2.216 / 2.244，
  故散布下界至少到 2.17。门限 2.15 正落在该带下沿 -> 边界抖动，非确定性缺陷。
  ```

  判定：这是上游的性能回归门限（threshold 2.15），不是 OHOS 功能缺陷；
  同一二进制同一次运行内其他 9 组后端均 PASS，说明查询解析结果正确性无误。
  因此**不修改该用例**（改门限等于掩盖上游性能信号），在此如实记录，
  建议按上游 flaky timing test 处理（可在 CI 中重跑或忽略该单项）。

## 本地门禁执行说明（W3 / G0 / PF9）

### W3 本地 CI 模拟（`finish` step [5/10]，阻塞门禁）— PASS

`archives/x/xapian-core/2.0.0/reports/w3-local-ci.log`，
`.ci-result.json`：`exit_code=0`、`integrity_hash=0f2d4b220989652e`、
`log_sha256=4e9ca467feea39b8…f691d8`
（== `sha256sum reports/w3-local-ci.log` 实测；`integrity_hash` 按
`scripts/ohc/finish.py:249-252` 的
`sha256(f"{timestamp}:{software}:{version}:{exit_code}")[:16]` 复算一致；
工具写入，未手改）。

| 门禁 | 结果 | 备注 |
|------|------|------|
| JC 杂项文件 | pass | 必须按 CI 口径限定变更范围：`JUNK_PR_DIFF=<本包 pr.diff>`。直接整仓扫描（本地停在 main/无 commit 时的回退模式）会命中一个与本包无关的存量文件 `archives/u/util-linux-login/2.42.2/.ci-trigger`（已被 main 跟踪），属仓库存量问题，不在本包修改范围（W2 原子性禁止捎带） |
| L0 | pass: all checks passed | |
| L1 | pass | 实际内容 = `conan create` + `test_package` 10 项断言；**不含上游 `make check`**（上游测试是探索阶段单独实跑，见 §上游测试） |
| L2 | pass（带明细） | `xapian-config --version OK`，其余 14 个 CLI 的 version/help 探测失败。根因：可执行文件**写了 RUNPATH，但值是 `//lib`**（`llvm-readelf -d` 实测 `(RUNPATH) [//lib]`——打包时 `--prefix=/`，libdir 展开成 `${prefix}/lib`），脱离 `LD_LIBRARY_PATH` 或 conan runenv 指向包内 `lib/` 时加载不到 `libxapian.so.45`；消费者按 conan 的 `runenv_info`/`VirtualRunEnv` 使用即正常。与 1.4.26 历史结论“generic version/help checks are not applicable to these CLI tools”同源，非构建缺陷 |
| L4 | warn | “dangerous functions in patches”经复核是**误报**：扫描正则 `(strcpy\|sprintf\|gets\|strcat)\b` 缺前导 `\b`，命中的其实是 `0002-config.guess.patch` **上下文行**（非 `+`/`-` 行）里 `# NetBSD ... targets ... match one or` 中的 `gets`（`tar|gets|` 子串）。对 5 个补丁做整词检索 `grep -nEw 'strcpy\|sprintf\|gets\|strcat'` = 0 命中，本包补丁未引入任何危险函数。该扫描还会递归进 gitignore 的 `patches/.patch-backup-*/`。warn 级不阻断，归因已在本轮更正 |
| L5 | pass | `bin/` 有内容 |

### G0 干净构建验证（`finish` step [3/10]，非阻塞）— FAIL（环境工件）

```text
shell-init: error retrieving current directory: getcwd: cannot access parent directories: Not supported
configure: error: working directory cannot be determined
```

`clean-verify` 在临时目录里以不可解析的 cwd 直接起 `configure`（日志
`/storage/Users/currentUser/tmp/ohc-verify-xapian-core-*/g0-configure.log`），
5 个补丁本身“全部应用成功”。同一份补丁源码在 `conan create`（G2）与 W3 真机模拟里都构建通过，
因此判定为验证脚手架/平台 getcwd 行为工件，不是配方缺陷；
修法在框架侧（`clean-verify` 显式 `cd` 到实体目录并用 `CONFIG_SHELL` 起 configure），
不在本包范围。已登记为 SKILL 反馈项（v12.17 backlog 已列“autotools configure 重执行 getcwd 失败”）。

### PF9 与 R38/PF8 的规则冲突（已定位根因，修框架判据，归档布局未动）

本地复跑 `scripts/ohc/preflight.py` 曾报：
`PF9 分支/路径闸: 变更路径缺版本目录层 … archives/x/xapian-core/README.md, commands.json, manifest.yaml`。

判据本身过粗（`check_branch_and_paths` 用 `len(f.split('/')) < 5` 一律判违规），与三处硬规范互斥：

| 判据 | 位置 | 认定的 commands.json 路径 |
|------|------|---------------------------|
| R38 规范 | `knowledge/ARCHIVE-SPEC.md:85-89`（另 `:21-24` 软件级 README/manifest 为必须） | `archives/{letter}/{name}/commands.json`，**与 manifest.yaml、README.md 同级** |
| PF8 | `scripts/ohc/preflight.py:518` `cj = pkg_dir / "commands.json"` | 只查软件级 |
| CI L0k | `ci/conan/build_and_test.sh:690-692` `PKG_SOFTWARE_DIR="$(dirname "$CONANFILE_DIR")"` | 只查软件级 |

对照实验（镜像目录，未动仓库）证明**把文件下移到版本目录不是解法**：

```text
变体 现状（软件级 commands.json）   : PF8 PASS  PF9 FAIL   CI L0k -> [ok] commands.json valid (type=tool)
变体 commands.json 移进 2.0.0/      : PF8 FAIL（"CLI 包缺 commands.json"）  PF9 仍 FAIL（顶层 manifest.yaml 仍 4 层）
                                     CI L0k -> [fail] CLI tool detected but commands.json missing => L0_FAILED=true
变体 连顶层 manifest.yaml 一起删    : PF8 依旧 FAIL；且违反 ARCHIVE-SPEC「README.md/manifest.yaml 必须」，
                                     并删除 1.4.22/1.4.26 共用的既有声明（破坏旧版本）
```

**处置**：归档布局一字未改；修正框架侧判据 —— `scripts/ohc/preflight.py` 的
`check_branch_and_paths` 豁免 ARCHIVE-SPEC 规定的软件级法定文件
`{commands.json, manifest.yaml, README.md}`，并把"真·No packages to build"的判定改为
**变更清单中不存在任何 depth≥5 的 archives 配方文件时才报**（原语义保留、误报消除）。
回归验证 4 个场景：现状 16 文件 PASS；混入 `archives/x/xapian-core/conanfile.py`（真错位）仍 FAIL；
纯软件级无配方变更 FAIL（新语义）；仅版本目录文件 PASS。
修好后 PF1–PF9 + PF5扩面 + R52 对现状 16 文件 = **0 findings**。

注：PF9 只存在于客户端 `scripts/gitcode_pr.py:297` 的 create-pr 前置闸，
`grep -rn preflight.py ci/` = 0 命中，CI 侧从来不跑 PF9 —— 所以这个冲突不影响 CI 绿，
修判据是为了让本地 preflight 与 CI 口径一致，而不是绕过任何真实检查。
框架改动属 `scripts/`，按协作铁律须走**独立框架 PR**，与本配方 PR 分开提交。

### finish [3/10] G0 clean-verify 失败根因（平台/脚手架，非配方）

```text
configure: error: working directory cannot be determined
shell-init: error retrieving current directory: getcwd: cannot access parent directories
```

本机复现（与 `scripts/ohc/clean_verify.py:156-161` 同样的 `subprocess(cwd=…)` 方式）：

```text
python subprocess.run([bash,"-c","pwd"], cwd=<…>/tmp/builds/xapian-core-2.0.0.work)  -> pwd 失败 rc=1
python subprocess.run([bash,"-c","pwd"], cwd=<…>/tmp/<任何新建目录>)                   -> pwd 失败 rc=1
```

即：本环境下以 `cwd=` 方式派生的 bash 无法 `getcwd`（`/storage/Users/currentUser/tmp` 下**所有**目录都失败，
包括本包构建成功过的 work 目录），故 `clean_verify` 起 `configure` 必挂；
同一份补丁源码经 conan 的 `create`/`test` 与 W3 真机模拟均为绿（G2 PASS、JC/L0/L1/L5 PASS）。
可归因到脚手架应以 `cd <dir> && <cmd>` 形式下发命令（与 conan 的做法一致），属框架侧待办，
不在本包修改范围；G0 在 `finish` 中标注为非阻塞。

### 其他修正记录

- 上游测试统计以 `13-make-check-final.log` 为准（打上 lockfileumask1 补丁后的复验轮）；
  `10-make-check.log` 是修复前的对照轮（glass 后端 1 失败即 `lockfileumask1`），两版都保留。
- `commands.json` 的 `2.0.0.binary` 初版误写 `true`，已按 ARCHIVE-SPEC §2.1 语义改为
  `false`（适配中未上传制品）；同时把软件级 `manifest.yaml`/`README.md` 里
  2.0.0 的存量 `published / 2026-06-15` 纠正为 `built / 2026-09-05`
  （该“published”是空壳归档遗留：目录里既无 conanfile 也无 sha256）。
- PF9 修正后重跑全套 finish 门禁（`33-finish-after-pf9fix.log`），`.ci-result.json` 与
  `reports/w3-local-ci.log` 已被新一轮覆盖，本文与 `manifest.yaml`、`reports/test-report.md`
  三处引用同步更新为 `4e9ca467…f691d8` / `integrity_hash=0f2d4b220989652e`。

## 交付清单与后续动作（本任务止于 LOCAL_AUDIT_PASS）

本包**未** claim、未 `git commit`、未 `git push`、未创建/更新 Issue 或 PR、
未 `conan upload` 制品、未做远端 Review。仅创建了本地分支 `feat/xapian-core-2.0.0`
（无 commit，HEAD 内容仍等于 main；工作区内其他包的脏文件未被触碰）。

交付文件共 16 个，全在 `archives/x/xapian-core/` 下：

- `2.0.0/`：`conanfile.py`、`conandata.yml`、`manifest.yaml`、`notes.md`、
  `patches/0001-backends-uuids.cc.patch`、`0002-config.guess.patch`、
  `0003-config.sub.patch`、`0004-configure.patch`、`0005-tests-api_backend.cc.patch`、
  `test_package/{conanfile.py,CMakeLists.txt,MANIFEST.yml,test_xapian_core.cpp}`
- 软件级：`commands.json`（新增 `2.0.0` 条目，`binary: false`）、
  `manifest.yaml` 与 `README.md`（把遗留空壳记录的 `2.0.0 published / 2026-06-15`
  纠正为 `built / 2026-09-05`；该目录此前既无 conanfile 也无 sha256）
- 另有知识草稿 `knowledge/drafts/E543-draft-C300.kv` + `.md`
  （toybox sed 静默清空生成头文件，对应上文问题 #3）

后续若有人接手提交，必须**精确 `git add` 上述 16 个路径 + 两个草稿文件**，
禁止 `git add archives/` 或 `git add -A`：当前工作区还带着与本任务无关的脏项
（`SKILL.md`、`archives/l/libXext/*`、未跟踪的 `archives/olsrd/`、`archives/osqp/`），
误加即违反 W2/PF1/JC6 单软件原子性。另外 `submission.py` 的默认 add 规则只会带
版本目录与 `knowledge/drafts/`，软件级 3 个文件不会自动入 PR，
而缺 `commands.json` 的 `2.0.0` 条目会让 CI L0k 硬失败——必须手工带上。

PR 说明必须附：① R51 上游测试申报（3617 用例 / 3545 通过 / 1 失败 / 70 跳过 / 1 预期失败，
含逐项名称）；② `qp_scale1` 不改测试、只如实上报的理由与 8 轮 `-b` 单后端复跑留档。
（原第①条"PF9 豁免申请"已作废 —— PF9 判据按上文修正后，
`run_preflight(repo, HEAD, <18 文件合成 commit>)` 返回 `True / 0 findings`，
不再需要 `--no-preflight`。框架改动 `scripts/ohc/preflight.py` 须另开一个框架 PR，
不与本配方 PR 混提。）

#### qp_scale1 复跑口径注记

`./apitest` 的后端选择参数是 `-b <backend>`；**位置参数只作 TESTNAME 过滤**。
17:49 版留档用的 `./apitest multi_remoteprog_glass qp_scale1` 里
`multi_remoteprog_glass` 不是测试名（匹配 0 个），实际效果是"10 组后端 × qp_scale1"，
故该文件每轮恒打印 6 条（6 个后端组）且**未记后端名**；21:12 起的 `-b` 留档才是单后端数据。
17:49 那版多后端混合留档**已被 21:12/21:42 的 `-b` 单后端留档覆盖**（当前文件仅含 `-b` 数据），
其 6 个数值只存在于本机 gitignore 的 reports/test-report.md §4 与第 4 轮审计记录里（不随 PR 交付），
  因此不再把它当数据出处引用。

## 框架侧工具口径问题（本包不受本地门禁阻塞，但提交前需知晓）

1. `finish` step [10/10] 把"缺 `packaging/*.tar.gz`"列为未就绪项，但
   `knowledge/ARCHIVE-SPEC.md:7,242-245` 明确 `packaging/` 目录、`packaging/*.tar.gz`、
   `packaging/.packaged` 均已**废弃**（由 `conan create` + `conan upload` 替代），
   全仓 5303 个版本目录（5286 个含直接文件）里只有 36 个遗留 packaging/（全仓同名目录共 38 个）；更关键的是
   `ci/scripts/junk_check.sh:136-137`（JC3 制品闸）会把 `/packaging/.*\.tar` 判为杂项文件
   —— **创建它反而会挂 CI**。`submission.py:2214-2217` 自身也只记 WARN。
   故本包不创建 `packaging/`，此项按规范判定为不适用。
2. 版本级 `manifest.yaml` 缺**顶层** `build_system` 会让
   `submission._check_manifest_complete` 返回 False（`_REQUIRED_MANIFEST_FIELDS`
   要求顶层键；全仓实测 5044 个版本级 manifest 中 3625 个（71.87%）写了顶层 `build_system`）。
   已补 `build_system: autotools` → 6 项自检中 5 项 PASS，
   第 6 项 `packaging_present` 因上述规范冲突判为不适用（见下一条，它会硬阻塞 submit）。
   注：同软件的 1.4.22/1.4.26 也缺该键（存量漂移，不在本 PR 范围）。
3. **`packaging_present` 在 submit 侧是硬阻塞——所以本包无法在不做框架改动的前提下走 submit
   （这是当前唯一的真实阻塞项，需与 PF9 合并进同一个框架 PR）**：
   `submission.py:2214-2216` 的 Check 9 只记 WARN，但 `cmd_submit` 的 Gate 4 自检清单
   （`submission.py:1074-1081` + `1088-1096`）把 `packaging_present=False` 计入 `failed_checks`
   并 `return 1` → 对 `status: built` 的包，`ohc submit` 会被"必须打包 tar.gz"卡住，
   而该要求已被 ARCHIVE-SPEC v3.0 废弃、且 tar.gz 会被 JC3 判为杂项文件。
   修法建议：`_check_packaging_present` 仅在 `status == "published"` 时要求产物，
   或整体移除该检查（与 §7 对齐）。本包不创建 `packaging/`。
4. PF9 判据修正目前**没有配套防回归单测**（`tests/test_v1220.py::test_pf9` 只覆盖旧语义），
   框架 PR 应补：软件级 {commands.json,manifest.yaml,README.md} + 版本目录 → PASS；
   真错位文件 → FAIL；纯软件级无配方 → FAIL。
5. 知识草稿 `E543` 与仓内既有 E543 草稿撞号（`ls knowledge/drafts | grep -c '^E543-draft-'` = 20），
   promote 时由主编重编号；PR 建出后需回填草稿的 `source_pr` 字段。

## 注意事项

- `xapian-config` 是 shell 脚本，安装后需要 `0755`（配方 `package()` 已处理），
  首次执行二进制会触发 OHOS 安全弹窗（R7）。
- 包内 `lib/cmake/xapian/xapian-config.cmake` 是上游自带的变量式脚本
  （`XAPIAN_LIBRARIES`，无 imported target），消费者统一走 Conan 的 CMakeDeps：
  `find_package(xapian)` + `xapian::xapian`，与 `cmake_file_name`/`cmake_target_name` 对齐。
- 2.0.0 移除了 `Xapian::version_string()`，版本断言只能用 `XAPIAN_VERSION` 宏，
  `test_package` 已按此编写。
- 本目录 `status: built`：仅本地 `conan create`/`conan-verify` 通过，
  **未执行 `conan upload`，未发布制品**。
---

**编译结束**: 2026-09-05 20:03
**最终状态**: built
