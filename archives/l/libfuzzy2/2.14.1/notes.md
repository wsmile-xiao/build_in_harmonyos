# libfuzzy2 2.14.1 适配笔记

## 编译环境

- 构建系统: autotools（发布包自带 configure，无需 autoreconf）
- 编译日期: 2026-09-15
- 编译器: clang/clang++（OHOS SDK）
- 状态: built（待真机 conan create 验证后按结果更新）

## 编译步骤

1. `get()` 解压 `ssdeep-2.14.1.tar.gz`（strip_root）。
2. `generate()`：AutotoolsToolchain；`shared=False` 时追加
   `--enable-static --disable-shared`；OHOS 时追加
   `--build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-ohos`。
3. `build()`：umask 022 + PWD 修复；configure 的 `umask 077` 放宽为
   `umask 022`（E046 HMDFS）；`_patch_config_sub_for_ohos()` 教老
   config.sub 识别 `linux-ohos`（E072）；`_resolve_compilers()` 消毒
   profile 死链 CC/CXX（是可执行文件才信任，否则回退裸 `clang` 走
   PATH；ladspa-sdk 先例）；`configure`（显式
   `env=["conanbuild", "conanautotoolstoolchain"]` 传入工具链
   CFLAGS/LDFLAGS，命令行再显式 `CC/CXX` 前缀双保险，
   `(unset CONFIG_SHELL; …)` 包裹保持 Round-4
   中和，失败时打紧凑取证 + `which clang/ls -l` 死链证据）；OHOS下去掉生成 Makefile 中
   `ssdeep_LDFLAGS = -static`（构建树修改，非源码补丁）；`make -j1`。
4. `package()`：`make install DESTDIR=... INSTALL="<staged install-sh> -c" INSTALL_PROGRAM/... INSTALL_DATA/... MKDIR_P=...`（R10：覆盖 configure 烘焙进 Makefile 的 HMBS shim 路径，见问题 8）；删除 `*.la`；`chmod -R a+r` 保证 HMDFS 可读（chmod=0 下失败仅警告，不中断）。
5. `test_package`：clang 直编 `test_fuzzy.c -lfuzzy` 并运行（R34 真实 API）。

## 上游测试审计结论

- ssdeep 2.14.1 无自动化测试套件：无 tests/ 目录、无 TESTS/check_PROGRAMS、
  configure.ac 无测试宏；`make check` 为 automake 空目标。
- `sample.c` 为演示程序；`normal.sh` 仅重建；`test-against-old.sh` 需旧二进制，
  均非可运行套件。
- 因此 `upstream_test_in_build: false`，`test_package` 输出
  `HMBS_UPSTREAM_TEST_RESULT status:"no_tests"`（discovered/executed 均为 0）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 2017 版 config.guess 不认识 OHOS | 上游 config.guess/sub 陈旧 | 传 `--build/--host` triplet + build() 内 `_patch_config_sub_for_ohos()` 在 config.sub 的 `linux-android*` 锚点旁注入 `linux-ohos*`（zeitgeist 0002 同 pattern，运行时替换免 patch 上下文漂移；E072） |
