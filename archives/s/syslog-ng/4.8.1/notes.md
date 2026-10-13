# syslog-ng 4.8.1 — OHOS 适配笔记

状态：built（配方与归档齐备；真机构建/测试数据回填见下）

## 来源与版本

- 上游发布包：`syslog-ng-4.8.1.tar.gz`（顶层目录 `syslog-ng-4.8.1/`）
- 下载地址（按序兜底）：
  1. `https://sources.buildroot.net/syslog-ng/syslog-ng-4.8.1.tar.gz`（设备实测可达；Content-Length 与本地锁定文件逐字节一致）
  2. `https://downloads.yoctoproject.org/mirror/sources/syslog-ng-4.8.1.tar.gz`（同文件源镜像兜底）
  3. `https://github.com/syslog-ng/syslog-ng/releases/...`（仅参考置后；前两条镜像 URL 不含 github 子串，对平台 E017 的 ghfast.top 改写免疫）
- SHA256：`e8b8b98c60a5b68b25e3462c4104c35d05b975e6778d38d8a81b8ff7c0e64c5b`（本地实下锁定）
- 构建系统：autotools（tarball 自带预生成 configure；捆绑 `lib/ivykis` 经 `AC_CONFIG_SUBDIRS` 二次 configure）
- 许可证：GPL-2.0-or-later（核心与模块）与 LGPL-2.1-or-later（`lib/` 复用库）组合，见 COPYING

## 构建配置

| configure 开关 | 原因 |
|---|---|
| `--disable-python --disable-python-modules` | 交叉环境无 python3 开发包；python 模块不构建 |
| `--disable-java --disable-java-modules` | 同上（无 JDK） |
| `--disable-systemd` | OHOS 无 systemd（journal 集成关闭） |
| `--with-libcurl=<libcurl 包目录>` | curl 检测直接指向制品仓包（不依赖 PATH 探测） |

不使用 `--build=/--host=/--target=`（native 编译纪律）：三元组识别由 0001–0004/0007–0009 补丁下的三套 config.guess/config.sub 自检完成。

五组致命 pkg 检查（GLIB/PCRE2/OPENSSL/JSON/CRITERION）经 pkg.m4 的 `<VAR>_CFLAGS/<VAR>_LIBS` 环境变量短路注入包内真实路径（见「已知说明」）；`make -j1`（HMDFS jobserver 限制）。

## 补丁清单与落点

| 补丁 | 文件 | 内容 | 依据 |
|---|---|---|---|
| 0001 | `config.guess` | case 头后新增 HarmonyOS 识别 → `aarch64-unknown-linux-ohos` | 上游不识别 HarmonyOS uname |
| 0002 | `config.sub` | 接受并归一化 `linux-ohos` 内核-系统组合（否则被 `linux*)` 变换吞成 `linux-gnu-ohos`） | 同上游 rsyslog/libestr 同款修法 |
| 0003 | `lib/ivykis/config.guess` | 同 0001；ivykis 自带独立副本（AC_CONFIG_SUBDIRS 再跑一次 configure） | 同上 |
| 0004 | `lib/ivykis/config.sub` | 同 0002 | 同上 |
| 0005 | `configure` | 临时目录创建块 `umask 077` → `022` | E011：HMDFS UID 映射使 0700 目录对当前进程不可写 |
| 0006 | `lib/ivykis/configure` | 同 0005 | 同上 |
| 0007 | `lib/ivykis/test.mt/config.guess` | 同 0001；第三套独立副本（该子项目自带 configure 与三元组脚本） | 裸副本落到编译哑元兜底并在 HMDFS 上死于 `mktemp -d`（E046 族 Permission denied） |
| 0008 | `lib/ivykis/test.mt/config.sub` | 同 0002 | 同上 |
| 0009 | `lib/ivykis/test.mt/configure` | 同 0005 | 同上 |
| 0010 | `lib/ivykis/test.mt/iv_thread_test.c` + test.mt `configure`/`configure.ac`/`config.h.in` | 取消语义测试段以 `HAVE_PTHREAD_CANCEL` 守卫；test.mt 子工程新增 `AC_CHECK_FUNCS(pthread_cancel)` 能力探测 | OHOS libc 无 `pthread_cancel`/`pthread_testcancel`（全树唯一使用点），链接期未定义符号 |
| 0011 | `modules/afuser/afuser.c` | utmp 查询实现以既有能力宏 `SYSLOG_NG_HAVE_GETUTXENT` 守卫，探测失败时为空查询 | OHOS 仅存根 `utmpx.h`、无 `getutxent`/`endutxent` 与 utmp 库；usertty() 目标退化为「无登录用户」 |
| 0012 | `lib/thread-utils.h` + `configure`/`configure.ac`/`config.h.in` | `thread_cancel()` 在 `SYSLOG_NG_HAVE_PTHREAD_CANCEL` 未定义时 no-op；`pthread_cancel` 加入既有 `AC_CHECK_FUNCS` 列表 | C++ TU（modules/examples/random-choice-generator）把未声明标识符升级为硬错误 |
| 0013 | 根 `Makefile.in` + `modules/http/Makefile.am` | 模块 LIBADD 显式补 `$(ZLIB_LIBS)` | musl 对 dlopen 模块做 eager 重定位：上游动态链接模式从未给 libhttp.so 链 `-lz`（compression.c 调 `deflateInit2_`/`deflateEnd`），glibc 惰性绑定可容忍、musl 直接拒载（`symbol not found`） |

