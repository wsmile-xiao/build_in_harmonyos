# genders 1.27-3 适配笔记

## 编译环境
- 构建系统: autotools（预生成 configure 直用，免 autoreconf——规避 worker 缺 automake 的 §一.4 假绿面）
- 编译日期: 2026-09-25
- 编译器: clang / clang++（OHOS aarch64，profile ohos-aarch64）
- 状态: built
- 工作面: in-source 构建（`self.folders.build = "."`，先例 acpitool/0.5.1）

## 版本与源码溯源（W0 三路证据）

版本串 `1.27-3` 带 Debian 修订形态，立项时按三路证据实核「官方渠道存在 1.27-3 可构建发行物」：

| 路 | 渠道 | 证据 |
|---|---|---|
| ① 上游 git | GitHub `chaos/genders` | `git ls-remote --tags` 存在 `refs/tags/genders-1-27-3`（7d35a202…），GitHub Releases 列出该 tag；`genders-1-27-1/-2/-3` 为 1.27 线三次定版 cut，与 `-1` cut 档 sha256 不同（e049d025… vs c176045a…），`-3` 是独立可构建发行物 |
| ② Debian 源 | `deb.debian.org/debian/pool/main/g/genders/` | `genders_1.27-3.orig.tar.gz`（1142250 B）+ `genders_1.27-3-3.1/3.2.debian.tar.xz` + `.dsc`（PGP 签名）齐全；`.dsc` 声明 `Version: 1.27-3-3.1` ⇒ Debian 上游版本=1.27-3；changelog 版本序列 `1.27-3-1 → 1.27-3-2 → 1.27-3-3 → 1.27-3-3.1 → 1.27-3-3.2` |
| ③ 其他发行版 | Fedora / Alpine | Fedora rawhide spec 引用 github.com/chaos/genders（1.28.1 git snapshot，未引用 1.27-3）；Alpine aports 无 genders 包 |

**sha256 同源检测**：GitHub tag 档与 Debian orig **逐字节一致**（均 `c176045a7dd125313d44abcb7968ded61826028fe906028a2967442426229894`，实测下载 == `.dsc` 签名声明）。

**版本串如实说明**：源码内部 `AC_INIT([genders],[1.27])`（`configure` `PACKAGE_VERSION='1.27'`、`META` `Version:1.27`）——`-3` 是发行身份（上游第三定版 tag / Debian 上游版本 1.27-3），上游 1.27 线三个 tag 的 AC_INIT 均为 1.27，属其一贯写法；**非**拿 1.27 冒充 1.27-3（源就是 `-3` cut 本体，双渠道 sha 同源已证）。证据档：`$TASK_DIR/w0-evidence/`（含 w0-verdict.md）。

## 编译步骤（配方实际执行）

```bash
# conanfile.py build() 内：
# 1) E011 归一：configure 的 `umask 077 && mktemp -d "./confXXXXXX"` → `umask 002 && mkdir ...`
#    （HMDFS euid(20020085)≠落盘属主(20001006)，0700 目录必拒；config.status 是 configure
#     尾段范围拷贝，confXXXXXX 全文件仅 1 处，改一处贯通）
# 2) configure（in-source）：
./configure --prefix=<conan package folder> \
  --without-perl-extensions --without-python-extensions \
  --without-java-extensions --without-cplusplus-extensions \
  --build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu \
  --enable-static --disable-shared
# 3) make -j1（钉串行，见问题表 #2）+ make check（上游 no-op，满足 TEST_QUALITY_SPEC §3.1）
# 4) 上游真实测试：src/testsuite/libgenders/genders_test -v -v（cwd=同目录可达夹具）
# 5) make install → 删除 lib/*.la（先例 a52dec）
```

