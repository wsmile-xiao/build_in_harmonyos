# aircrack 1.7 适配笔记

## 编译环境
- 构建系统: autotools（官方 release tarball 为 git 快照，不含 configure）
- 编译日期: 2026-08-20
- 编译器: clang/clang++
- 依赖: openssl/3.5.6.1, zlib/1.3.1.1（conan requires，均与制品仓预编译二进制对齐）
- 构建工具: automake/1.18, libtool/2.5.4（conan tool_requires）

## 编译步骤

```bash
autoreconf -fiv          # 生成 configure（tarball 只有 configure.ac）
./configure --enable-static --disable-shared --disable-libnl
make -j1
make check               # 上游官方测试（30 个脚本）
make install
```

## 真机失败与修复（2026-08-20 聚焦轮）

### 现象（本轮，compile 阶段）
真机预检 conan create 失败：
```
ERROR: openssl/3.5.6: Invalid configuration: Unsupported configuration (OHOS/armv8/clang).
Please open an issue at https://github.com/conan-io/conan-center-index.
Alternatively, set the CONAN_OPENSSL_CONFIGURATION environment variable into your conan profile.
```
日志先出现 `openssl/3.5.6: Copying sources to build folder` / `Building your package`，
即 openssl 被从源码构建，而非命中 ohpcd 制品仓预编译二进制。

### 根因
1. 旧配方把 zlib 钉在 **1.3.1**；ohpcd 制品仓预编译二进制（openssl/3.5.6 等）
   基于 **zlib/1.3.1.1** 构建（同仓库 abiword-plugin-eml/curl/cpr 先例）。
2. openssl 配方要求 `zlib/[>=1.2.11 <2]`，被 aircrack 的 zlib/1.3.1 钉住后，
   openssl 的 package_id（含 zlib 依赖版本）与制品仓二进制不匹配 → conan 转源码构建。
3. CCI openssl 配方 `_ancestor_target` 的 target 表无 OHOS/armv8/clang 条目，
   validate 时直接 `ConanInvalidConfiguration`，compile 阶段即失败。

### 解决方案
- `requirements()`：`zlib/1.3.1` → `zlib/1.3.1.1`，与制品仓 openssl/3.5.6
  预编译二进制对齐，openssl 直接命中二进制，不再源码构建、不再触发 OHOS 拒绝。
- manifest.yaml dependencies 同步改为 zlib/1.3.1.1。

### 二次失败（同指纹，2026-08-20 第 2 轮）
**前次修复无效**：zlib/1.3.1.1 已在真机生效（日志确认 `zlib/1.3.1.1: Not found
in local cache, looking in remotes...` 并成功解析），但 openssl/3.5.6 仍走
`Copying sources to build folder` 源码构建，同样报
`ERROR: openssl/3.5.6: Invalid configuration: Unsupported configuration
(OHOS/armv8/clang).`。即制品仓**没有 openssl/3.5.6 的 OHOS armv8 预编译二进制**，
zlib 版本对齐无法改变这一点。

### 二次根因
ohpcd 制品仓实际发布的 openssl 版本是 **3.5.6.1** 而非 3.5.6：
- curl/8.15.0/notes.md 实证：真机从 ohpcd 下载
  `openssl/3.5.6.1#d871951ad035e2c4eecb6112af441801` 与 `zlib/1.3.1.1#9a23e7d51311d0440b6e4d36cf44e4d9`；
- 仓库内已入库验证的 openssl 依赖方（curl/8.15.0、cpr/1.14.2、ice/3.8.2、
  icecast/2.4.4、alicloud/1.3.4、chibicc、fluent-bit 等）全部 requires
  `openssl/3.5.6.1`；
- 而 uses openssl/3.5.6 的配方（abuild、h2o、hydra、ffmpeg 等）多处于
  pending/未过真机状态。

### 二次解决方案（换策略）
- `requirements()`：`openssl/3.5.6` → `openssl/3.5.6.1`，与制品仓实际发布的
  版本对齐，conan 直接命中预编译二进制，不再源码构建、不再触发 CCI 配方
  `_ancestor_target` 对 OHOS 的 ConanInvalidConfiguration。
- manifest.yaml dependencies 同步改为 openssl/3.5.6.1。
- zlib/1.3.1.1 保持上轮修改（与制品仓一致）。