补丁为 unified diff（a/ b/ 前缀，strip 1）；文件不相交，按序应用无耦合。`ZLIB_LIBS` 为 configure.ac 既有 `AC_SUBST` 变量（modules/afsocket 已在用），经 recipe 环境注入。

## 本地验收（Windows 主机）

- **13 补丁按序应用无冲突**：conan create 实跑经 `apply_conandata_patches` 全量应用通过（0001–0006 的六文件曾另经本地纯净解压逐字节比对，md5 六项全 MATCH）
- **config.guess 假 uname 测试**：模拟 `uname -s HarmonyOS / -m aarch64` → `aarch64-unknown-linux-ohos`（rc=0），顶层与 ivykis 副本同行为
- **config.sub 矩阵 5/5 通过**：`aarch64-linux-ohos`、`x86_64-unknown-linux-ohos`、`arm-unknown-linux-ohos` 归一化正确；`aarch64-unknown-linux-gnu` 回归不变

## 真机验证（HarmonyOS PC aarch64）

- 构建：`conan create`（ohos-aarch64 profile，clang 15，Release）——`SNG_CREATE_EXIT=0`（全量构建含全部模块，`make -j1`；后续重跑命中缓存秒过）；配方最终版（补丁后 Makefile.in 时间戳归一，见「已知说明」）已在全新树净建复跑（约 22 分钟）+ test_package ALL_PASS 验证
- 消费者 test_package：14/14 全过（守护进程起停、`--version` 重定位、模块注册表、控制套接字端到端）
- 上游 `make check`（criterion 单元测试，全量重跑 207 项）：**196 PASS / 11 FAIL / 0 ERROR / 0 SKIP**，退出码 2（存在失败项时 make check 的非零退出）。**11 项 FAIL 全部为平台性限制**（与配方/补丁无关）：时区数据库/宿主机 TZ 依赖 4 项（rewrite、unixtime、date、format_date）、musl 与 glibc 时区解析差异 5 项（template、scan_timestamp、conv、msgparse、zone）、系统 `/tmp` 只读 1 项（secure_logging）、平台无 `sys` 组 1 项（userdb）。首轮验证（run#13，同环境）另有 1 项计时 flake（logthrdestdrv）出现、单跑复验 2/2 通过；最终轮（run#14，配方最终版全新树）未复现。
- `ohc-run.py conan-verify`：**Verdict PASS**（2026-10-11 16:09；八门禁 G1/G0/G2/G3/G4/L2/L4/L5 全过——G2 命中同 RREV 缓存秒过；`.conan-verified` 已写入归档目录，报告 `reports/conan-verify-report.md`）
- 产物：`bin/` 12 个工具（syslog-ng、syslog-ng-ctl、dqtool、loggen、pdbtool、persist-tool、slogencrypt、slogkey、slogverify、syslog-ng-debun、syslog-ng-update-virtualenv、update-patterndb）；`lib/syslog-ng/` 38 个模块 .so；`--module-registry` 全量 dlopen 36 个模块、`Status: Unable` 计数 0（`sbin/` 为空，上游 4.8 起工具已全部装至 `bin/`）

### 重跑步骤（可直接复用）

