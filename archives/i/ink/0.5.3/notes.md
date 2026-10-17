# ink 0.5.3 适配笔记

## 编译环境
- 构建系统: autotools（autoconf 2.69 老式，configure.in；config.guess/sub 2018-02 vintage）
- 编译日期: 2026-09-27
- 编译器: clang 15（/data/service/hnp/bin/clang，OHOS aarch64，musl libc）
- 状态: built（conan-verify Verdict=PASS，见 reports/conan-verify-report.md）
- Conan: 2.29.1（OHOS 适配版），profile ci/conan/profiles/ohos-aarch64
- 本轮适配机: A 机（worktree ~/qzy/主理-73-ink-0.5.3，CONAN_HOME ~/tmp/ch/home-主理-73-ink）

## 源 URL 选择（R39 例外说明）
- 上游官方 sourceforge 实测不可达：`https://downloads.sourceforge.net/project/ink/ink/0.5.3/ink_0.5.3.tar.gz`
  返回 404；`https://sourceforge.net/projects/ink/files/ink/0.5.3/ink_0.5.3.tar.gz/download`
  返回 57851 字节 ASCII HTML interstitial（非 tarball）。
- 改用 `https://deb.debian.org/debian/pool/main/i/ink/ink_0.5.3.orig.tar.gz`
  （sha256 2d318fb6a826ef3a...60ba）：orig.tar.gz 是**未加 debian/ 目录的上游原生
  tarball**，解包清单与上游布局一致（ink.c/malloc.c/configure.in/Makefile.am/
  config.guess/config.sub/ink.spec.in/ink.1.in...），非 Debian 重打包。

## 依赖
- **libinklevel/0.9.7**（制品仓已发布，recipe+binary 直接 Download 自 ohpcd）：
  ink 是它的命令行前端。注意 configure 经 AC_CHECK_HEADERS(inklevel.h) 与
  AC_CHECK_LIB(inklevel, get_ink_level) **硬依赖**该库（任务前置情报称"无第三方
  库依赖"系误判，实际必须依赖 libinklevel，已按源码实况修正并确认 W0 可满足）。
- libusb/1.0.27、libxml2/2.15.3 为 libinklevel 的传递依赖，Conan 自动解析。

## 编译步骤（conan create，全日志见 reports/conan-create.log）
1. source(): get 下载+解包 → apply_conandata_patches 应用三件补丁（日志 111-113 行）
2. generate(): AutotoolsDeps（-I/-L/-l 注入 conanbuild）+ AutotoolsToolchain
   + LD_LIBRARY_PATH 指向依赖 lib 目录（conftest/运行期加载共享库）
3. configure：host= aarch64-unknown-linux-ohos；inklevel.h yes；
   get_ink_level in -linklevel yes；GNU libc compatible malloc yes
4. make -j1：clang -DNDEBUG -Wall -O3 编 ink.o/malloc.o，
   链 `-linklevel -lxml2 -lusb-1.0 -lm -lpthread`
5. package: bin/ink（27072 字节，sha256 e6aa9c99a2175aea...）+ share/man/man1/ink.1
6. test_package：bash test.sh → `ink -v` 输出 "ink 0.5.3 / libinklevel 0.9.7" rc=0 ✅

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 报 "cannot guess build type" 退出 1（前任卡点 autotools.configure() Error 1 的复现） | config.guess(2018-02-24)/config.sub(2018-02-22) 不识 HarmonyOS/OHOS；内置 patch-autotools-ohos.pl 依赖的 __ANDROID__/LIBC=android、android-linux 等锚点在该 vintage 不存在，实测 Score 1/5，config.guess 仍 unable to guess（E007） | 按 libinklevel 0.9.7 已验证同款最小手补：0001 config.guess 增 `*:HarmonyOS:*:*` case 输出 aarch64-unknown-linux-ohos；0002 config.sub 在 KERNEL-OS 组合白名单与基本系统类型清单两处放行 linux-ohos（补丁不含平台宏） |
| 2 | HMDFS 上 configure mktemp -d 分支历史不可用（E490，libinklevel 实证） | autoconf 2.69 生成的 mktemp -d ./confXXXXXX 在 HMDFS 部分路径/固件下失败 | 0003 补丁改固定目录名（与上游 fallback 分支语义一致）；2026-09-27 探针显示当前固件在 ~/tmp 下 mktemp 可用，补丁作为同源已验证防御保留 |

第一条真实错误（探索阶段，证据 $HOME/tmp/uc2/ink/explore.log）：
`./config.guess: unable to guess system type ... config.guess timestamp = 2018-02-24`
随后 `configure: error: cannot guess build type; you must specify one`（configure_rc=1，
make 因无 Makefile 连锁失败 rc=2——首错是 config.guess，非 make）。
最小复现：解包 orig tarball → 裸跑 `./config.guess` rc=1。