`--build/--host` 说明：随包 config.guess/config.sub 为 2009-11-20（先例 #1 陈旧族），
实测两处失败——①其内嵌 `umask 077 && mktemp -d "$TMPDIR/cgXXXXXX"` 在 HMDFS 必拒
（`can't create .../dummy.c: Permission denied`）；②不识 aarch64（`cannot guess build type`）。
显式给出 build==host 后不再调用 config.guess；**两者相等 ⇒ AC_RUN_IFELSE 仍本地执行**（非
交叉跳过），以 config.h 检测正确 + 17847 项上游测试全过实证。与 E011 `forbid` 的关系：
该 forbid 针对「用 --host 规避 umask 问题」，本包 umask 问题已独立修复（第 1 步），triplet
只解决 config.guess 陈旧族。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `config.status[1098]: can't create ./confOJNGFD/subs1.awk: Permission denied` | E011 族：`mktemp -d` 强制 0700 + HMDFS 属主映射（euid 20020085 ≠ 属主 20001006，仅组可写目录可写） | build() 内 `replace_in_file` 把 configure 两处归一为 `umask 002 && mkdir`（strict=True 反静默；config.status 由 configure 范围拷贝生成，一处贯通——实测生成的 config.status 带修复） |
| 2 | `make -j4` clang-15 **ICE（frontend exit code 135）** 崩在 `genders_query.tab.c`（`genders_query.y:443 _calc_complement`） | 上游 `.y` 规则 target 名 `genders_query.c` 与实际产物 `genders_query.tab.c` 不匹配 ⇒ 每轮 make 必重跑 bison；-j>1 时并发覆写同一生成物 ⇒ 交叉写坏 | **钉 `-j1`**（A/B 实测：-j4 确定性复现 bison×3 + ICE；-j1 rc=0）。ICE 是表象，非 clang 缺陷 |
| 3 | `./configure` 不带 triplet 必败（见编译步骤说明） | config.guess 2009 双因（HMDFS mktemp + aarch64 未识别） | `--build/--host=aarch64-unknown-linux-gnu`（先例 a52dec 同款） |
| 4 | VPATH（conan 默认 out-of-source）在 `nodeattr-nodeattr.o` 处 `fatal error: 'genders.h' file not found` | 上游非 VPATH-clean：`nodeattr_CFLAGS` 用 `$(srcdir)` 相对路径，`genders.h` 是 config.status **生成物**（落在 build 树） | `self.folders.build = "."` in-source（先例 acpitool/0.5.1、abduco/0.6） |
| 5 | conan-verify **L2 冒烟门禁**：nodeattr 无 `--version`/`--help`（`usage()` 恒 `exit(1)`），单 bin 包必 FAIL | 上游仅 getopt 短选项（E503，libubox jshn 先例） | 补丁 `0001-src-nodeattr-nodeattr.c.patch`：main() 开头拦截两长选项 exit(0)（`--version` 打印 PACKAGE_VERSION=1.27）；`usage()` 拆为 `usage_msg()`+`usage()`，既有语义不变（实测 `-h`=1、错误路径=1、`-l`=0） |
| 6 | 语言预检停点（阶段1）：`task=cpp, detected=perl → env_unsupported` 假终态写共享 result 槽 | `src/extensions/perl/Libgenders/Makefile.PL` 劫持 manifest（lang_detect 排除表不含 `extensions`）；统计无 ≥70% 主体时按 manifest 判 perl；stage1 未注入任务卡 lang（默认 cpp） | 按停点交接包指令排除语言绑定目录（R47 附录 D.4，42 文件留档 `$TASK_DIR/lang-exclude/`）重跑 + `OHPCD_LANG=c` 注入 → detected=c、占比 89%、rc=0（详见 DRAFT-E727） |
| 7 | 语言排除后 config.status 报 `cannot find input file: 'src/extensions/Makefile.in'` | `AC_CONFIG_FILES` 无条件引用该目录 | 构建面恢复完整源树（配方侧 conan 下载完整 tarball 天然含该目录；`--without-*-extensions` 只关构建不删文件）——排除仅作用于语言扫描面 |

## 源码修改

- `patches/0001-src-nodeattr-nodeattr.c.patch`（+20/-1，对 CRLF 原件字节级生成）：
  L2 冒烟接口（E503），三关验证通过——NUL=0、`@@` hunk=3、真 apply 后与目标树逐字节 `cmp` 一致、
  `-R` 反向可还原。生成遵循先例 #18：**字节级读写**（原件 1680 行全 CRLF，曾因通用换行翻译
  导致整文件 diff +1699/-1680，已按 rb/wb 重做）。
- 无其他源码补丁；mktemp 归一在 build() 内联完成（先例 #8「标准适配免 refresh_patch」，同款 acpitool 内联先例）。

## 依赖版本

- 无外部 Conan 依赖（`requirements()` 为空；W0-2 清单 `w0-deps.txt` = none）
- 构建期工具：flex / bison（BUILT_SOURCES 必需，生成物不在 tarball）——设备与 CI worker
  均经 `/data/service/hnp/bin` 提供（device-facts §一.4 worker PATH 实证），不声明 tool_requires
- 可选扩展 perl/python/java/cplusplus 显式关闭（`--without-*-extensions`，上游默认全开）

## 测试口径（数量与取数命令）

**上游测试（N=17847，口径 = `genders_test -v -v` 运行级检查点）**

```bash
cd src/testsuite/libgenders && ./genders_test -v -v; echo $?
grep -c ': PASS' <日志>      # 17847
grep -c ': FAIL' <日志>      # 0
grep 'Total' <日志>          # Total Corner Case Failures: 0 / Total Functionality Failures: 0 / Total Failures: 0
```

- 参照口径（不与 N 混用）：注册测试函数 78（39 corner-case + 39 functionality，genders_test.c）；
  测试夹具 `testdatabases/` 113 个文件；automake `TESTS` 注册数 = 0（上游 `make check` 为 no-op，
  如实记录，配方保留 `make check` 调用但不以它充当测试证据）。
- 默认零输出是 harness 设计行为（仅 `-v` 且有失败才打印），**`-v -v` 是唯一正证据档**。

**test_package（消费者）**：17 断言 = test.c 16 项 API 断言 + nodeattr CLI 1 项（见 test_package/MANIFEST.yml）。

## 验证结果（探索构建轮；最终以采信轮 conan-verify 干净轮日志为准）

```bash
./configure … && make -j1        # rc=0
make check                       # rc=0（上游 no-op，如实记录）
./genders_test -v -v             # rc=0，PASS=17847，FAIL=0，Total×3=0
make install DESTDIR=staging     # rc=0，安装树 46 文件（bin/nodeattr, include/genders.h,
                                 #  lib/libgenders.{a,so.0.3.3,la}, man 42 页, lib/genders/*.pl×2）
nodeattr --version               # 1.27, rc=0（补丁后）
```

## 注意事项

- 严禁 `make -j>1`（问题 #2，会以 clang ICE 形态复现，别当编译器 bug 排查）。
- 配方默认 `shared=False`：共享构建的 `nodeattr` 依赖 loader 找 `libgenders.so.0`
  （探索轮实测 rc=127 形态留档），静态链接自足。
- `OHPCD_LANG` 必须来自任务卡（本任务 lang=c），不要依赖工具默认值（默认 cpp）。