| 2 | ssdeep CLI `-static` 在 OHOS 链接风险 | 上游 Makefile.am 硬编码全静态 | 构建树 Makefile 去掉该标志，仅影响 CLI，库不受影响 |
| 3 | HMDFS 权限/工作目录问题 | 640 权限与 getcwd 失败 | umask 022、PWD 修复、安装后 chmod（E046 家族常规手段） |
| 4 | `C compiler cannot create executables`（config.sub 修复后新暴露） | 手工 `self.run(configure)` 只套了 SHELL/TMPDIR 的 fresh Environment，从未 source 工具链脚本，configure 拿裸 clang、无 sysroot/target 标志 | configure/make/install 三处 `self.run` 显式传 `env=["conanbuild", "conanautotoolstoolchain"]`；`(unset CONFIG_SHELL; …)` 包裹保留（source 之后执行，中和优先级不变） |
| 5 | 同错第 3 次：补传工具链环境后仍 `works... no`，且失败取证 `tail -60` 只打出 make 变量表、无错误行 | 取证机制本身失效（config.log 尾部全是 `am__*=''` 噪音，真错误在 compiler-check 段）；兼 `_writable_tmpdir()` 未覆盖 HMBS 新能力键、未排除裸 `/tmp`、未做可写探针 | 换取证路线：失败分支改打紧凑证据（CC/CFLAGS/LDFLAGS/TMPDIR 回显 + `checking whether the C compiler works` 段 12 行 + `error|fatal|cannot|not found|Read-only|temporary file|while loading` 30 行）；`_writable_tmpdir()` 升级为 HMBS 优先级（path 型 HMBS_AUTOCONF_MKTEMP_FALLBACK > HMBS_TMPDIR > TMPDIR/TMP/TEMP，排除裸 `/tmp`，逐个 makedirs+写探针，不可用回退 build-folder/tmp；courier-unicode 先例） |
| 6 | 同错第 4 次：紧凑取证揭示 `CC=/data/service/hnp/bin/clang` 但 `configure: /data/service/hnp/bin/clang: inaccessible or not found`（exit 127） | 上轮 Round-5 补传工具链环境把 profile 死链 CC 也一起坐实：该绝对路径在本预检设备上是死链接/不可执行，裸 `clang` 经 conanbuild.sh 的 PATH 本可解析到可用编译器，但工具链脚本导出的死链 CC 优先导致 compiler-check 段整体失败；TMPDIR/取证只改善诊断未触及该死链 | 换实现路线为编译器消毒（ladspa-sdk `_compiler_paths` 先例）：新增 `_resolve_compilers()` 仅当 conf 绝对路径 `isfile+X_OK` 时才信任，否则回退裸 `clang`/`clang++` 走 PATH；`generate()` 经 `tc.generate(env)` 发布消毒后 CC/CXX，`build()`/`package()` 的 configure/make/install 命令行再显式 `CC=".." CXX=".."` 前缀双保险；test_package 同理消毒；失败取证追加 `which clang` + `ls -l /data/service/hnp/bin/clang` 以便下轮证伪 |
| 7 | `source()` 下载 `ssdeep-2.14.1.tar.gz` 报 `HTTPSConnectionPool(host='release-assets.githubusercontent.com'): Read timed out`（重试 5 秒后成功，抖动但真实超时） | 真机到 GitHub release 资产直连不稳定，单 URL 无回退；按任务守则“源码包下载超时”例外必须加镜像 | `conandata.yml` 的 `url` 由单值改为有序列表：`https://gh-proxy.com/https://github.com/...`（`ci/conan/build_and_test.sh` 已维护的 GitHub 镜像映射）优先、官方 URL 兜底；同一归档，`sha256` 不变；conan `get()` 逐个尝试 |
| 8 | `package()` 的 `make install` 在 `install-libLTLIBRARIES` 失败：`libtool: install: <runtime>/bin/install -c .libs/libfuzzy.a <pkg>/p//lib/libfuzzy.a` 看似成功，紧接着 `chmod 644 <pkg>/p//lib/libfuzzy.a` 报 `No such file or directory`（Error 1/2） | configure 把 HMBS 注入的 `.../runtime/<pkg>/bin/install -c` shim 检测为 BSD-compatible INSTALL 并烘焙进 Makefile；该 shim 对 libtool 的 `install -c src destfile`（单文件到文件）调用静默无安装（退出码仍 0），文件实际不存在，后续 `chmod` 遂以 ENOENT 失败（E174/E108 同类：OHOS 上默认 install 不可用） | 换实现路线为自带 installer 覆盖（cyrus-sasl-login `_ohos_make_vars` 先例，非上一轮“只加未调函数”的重复）：新增 `_install_sh_for_ohos()` 把包内自带 `install-sh` 拷贝到 tmpdir、shebang 重写为设备 shell（`_device_shell()`，纯 Python，无需 chmod 持久性）；`package()` 的 `make install` 命令行追加 `INSTALL/INSTALL_PROGRAM/INSTALL_DATA/INSTALL_SCRIPT/MKDIR_P` 覆盖（make 命令行变量优先于 Makefile 烘焙值），libtool 经 `$(INSTALL)` 用到真实 installer；找不到 install-sh 时回退默认行为 |

## 源码修改

无补丁（R6）。`conandata.yml patches: {}`。

## 依赖版本

- 运行时依赖：无。
- 构建：OHOS profile 自带 clang 15 + Autotools（发布包自带 configure，无需 tool_requires）。

## 验证结果

待 HMBS 真机预检（conan create）回填：`test_fuzzy` 4 断言与 `no_tests` 标记。
本地未运行 conan（按任务守则，仅真机验证）。

## 交付物

- 库：`lib/libfuzzy.a`（默认静态；`shared=True` 时为 `.so.2` 系列）
- 头文件：`include/fuzzy.h`、`include/edit_dist.h`
- 附带：`bin/ssdeep`（上游默认安装产物，非本包主要交付）

## 注意事项

- `cpp_info.libs = ["fuzzy"]`（实际库名，非 `libfuzzy2`）。
- 纯库包，无 `commands.json`（L0k 仅对 application/bindirs 触发）。
- Debian 包名 `libfuzzy2` 对应 SONAME `libfuzzy.so.2`（version-info 3:0:1）。