### 现象
真机预检 compile 阶段失败：
```
Could not auto-detect 'libtoolize'; please install or specify the 'LIBTOOLIZE' environment variable.
ERROR: aircrack/1.7: Error in build() method, line 45
    self.run("./autogen.sh", cwd=self.source_folder)
```
另有 hmbs 平台诊断 [readonly_tmp]（`can't create temporary file /tmp/shyj9ocj.tmp:
Read-only file system`）。

### 根因
1. 旧配方在 configure 不存在时执行 `./autogen.sh`。上游 autogen.sh 会逐个探测
   libtoolize → aclocal → autoconf → autoheader → automake，真机全部缺失，
   第一个探测（libtoolize）即 `missing_tool` 报错 exit 1。
2. 真机 /tmp 只读；autoconf 生成的 configure/config.status 用
   `./confXXXXXX` + `umask 077` 建临时目录，在 HMDFS/只读 /tmp 上失败。

### 解决方案（与仓库内 aircrack-ng/1.7 先例一致，已入库验证）
1. `build_requirements` 增加 `tool_requires("automake/1.18")` +
   `tool_requires("libtool/2.5.4")`，把 autotools 链带进真机构建环境；
2. 放弃 autogen.sh，改跑 `autoreconf -fiv`（一条命令完成
   aclocal/autoheader/automake/autoconf，且不逐个探测工具是否存在）；
3. autoreconf 后对生成的 configure 打临时目录补丁：
   `./confXXXXXX` + umask 077 → `${TMPDIR:-/tmp}/confXXXXXX`（hmbs 注入
   可写 TMPDIR），去掉 umask 077；
4. config.guess/config.sub 补 HarmonyOS 识别（aarch64-unknown-linux-ohos）；
5. 源码补丁 0001/0002：lib/osdep/linux.c、linux_tap.c 的
   sockaddr_storage 重复定义，用 `_UAPI_LINUX_SOCKET_H` 守卫修复；
6. 上游测试接入：`make check`（test/Makefile.inc 注册 30 个测试脚本：
   test-aircrack-ng-000x 23 个、test-airdecap-ng-000x 6 个、
   test-wpaclean-000x 2 个、test-alltools 1 个、test-hex_string_to_array 1 个；
   EXPECT/SQLITE3 条件用例在真机缺依赖时自动不注册），解析 automake
   PASS/FAIL/SKIP 行输出 `HMBS_UPSTREAM_TEST_RESULT`；
7. test_package：aircrack-ng --help + WPA2 握手破解（test.sh，
   复用上游 test-aircrack-ng-0001.sh 的 12345678 用例），输出
   `HMBS_TEST_PACKAGE_RESULT`（discovered=2）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | autogen.sh 报 libtoolize 缺失 | 真机无 autotools 工具链 | tool_requires automake/1.18 + libtool/2.5.4，改跑 autoreconf -fiv |
| 2 | /tmp 只读、configure 临时目录失败 | autoconf 模板写 ./confXXXXXX + umask 077 | 生成后补丁改 ${TMPDIR:-/tmp} + 去 umask（hmbs 注入 TMPDIR） |
| 3 | sockaddr_storage 重复定义 | linux/socket.h 与系统头冲突 | 0001/0002 补丁 _UAPI_LINUX_SOCKET_H 守卫 |
| 4 | libnl 依赖 | OHOS 无 libnl | configure 加 --disable-libnl（AC_ARG_ENABLE 形式） |

## 源码修改

- `patches/0001-lib-osdep-linux.c.patch`、`patches/0002-lib-osdep-linux_tap.c.patch`
  （sockaddr_storage 重复定义修复，POSIX 兼容守卫，无 __OHOS__ 特判）。

## 验证结果

- 真机预检：conan create（compile + make check 上游测试）+ test_package 全链路，
  HMBS_UPSTREAM_TEST_RESULT / HMBS_TEST_PACKAGE_RESULT 标记由真机实际测试输出产生。

## 注意事项

- aircrack-ng 无线注入/监听类工具（aireplay-ng、airodump-ng、airmon-ng 等）依赖
  无线网卡驱动、raw socket 与 root 权限，在 HarmonyOS PC 上功能受限；本适配保证
  工具可编译、可运行（破解/解密类离线功能可用），抓包注入类功能取决于平台驱动支持。
- integration 测试（`make integration`，aireplay/airbase/airodump 注入类）需要
  root + 真实无线网卡，未注册进 make check，不纳入执行。
- make check 中依赖 expect/sqlite3 的条件用例在真机缺依赖时由 configure 自动排除。

## 三次失败（同指纹，2026-08-20 第 3 轮）——HMDFS getcwd 不可达

