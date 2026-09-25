# DRAFT-htscodecs-1.6.5-ohos-autotools-conanfile-selfcontained-patch

## clean `conan create` 中 OHOS autotools 适配补丁自包含进 conanfile.py（含 aclocal tool_requires 自举）

- **触发场景**：autotools 库在 OHOS 上做 conan 配方，`conan create`（干净树）
- **报错签名**（按出现顺序）：
  ```
  Can't exec "aclocal": No such file or directory at .../Autom4te/FileUtils.pm line 299
  autoreconf: error: aclocal failed with exit status: 2
  htscodecs/Makefile.am: error: Libtool library used but 'LIBTOOL' is undefined
  configure: error: cannot guess build type; you must specify one
  Invalid configuration 'aarch64-unknown-linux-ohos': Kernel 'linux' not known to work with OS 'ohos'
  ./config.status: line 816: ./confbYzDlm/subs1.awk: Permission denied
  config.status: error: could not setup config files machinery
  BadZipFile: File is not a zip file
  ```

### 根因

本地手动构建时 `SKILL_ROOT` 可用，跑框架的 `patch-autotools-ohos.pl` 即可；
但 `conan create` 在**干净缓存树**执行，SKILL_ROOT 与框架脚本不可用，且
git-archive 类 tag tarball（codeload `refs/tags/...`）**不含生成版 configure**。
于是 build() 内 `autoreconf -i -f` 重新生成的 `config.guess`/`config.sub`
仍是 GNU 原版：config.guess 无法识别 `uname -s = HarmonyOS`（E007），
config.sub 的 kernel-OS 校验列表拒绝 `aarch64-unknown-linux-ohos`（E122/E268），
生成的 configure 中 `umask 077 && mktemp -d ./confXXXXXX` 在 HMDFS setgid 下
产出不可写的 `drwx--S---` 目录使 config.status 失败（E114）。

E268 陷阱：config.sub 的 `basic_os=linux-ohos` 已含子串 `linux-ohos`，若按裸
字符串判断"已打补丁"会**跳过** kernel-OS 校验列表的修改——判重必须用精确模式
`linux-ohos\*-\s*\)`。

**【R02 补充根因】** CI 干净环境预装 autoconf 但**不预装 automake/aclocal**，
`autoreconf -i -f` 直接报 `Can't exec "aclocal"`（exit 2）；且 configure.ac 用
`LT_INIT`，缺少 libtool.m4 时 automake 报 `LIBTOOL is undefined`。**陷阱**：
不能顺手把 autoconf 也 tool_requires——conan 的 autoconf 包依赖 conan perl，
其 XS 模块（Cwd.so）污染 buildenv 加载路径，使**系统** autoreconf 报
`Can't load Cwd.so: Perl_my_cxt_init: symbol not found`（同 DRAFT-6049 perl
双架构族）。CI 已有 autoconf，只补缺失的 automake/libtool。

### 修复（recipe 自包含，五步）

0. **bootstrap 工具自举**：`build_requirements()` 声明
   `self.tool_requires("automake/1.18")` + `self.tool_requires("libtool/2.5.4.1")`
   （制品仓已发布，CI 可拉取，Conan 自动注入 PATH/ACLOCAL_PATH）——解决
   aclocal/libtoolize 缺失；**禁止**同时 tool_requires autoconf（perl XS 污染）；
1. **引导**：`build()` 内若 `configure` 不存在（git-archive tarball）先
   `autoreconf -i -f`；
2. **config.guess**：内联补 `__OHOS__` LIBC 检测 + `*:HarmonyOS:*:*)` 系统识别
   分支（E007 的 config.guess 部分，输出 `aarch64-unknown-linux-ohos`）；
3. **config.sub**：内联补 `ohos-linux` triplet、OS 列表追加 `ohos*`、kernel-OS
   校验行 `linux-mlibc*- )` → `linux-mlibc*- | linux-ohos*- )`；判重用精确模式
   `linux-ohos\*-\s*\)`，**禁止**裸子串 `"linux-ohos"`；
4. **configure**：内联移除 `(umask 077 && mktemp -d "./confXXXXXX")` 的 umask
   （E114），使 config.status 临时目录可写。

codeload URL 无扩展名导致 `BadZipFile` 时，conandata.yml 追加
`filename: <name>-<ver>.tar.gz`（E276/E483）。

### 验证

htscodecs/1.6.5 三连复验（R01）：
① 裸配方 `conan-verify` G2 FAIL（cannot guess build type）；
② 仅 autoreconf+config.guess → G2 FAIL（config.sub kernel-OS 拒绝）；
③ 三合一补丁 → G2 PASS。
证据：`archives/h/htscodecs/1.6.5/reports/conan-create.log`、
`conan-verify-report.md`（2026-09-21，pc1-30）。

R02 CI 等价干净缓存（PATH 无 aclocal）四连复验（2026-09-22，pc1-30）：
① 原配方 → `Can't exec "aclocal"`（exit 2，首错复现）；
② +autoconf tool_requires → `Cwd.so Perl_my_cxt_init symbol not found`（exit 255）；
③ +automake tool_requires → `LIBTOOL undefined`（缺 libtool.m4）；
④ +automake+libtool tool_requires → conan create EXIT=0，make check 7/7 PASS，
test_package 1/1 PASS，conan-verify G1-G4 PASS。

### 适用边界 / 反例

- 适用：autotools + OHOS 的 conan 配方，尤其 source 用 codeload/git-archive
  tag tarball、无生成 configure 的库；CI 不预装 automake 的环境必须第 0 步。
- 反例：release tarball 自带生成 configure 的库，第 1 步可跳过但 2/3/4 仍需；
  CMake/Meson 库不适用；本地手动构建仍可走 `patch-autotools-ohos.pl`（SKILL_ROOT
  可用），但 CI/干净树必须用本方案。若 CI 已预装 automake/libtool，第 0 步可省。

### 关系

similar_to=E007/E122/E268/E114/E175/E276/E483/E490/
DRAFT-libuninameslist-conan-autotools-bootstrap-toolrequires/
DRAFT-6049-libnxml-0.18.5-autotools-perl-dual-arch；caused_by=conan create
clean tree（无 SKILL_ROOT）/ CI 不预装 automake；prerequisite_of=无；
conflicts_with=无。

**决定**：`new_draft`（路径 B，知识库扩展）——已验证、可跨库复用、四范围查重
未命中组合条目；R02 同步 tool_requires 自举部分后差异仍成立。