```sh
# 1. 完整构建 + test_package（消费者 E2E 14 例）
cd <repo>
CONAN_HOME=/storage/Users/currentUser/.conan2 conan create archives/s/syslog-ng/4.8.1 \
    -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
    --build=missing --user=ohpcd --channel=stable

# 2. 上游 make check 全量实跑（在缓存构建树内；criterion 由 test_requires 提供）
#    设备侧一键运行器：$HOME/sng-create-run5.sh（preflight + create + 本节全部 make check 环境）
#    平台三件套（见「已知说明·make check 平台差异」）：
#      - TMPDIR → el2 可写卷（系统 /tmp 只读；HMDFS 上 glib 临时文件受限）
#      - AM_CPPFLAGS 追加 libcurl 包内 include（HTTP 模块编译所需）
#      - LOG_COMPILER → cdwrap 包装器（仅 3 个 cwd 敏感测试切到 el2 运行；
#        包装器源码见设备 $HOME/sng-create-run5.sh 内联 heredoc）
#    测试夹具：modules/confgen/tests/confgentest.sh 为 shell 脚本，平台禁脚本 execve
#      （popen 码 32256）→ 以语义等价的已编译 ELF 原地覆盖（见「已知说明」）
BD="$(ls -dt $HOME/.conan2/p/b/syslo*/b | head -n 1)"   # 缓存构建树（-dt 取最新）
cd "$BD" && . ./build-release/conan/conanbuild.sh
E=/data/storage/el2/base/tmp/sng-el2; mkdir -p "$E/probe" "$E/tmp"
export TMPDIR="$E/tmp"
export SNG_CWD_DIR="$E/probe" SNG_CWD_TESTS="test_thread_wakeup test_file_opener test_qdisk"
CURL_INC="$(ls -d $HOME/.conan2/p/libcu*/p/include | head -n 1)"
AMCPP="$(sed -n 's/^AM_CPPFLAGS = //p' Makefile | head -n 1)"
find "$BD" -name '*.trs' -delete 2>/dev/null   # 清陈旧 .trs 强制全量重跑
make check -j1 "AM_CPPFLAGS=$AMCPP -I$CURL_INC" "LOG_COMPILER=$E/cdwrap"

# 3. 官方八门禁
CONAN_HOME=/storage/Users/currentUser/.conan2 python3 scripts/ohc-run.py conan-verify syslog-ng 4.8.1
```

## 可重定位说明（SYSLOGNG_PREFIX 实测点）

- 编译期模块目录默认 `${exec_prefix}/lib/syslog-ng`（conan 打包 DESTDIR 前缀下即 `/lib/syslog-ng` 死路径）；
- 运行期 `lib/reloc.c` 的 `lookup_sysprefix()` 优先取 `SYSLOGNG_PREFIX` 环境变量（配方 `package_info` 导出为包前缀）完成重定位；
- 消费者 E2E 校核 `--version` 输出的 `Module-Directory:` 指向 `$SYSLOGNG_PREFIX/lib/syslog-ng`，`--module-registry` 全量 dlopen 无 `Status: Unable`。

## 已知说明