### 现象（compile 阶段）
```
shell-init: error retrieving current directory: getcwd: cannot access parent directories
job-working-directory: error retrieving current directory: ...
pwd: error retrieving current directory: getcwd: cannot access parent directories
configure: error: working directory cannot be determined
ERROR: aircrack/1.7: Error in build() method, line 200
    autotools.configure()
```
（此前两轮均为限流暂停，无实际代码修改；本指纹首次真正修复。）

### 根因
HMDFS 对 conan 构建树父目录不提供 getcwd()（平台诊断 [shell_getcwd]）。
autoreconf 生成的 configure 启动时执行 `pwd` 判定工作目录，getcwd 失败
导致 `ac_pwd` 为空 → as_fn_error 退出。配方此前既未预置 PWD，也未改写
configure 判定（与 adcli/adms/libgsf/aribb24 已入库成功配方对比缺失项）。

### 解决方案（复用仓库已验证模式，适配本配方）
1. build() 开头预置 `os.environ["PWD"] = self.build_folder`：bash 的 pwd
   内建在 getcwd 失败时回退逻辑路径 $PWD（adcli 单靠此即通过）；
2. 新增 `_patch_configure_pwd()`：autoreconf 后改写生成的 configure——
   2.71+ 模式 `ac_pwd=\`pwd\` && test -n "$ac_pwd" &&` 改为
   `ac_pwd=\`pwd\` 2>/dev/null || ac_pwd=$PWD` + 保留 `test -n "$ac_pwd" &&`；
   2.69 模式 `if (pwd) >/dev/null 2>&1 && test -n "\`pwd\`"` 改为
   `if (pwd) >/dev/null 2>&1 || test -n "$PWD"`；两模式均未命中时仅告警，
   依赖 PWD 预置兜底；
3. 临时目录/umask 适配沿用既有 `_patch_configure_tmpdir()`（无需重复处理）。

## 四次失败（同指纹，2026-08-20 第 4 轮）——install shim 拒绝 `-m`（package 阶段）

### 现象（compile 阶段，package() 内 autotools.install() 失败）
```
/storage/Users/currentUser/usr/local/bin/mkdir -p '.../p//share/man/man1'
/storage/Users/currentUser/.../runtime/aircrack-1.7/bin/install -c -m 644 aircrack-ng.1 airdecap-ng.1 packetforge-ng.1 ivstools.1 kstats.1 makeivs-ng.1 airdecloak-ng.1 buddy-ng.1 '.../p//share/man/man1'
make[2]: *** [Makefile:642: install-man1] Error 64
ERROR: aircrack/1.7: Error in package() method, line 304
	autotools.install()
```
上游测试本轮已全绿（make check 38/38，`HMBS_UPSTREAM_TEST_RESULT` passed），
编译与测试均通过，仅打包安装阶段失败。

### 根因
1. hmbs 平台能力报告 `install_shim=true, chmod=0, hardlink=0`：目标文件系统
   不支持 chmod，hmbs 提供 install shim（runtime/aircrack-1.7/bin/install）。
2. configure 的 AC_PROG_INSTALL 把该 shim 绝对路径写死进 Makefile：
   `INSTALL='.../bin/install -c'`、`INSTALL_DATA='${INSTALL} -m 644'`。
3. 上游 top-level Makefile.am 的自定义 man 安装规则一次性安装 8 个 man 页：
   `install -c -m 644 <8 files> <mandir>/man1`。`-m 644` 需要 chmod，
   目标文件系统不支持 → shim 以 EX_USAGE(64) 拒绝，install-man1 失败。
   （PATH 前置自己的 install 无效：Makefile 里是硬编码绝对路径，必须覆盖
   make 命令行变量。）

### 解决方案
1. conanfile.py 新增配方内 install shim（`_INSTALL_SHIM`，POSIX sh）：
   - 忽略模式位（`-m <mode>`/`-m644`/`--mode=` 直接丢弃，chmod 不可用）；
   - `-d` → `mkdir -p`；`-D` → 建目标父目录；
   - 多文件安装（≥3 参）自动补建目标目录，`cp -f` 复制；
   - 单文件 `cp -f src dest`（cp 保留源文件权限，二进制执行位不丢失）。
2. package() 不再用 `autotools.install()`，改为：
   `make install DESTDIR=<pkg> INSTALL="sh <shim> -c" INSTALL_DATA='$(INSTALL)'`
   （env="conanbuild"，cwd=build_folder，与 Autotools.install 等价）；
   INSTALL/INSTALL_DATA 覆盖经 MAKEFLAGS 传播到各子 Makefile，
   所有 `$(INSTALL)`/`$(INSTALL_DATA)` 调用统一走配方内 shim。
