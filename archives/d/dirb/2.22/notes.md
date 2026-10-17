# dirb 2.22 适配笔记（HarmonyOS PC）

## 概况

- 构建系统：老式 autotools；tarball 自带预生成 `configure`（GNU autoconf 2.69）与
  `Makefile.in`（automake 1.9.6）。`configure.ac` 无 `AC_CANONICAL_HOST`，不含
  config.guess/config.sub → 无需 autoreconf，也无需 OHOS 三元组补丁（R1 原生编译）。
- 产物：`dirb`（主工具）、`gendict`、`html2dic` 三个可执行文件 + man 页 `dirb.1` + 词表目录。
- 依赖：唯一外部依赖 libcurl（`configure.ac` 用 `curl-config` + `AC_CHECK_LIB(curl,
  curl_easy_init)` 探测），经 `self.requires("curl/8.15.0")` 提供。

## 关键问题与修法

### 1. clang -fno-common 多重定义（patch 0001）

`src/variables.h` 在头文件里直接定义全局变量（`FILE *outfile`、`CURL *curl`、
`struct opciones options` 及 19 个 int/struct 指针），经 `src/dirb.h` 被 8 个 TU
（dirb.c、crea_wordlist.c、get_url.c、lanza_ataque.c、calculanec.c、utils.c、
options.c、resume.c）包含。clang 默认 `-fno-common` → 链接报 multiple definition。

修法（AUR dirb 同思路）：variables.h 全部改 `extern` 声明，新增 `src/variables.c`
单点定义；同步把 `variables.c` 注册进 `src/Makefile.am`（base 列表）与
`src/Makefile.in`（`base` 与 `am__objects_1`——tarball 无需 autoreconf，构建实际读
Makefile.in，两处都要改）。兜底方案（配方加 `-fcommon`）未采用。

### 2. 默认词表路径硬编码 /usr/share（patch 0002）

`src/dirb.c:62` 无词表参数时默认 `/usr/share/dirb/wordlists/common.txt`（OHOS 不
存在），`src/dirb.c:284` usage 示例同样硬编码。上游 make install 也不安装 wordlists。

修法：dirb.c 新增 `default_wordlist()`，运行期经 `/proc/self/exe` 解析
`<exe_dir>/../share/dirb/wordlists/common.txt`（conan 包、hnp、FHS 布局都保持
bin/ 与 share/ 的相对位置），解析失败回退 CWD 相对路径；`package()` 把
`wordlists/`（1.6MB，common.txt 4614 行）装入 `<prefix>/share/dirb/wordlists`。

### 3. configure 丢执行位 + man 页安装（平台 install 语义）

- **configure 无执行位**：tarball 里 configure 本有 +x，但 conan 解包后丢失；
  `Autotools.configure()` 直接 exec configure → `/system/bin/sh: can't execute:
  Permission denied`（conan Error 126；run1/run2 日志实证，run1 日志 5191-5197
  行）。真机探针：python `os.chmod()` 与 `/usr/bin/chmod` 均可置位（640→750，
  X_OK）→ build() 里 `os.chmod(configure, 0o755)`（同款手法见
  archives/a/abiword-plugin-pdf/3.0.8/conanfile.py）。config.status 由 configure
  经 `$SHELL` 调用（autoconf 2.69 生成代码），不受影响。
- **man 页安装**：automake 1.9 的 `install-man1` 规则用 `$(INSTALL_DATA)`
  （= `${INSTALL} -m 644`），configure 探测到平台 `INSTALL=/system/bin/install
  -c`。真机探针：`/system/bin/install -c -m 644` 返回 0（产物权限位受文件系统
  umask 影响为 640）。为不依赖平台 install 的模式位与多文件语义，package() 用
  配方内 install shim 覆盖 `INSTALL` 与 `INSTALL_DATA`（忽略模式位、文件 cp、
  目录 mkdir -p）；CI run5 起 make install（含 man 页）实测成功。

### 4. configure 的 HMDFS 适配（配方内运行期改写）

autoconf 2.69 生成的 configure 有两处 HMDFS 阻塞点（临时目录问题同 E114，
记载于 archives/a/aaphoto/0.45/notes.md 问题表第 1 行；getcwd 问题另见
knowledge/drafts/DRAFT-6487-classads-configshell-hmdfs-getcwd.md）：