- **pkg 短路策略与例外**：制品仓 .pc 为 relocatable 打包、前缀被改写成 `/`，直接用会产出 `-I//include` 类废路径 → 五组致命检查经 pkg.m4 的 `<VAR>_CFLAGS/<VAR>_LIBS` 变量短路（变量非空即不再调 pkg-config），直接写真实包路径。**例外**：JSON 的模块名探测走 `PKG_CHECK_EXISTS`（不吃变量短路、会真调 pkg-config），用 `PKG_CONFIG_PATH`（依赖自带 lib/pkgconfig + PkgConfigDeps 兜底）保证可发现——`--exists` 只查 .pc 可解析与 Version、不校验前缀。
- **criterion 静默探测**：configure 探测到 criterion≥2.2.1 即自动开启单元测试、找不到即静默关闭（无显式开关）→ `test_requires` criterion/2.4.3 + 变量短路确保命中，configure 摘要 `Unit tests ... yes` 作为门禁。
- **glib 必须 shared 单实例**：40+ 个 dlopen 模块与核心框架 `libsyslog-ng.so` 共享同一 gobject 类型系统；制品仓 glib/2.84.0.1 即该 shared 二进制修订。
- **autotools 三件套**：E490 辅助脚本执行位恢复（configure/config.guess/config.sub/install-sh 等 ×2 套）；依赖 .la 清理（relocatable 打包坏路径会让 libtool 报 "not a valid libtool archive"）；TMPDIR 钉在 build 目录（OHOS /tmp 只读，测试二进制写临时文件）。
- **$ORIGIN rpath 两档**：`bin/` 二进制找 `../lib` 的 libsyslog-ng.so；`lib/syslog-ng/` 模块找 `..` 的框架库（rpath 内联于 LDFLAGS，libtool 不改写）；依赖库走绝对 rpath。
- **json 头风格**：模块以 `<json.h>` 包含 → JSON_CFLAGS 额外补 `<pkg>/include/json-c` 子目录。
- pcre2/10.45 制品仓为**静态库**修订（仅 libpcre2-8.a 等），链接面无需运行时 .so。
- **make check 平台差异三件套**：「系统 /tmp 只读 + HMDFS 临时文件限制」→ `TMPDIR` 指 el2 可写卷；「HMDFS 用户卷禁 AF_UNIX bind、mkfifo/fallocate 预分配受限」→ `test_thread_wakeup`/`test_file_opener`/`test_qdisk` 三个 cwd 敏感测试经 `LOG_COMPILER` 注入的 cdwrap 包装器在 el2 目录运行（realpath→chdir→execv，名单外测试 cwd 不变；OHOS 全盘禁 symlink、禁脚本 execve，故用编译型包装器）；缓存树内复跑 `make check` 时 HTTP 模块编译需经 `AM_CPPFLAGS` 追加 libcurl 包内 include。
- **criterion worker 守护**：worker fork 失败时 criterion 无错误处理、test-driver 永久等待（挂死态特征：用例失败输出块出现但无 `[FAIL]` 用例行与 Synthesis 行、`.trs` 不落地）。处置：先 `kill -9` 子 worker 进程、隔 1s 再杀测试父进程 → driver 落 FAIL `.trs` 并继续套件。判别（vs 设备休眠）：多次探测窗口内可运行进程均不动。
- **criterion 挂死非配方缺陷**：上述挂死为设备环境下的 fork/进程配额扰动（E046 第十五弹）；test_conv 本身即平台性失败用例（musl 时区解析差异），击杀不改变结论（驱动如实记录 Killed 行，退出码 1→137）。
- **官方 conan-verify G2 首跑两坑（14:47，均已修）**：①**非递归 automake 时间戳竞态**——syslog-ng 4.8 为 subdir-objects 单顶层 Makefile，全树仅 10 个 Makefile.in、202 个 Makefile.am 均为顶层 Makefile.in 再生规则的依赖；0013 触及 `modules/http/Makefile.am` 后（同秒毫秒差即触发，实测 4ms）make 首步即走 `missing→automake-1.16` 再生分支，设备无 automake → Exit 127 直接死。对策=配方 build() 补丁后把全树 Makefile.in 的 mtime 归一到当前时刻（只动时间戳不动内容）；早期开发构建树曾因两文件恰落同一纳秒而侥幸不触发，纯净重建（verify）必踩。**2026-10-12 扩展（R8 能力探测版 0010/0012 触及 configure.ac/config.h.in 后）**：同族再生链不止 Makefile.in——`aclocal.m4`（←configure.ac/acinclude.m4/m4/*.m4）、`configure`（←autoconf）、`config.h.in`（←autoheader）任一判旧同样经 `missing` 调 aclocal-1.16/autoconf/autoheader（设备全无，Error 127）；v6 运行器净建实证顶层 `Makefile:13732: aclocal.m4` Error 127（configure 通过后 make 首步即死）。对策=归一扩展为全树两趟、按依赖序：先 aclocal.m4 归一到 T，再 configure/config.h.in/Makefile.in 归一到 T+2s（同刻会让以 aclocal.m4 为前置的二者判旧）；test.mt 子工程同构一并覆盖。本地以配方真实代码块重放验证（13 补丁链 + 设备时间戳模拟）：3 处违规（顶层 aclocal.m4、test.mt 的 aclocal.m4/Makefile.in）→ 归一后 19 个再生目标 0 违规。②**G2 预热 RREV 需「仓库版 conandata 原样」**——verify 源码注入条件为「含 github.com 且不含 ghfast.top 字样」；本包 conandata 注释即含 ghfast.top → 注入被跳过、原样导出。此前用 ghfast 变体（32292a44）换入预热导致 RREV 错位 → G2 必全量重建（踩 3600s 硬上限风险）；正确预热=直接以仓库版 create，与官方 G2 同 RREV 命中缓存。