3. 本机 bash 实测 6 种调用形态全部通过（man 多文件、二进制保留执行位、
   -d、单文件、-D、复制进目录）。

### 边界与注意
- shim 只复制不设模式：二进制由 clang 生成时已带执行位，cp 保留之；
  数据文件 644 语义由 umask/源文件权限决定，目标文件系统本就不支持 chmod，
  无影响。
- 若后续上游引入 `install -s`（strip）、`-o/-g`（属主）等参数，shim 均已
  忽略/吞参处理，不会中断安装（strip 不做，包体积略大，可接受）。
- aircrack-ng/1.7 先例（2026-08-09 入库）当时用原生 autotools.install()
  通过，说明 install shim 对 `-m` 的拒绝是平台能力演进后的新行为。

## 五次失败（同指纹，2026-08-20 第 5 轮）——libtool 拒绝多词 INSTALL（package 阶段）

### 现象（compile 阶段，package() 内 make install 失败）
上一轮修复（`INSTALL="sh <shim> -c"`）让 man 页安装通过（install-man1 不再报错），
但 libtool 安装 .la 库时失败：
```
libtool: install: sh /storage/.../b/build-release/install-shim.sh /storage/.../p//lib/install-shim.sh
libtool: install: sh -c /storage/.../p//lib/-c
sh: /storage/.../p//lib/-c: inaccessible or not found
make[2]: *** [Makefile:2765: install-libLTLIBRARIES] Error 127
ERROR: aircrack/1.7: Error in package() method, line 369
```

### 根因（libtool 2.5.4 ltmain.sh func_mode_install 实读确认）
1. aircrack 的 lib_LTLIBRARIES（lib/Makefile.inc）为
   `libaircrack-ce-wpa.la`（aarch64+NEON 另加 arm-neon 变体），
   安装走 `$(LIBTOOL) --mode=install $(INSTALL) <file> <dest>`。
2. ltmain.sh 把 `--mode=install` 后**第一个参数**当作安装程序：
   - 特判分支（`if test "$SHELL" = "$nonopt" || test /bin/sh = "$nonopt"`）
     只接受首词为 $SHELL 或字面 /bin/sh 的 "sh <脚本> [选项]" 形式；
   - 裸 `sh`（首词≠/bin/sh）走普通分支：install_prog="sh"，
     **shim 路径、`-c`、.la 文件全部被当作待安装文件列表**（files），
     最后一个参数当 dest 目录。
3. 于是 libtool 逐个"安装"这些假文件：
   - `sh <shim> <dest>/lib/install-shim.sh`（shim 被当成文件安装，无操作）；
   - `sh -c <dest>/lib/-c`（把 -c 当文件安装，sh 执行不存在的
     `<dest>/lib/-c` → "inaccessible or not found" → exit 127）。

### 解决方案
1. package() 的 INSTALL 覆盖从 `"sh <shim> -c"` 改为 `"/bin/sh <shim>"`
   （去掉 -c，首词用字面 /bin/sh），命中 ltmain.sh 特判分支，
   install_prog 正确解析为 `/bin/sh <shim>`，files/dest 正常；
2. 本地用真实 libtool 2.5.4 ltmain.sh（注入 macro_version/macro_revision/
   build_old_libs 绕过版本与配置自检）复现验证：
   - 旧 INSTALL：逐字复现 `sh -c <dest>/-c` → exit 127（与真机日志一致）；
   - 新 INSTALL：`ltmain.sh: install: /bin/sh <shim> <src>.lai <dest>.la` 与
     `<src>.a <dest>.a` 均成功，exit 0，产物内容校验通过；
   - 普通 make 规则形态（man 多文件 `-m 644`、`-d`、单文件）全部通过。

### 边界与注意
- INSTALL 首词必须与 ltmain.sh 特判严格一致：$SHELL（真机注入 /bin/sh）
  或字面 /bin/sh；后续不带 `-c` 更简单（shim 本就忽略该参数）。
- 只要 libtool 参与安装（--mode=install），多词 INSTALL 都是雷区；
  普通 make 规则（非 libtool）则不受此限制。
- 真机错误 127 的完整链条：install_prog 误解析 → 把 shim/-c/.la 当文件 →
  `sh -c <dest>/lib/-c` 找不到可执行文件；同指纹勿再回到裸 sh 方案。