- `./confXXXXXX` + `umask 077` 临时目录 → 改 `${TMPDIR:-/tmp}`（只读 /tmp 与
  HMDFS 上失败）；
- `ac_pwd=\`pwd\`` 判定 → getcwd 失败时回退 `$PWD`，并在 build() 预置
  `PWD` 环境变量兜底（HMDFS 对构建树父目录不提供 getcwd()）。

### 5. curl-config 探测

configure.ac 在 PATH 上直接调用 `curl-config --version/--cflags/--libs`。
generate() 用 `Environment` 把全部 host 依赖包的 `bin` 目录（含 curl 包的
curl-config）前置进 conanbuild PATH；`AutotoolsDeps` 提供 `-I/-L` 供
`AC_CHECK_LIB` 与最终链接使用。

## 上游测试门禁证据（NO_UPSTREAM_TESTS）

检查过的入口与结论：

- **Makefile.am（全部 4 个：顶层、src、gendict_src、web2dic）**：顶层仅
  `AUTOMAKE_OPTIONS/SUBDIRS/man_MANS/EXTRA_DIST/CLEANFILES/DISTCLEANFILES`；
  三个子目录仅 `bin_PROGRAMS` + `AM_CFLAGS` + 源列表。没有任何 `check:`/`TESTS`/
  `test` 目标 → `make check` 无事可做（automake 仅回 "Nothing to be done for
  'check'"）。
- **docs/**：仅 CHANGES.txt、FAQ.txt、GENDICT.TXT、INSTALLATION.txt、TODO.txt，
  无测试文档；tarball 无 test/、tests/ 目录（win32/ 为 Windows 工程文件）。
- **configure.ac**：除 libcurl 探测（curl-config + AC_CHECK_LIB）外无任何测试
  框架/程序探测（无 AC_CONFIG_TEST_DIR、无 dejagnu/autotest、无测试类
  AC_CHECK_PROGS）。
- **CI 惯例**：无上游官方测试命令可运行（`make check` 为空操作），不满足
  no_official_test.txt 白名单语义（该白名单面向"上游有测试但与 OHOS 环境不兼容"
  的情形），L1 门禁由 test_package 真实执行满足，无需白名单。

结论：上游无任何自动化测试套件，无法运行上游官方测试 → 建议记录
`NO_UPSTREAM_TESTS` discovery。功能性验证由 test_package 承担（真实编译运行 +
本地 loopback HTTP 服务字典扫描）。

## 验证

- test_package：无参 usage 冒烟（断言 banner 且按上游约定非零退出）+ 本地
  loopback HTTP 服务（python3 http.server）+ 预置词表扫描，断言发现预置目录
  admin/、backup/。
- CI：ci/conan/build_and_test.sh，profile=ohos-aarch64（host/build 显式传递），
  CI_PACKAGES=archives/d/dirb/2.22。

## CI 历程与证据口径

- run1：CI pre-download 子进程找不到 curl（`[Errno 2] No such file or directory:
  'curl'`，run1 日志 84-89 行）未完成预下载；conan source() 自行下载源码成功
  （run1 日志 5174 行 "Sources correctly downloaded"）；真实失败点为 configure
  执行位（Error 126，run1 日志 5191-5197 行）。CI 摘要中的 "429" 提示为通用
  关键词触发的修复建议，日志中无任何 HTTP 429 记录。
- run2：预置 CI 预下载缓存后复现同一 Error 126 → build() 增加 os.chmod 修复。
- run3：conftest "cannot run C compiled programs" → 依赖 libdir 注入
  LD_LIBRARY_PATH 修复。
- run4：variables.c "tentative definition has type 'struct opciones' that is
  never completed" → variables.c 改为 include dirb.h（经 dirb.h 引入
  estructuras.h 补全类型）。
- run5 起：PASS（L0/L1/L4/L5 pass，L2 skip 为上游无 --version/--help 的既有
  行为，非阻塞）。
- 真机探针存证：`/system/bin/install -c -m 644` 退出码 0（产物权限 640）；
  os.chmod 640→750 且 X_OK；`/usr/bin/chmod +x` 生效。