## 已试败方案
- `perl scripts/patch-autotools-ohos.pl config.guess config.sub`（内置脚本）：
  "Some patches may have failed"（Score 1/5），打完 config.guess 仍 rc=1 →
  弃用脚本，改按 libinklevel 同款手补两处。
- finish Step1 `refresh-patch --auto` 事故（2026-09-27 00:30 首轮 finish）：
  它基于 init-build work 目录（ink-0.5.3.work，残留探索期 perl 脚本改动）的
  编辑追踪器重生成补丁，把归档里手写的 0001 覆盖、0002/0003 删除，导致该轮
  G2/W3 红（首错：conandata 列出的补丁文件缺失）。修复：从
  patches/.patch-backup-*/ 恢复三件补丁 + manifest.yaml 复位，并把 work 目录
  的 config.guess 复位为 orig 使 refresh-patch 判零变更；复跑 finish 全绿。
  教训：**手写 patches/ 的包在 finish 前必须把 init-build work 目录复位到
  orig（或让 work 目录内容与补丁后一致），否则 refresh-patch 会按 work 目录
  差异重生成补丁覆盖归档**。

## 上游测试口径（R51 三步法）
- **清点**：上游无测试套件。证据：Makefile.am 仅 `bin_PROGRAMS=ink` 与
  `dist_man1_MANS=ink.1`，无 check 目标/TESTS 变量；源码树仅 ink.c（257 行）/
  malloc.c（17 行），无 tests/ 目录；`make -n check`（在真实配置后的构建目录）
  仅输出 config.h 时间戳规则，无任何测试命令。
- **可运行环境实测**：可执行上游测试数 = 0（无测试可运行）。
- **本包补齐**：消费者冒烟 test_package/test.sh（`ink -v`，2 条断言：首行=
  PACKAGE_STRING "ink 0.5.3"；次行调用 libinklevel get_version_string() 证明
  动态链接成功），conan create 内实测 1/1 通过。
- **五维账本**：上游静态总数 0 / 上游可执行数 0 / 上游实测通过 0 / 跳过 0 /
  失败 0；消费者冒烟 1/1 通过（非上游测试，不计入上游账本；正文数字与实测同源）。

## K0 口径自检（命令行工具运行探针，打包产物实跑）
- `ink -v` → **rc=0**，stdout "ink 0.5.3\nlibinklevel 0.9.7"（版本探针正常）
- `ink --help` → rc=1，stderr "unrecognized option: -" + usage（上游 getopt 串
  "b:p:n:t:v" 无长选项，属上游原设计，非适配缺陷）
- `ink --version` → rc=1，同上（上游版本探针是短选项 `-v`）
- `ink`（无参）→ rc=1，stdout usage（argc==1 → usage(); return 1，上游原设计）
- readelf -d NEEDED: libinklevel.so.5 / libxml2.so.16 / libusb-1.0.so.0 / libc.so

## B 判定（路径 B）终评：none
- 当轮第一条真实错误 = 老式 config.guess/config.sub 不识 OHOS 三元组
  （"unable to guess" → configure Error 1）。该机制同层条目已存在：
  E007（patch-autotools-script：config.guess/sub 补 HarmonyOS 识别）与
  E268（patch-autotools-ohos.pl 对特定 vintage config.sub 失效——记 2024+ 新版
  误判形态；本轮 2018-02 老版"锚点缺失致补不全"为同一机制族的 vintage 变体，
  按"组合型知识不判重"口径不另立新条目）。
- 处置完全落在 E007 推荐方案（手补 config.guess/sub，无平台宏）内，
  无「KB 无同层条目且可跨库复用」的新机制 → 维持 B判定=none，不建
  knowledge/drafts/DRAFT-*。（finish 阶段 refresh-patch 覆盖手写补丁的
  工作流坑已在上方"已试败方案"留痕，供主代理酌情另行立项。）

## 验证结果
- conan-verify: **Verdict: PASS**（reports/conan-verify-report.md，2026-09-27）
- G2 conan create 日志: reports/conan-create.log（configure→make→package→
  test_package 端到端，test 输出含 "[test] ✅ ink -v OK"）

## 注意事项
- `ink -v` 之外的功能（-p usb / -p bjnp / -b uri 查询真实打印机余量）需要打印机
  硬件，CI/本机均无环境——冒烟口径以 `-v` 为准，不伪造打印查询测试。
- libinklevel 为共享库，直接运行 ink 需 conanrun 环境（VirtualRunEnv）注入
  LD_LIBRARY_PATH；test.sh 已在 conanrun 下验证通过。
- 前任在另一机器的工作未推送已丢失，仅存"configure Error 1"卡点情报；本笔记
  已用盘面证据重建全链路并修复该卡点。
---

**编译结束**: 2026-09-27 00:48
**最终状态**: built
