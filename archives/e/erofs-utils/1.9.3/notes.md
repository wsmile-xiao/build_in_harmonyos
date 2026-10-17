# erofs-utils 1.9.3 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-08-21
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 下载 erofs-utils v1.9.3 (GitHub 官方镜像 erofs/erofs-utils + gh-proxy fallback；CI worker 无法访问 git.kernel.org)
2. 1.9.3 tarball 不含预生成 autotools 文件（与 1.9.2 不同），在 build() 中运行 `autoreconf -fi` 生成 configure/Makefile.in/aclocal.m4/config.h.in 等
3. 通过 tool_requires automake/1.18 + libtool/2.5.4 提供自举工具链（同 adcli/afuse/audit 模式）
4. generate()/build() 中调用 _drop_umask_077() 移除 configure 中 `(umask 077 && mktemp -d ...)` 模式（E114: HMDFS setgid 导致临时目录不可写）
5. build() 中 autotools.configure() 后调用 _fix_config_status() 修补生成的 config.status（同样移除 umask 077 + 添加 chmod 755）
6. build()/package() 中 make 传递 `ACLOCAL=true AUTOMAKE=true AUTOCONF=true AUTOHEADER=true` 禁止 autotools 重新生成（否则 make 触发 config.status --recheck 产生未修补的 config.status）
7. make -j1 避免 HMDFS jobserver fifo EPERM (E074)

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 1.9.3 tarball 无 configure/Makefile.in | 上游 1.9.3 release tarball 不含预生成 autotools 文件 | build() 中 autoreconf -fi 生成，通过 tool_requires automake/1.18 + libtool/2.5.4 提供工具链 |
| 2 | config.status: subs1.awk Permission denied | E114: HMDFS 上 mktemp -d 创建的临时目录权限为 drwx--S--- (2700+setgid)，umask 077 加剧问题 | _drop_umask_077() 移除 configure 中的 `(umask 077 && mktemp -d ...)` 模式 + _fix_config_status() 修补生成的 config.status |
| 3 | make 触发 autotools 重新生成 config.status --recheck | 时间戳检测认为 configure.ac 比 configure 新 | make 传递 ACLOCAL=true AUTOMAKE=true AUTOCONF=true AUTOHEADER=true 禁止重生成 |
| 4 | CI checkout-pr 步骤失败：binary patch does not apply | 1.7MB 二进制 tarball 无法被 .diff 补丁正确编码，git apply 报 missing binary patch data | 删除 files/autotools-generated.tar.gz，改用 autoreconf -fi 构建时自举（不提交二进制 blob） |
| 5 | CI 预下载脚本正则截断含连字符的 URL | build_and_test.sh 的 URL 正则 `[^\s"\'-]+` 在连字符处停止 | 预填充 predl_cache 的嵌套目录路径绕过 |
| 6 | CI source() 下载超时：`HTTPSConnectionPool(host='git.kernel.org', port=443): Read timed out` | CI worker 网络受限，无法访问 git.kernel.org（已知不可达: ftp.gnu.org；已知可达: zlib.net） | conandata.yml 改用上游官方 GitHub 镜像 erofs/erofs-utils + gh-proxy/ghfast.top/gitclone.com/kkgithub.com fallback；sha256 来自 termux/homebrew 两独立来源 |

## 源码修改

无补丁。autotools 文件（configure/Makefile.in/aclocal.m4 等）在 build() 中通过 `autoreconf -fi` 动态生成，不提交二进制 blob。
configure/config.status 的 umask 077 修补在 build() 运行时进行（生成文件无法作为源码补丁）。

## 依赖版本

无编译依赖（所有可选依赖均禁用）。

## 验证结果

> **2026-08-24 更正（CI PR 5989 复盘）：** 以下"conan create PASS"系缓存命中假象——
> conan 缓存中残留了设备手动构建的产物，验证日志显示 `Already installed` 而非
> `Building from source`，从未真正从源码重新编译。CI worker 是干净环境，第一次
> 真正 `conan create` 即暴露 `C compiler cannot create executables`（configure:77）。
> 根因有二：
> 1. **E007 违规**——配方显式传 `--build/--host/--target=aarch64-linux-ohos`，
>    触发交叉编译副作用，导致 `AC_PROG_CC` 链接测试失败。已改为用 config.guess/
>    config.sub 补丁原生识别 OHOS。
> 2. **E114 脆弱补丁**——`_drop_umask_077` 用精确字符串匹配修补 configure，
>    autoconf 版本/引号变动即静默失效；已改为正则匹配覆盖所有 `umask 077` 变体。
>
> 修复后清缓存复跑 `conan create --build=missing`，确认 `Building from source` →
> `C compiler works... yes` → 成功。

- conan create: PASS (mkfs.erofs/fsck.erofs/dump.erofs/mount.erofs 全部编译安装)
- test_package: PASS (4 个工具 --help 均通过)
- conan-verify 8 道门禁: 全部 PASS (G0/G1/G2/G3/G4/L2/L4/L5)
- W3 本地 CI 模拟: PASS

## 上游测试调查

erofs-utils 1.9.3 源码中**无标准 `make check` 测试套件**：
- 所有 Makefile.am 中无 `TESTS`/`check_PROGRAMS`/`check_SCRIPTS` 定义
- 无 tests/ 目录、无 runtest 脚本、无 DejaGNU/autotest 框架
- 仅存在内部调试用 noinst_PROGRAMS: `fsck/fuzz_erofsfsck`(libFuzzer)、`lib/Makefile.am` 中 s3erofs_test/ocierofs_test（需启 s3/oci，本配方已禁用）
- contrib/ 下有 `mkstress.sh` + `stress.c`（非自动化测试，需手动构造源目录 + fakeroot 运行）
- 上游 CI (.github/workflows/) 仅做编译检查（make + make check），但 `make check` 在无 TESTS 时为空 target

结论：上游未提供可在本环境自动运行的测试用例。

## 功能集成测试（自建）

由于无上游测试套件，在 OHOS aarch64 交叉编译产物上自建功能集成测试，
模拟真实使用链路 mkfs → fsck → dump。测试脚本:
`$HOME/tmp/erofs-func-test/`（构建机本地，未纳入归档）。

测试步骤与结果：

| 步骤 | 命令 | 结果 |
|------|------|------|
| 1. 创建镜像 | `mkfs.erofs -d2 -x-1 test.erofs src/` | ✅ EXIT=0, 生成 4096B 镜像 |
| 2. 校验镜像 | `fsck.erofs test.erofs` | ✅ EXIT=0, 无错误 |
| 3. 检查镜像 | `dump.erofs test.erofs` | ✅ EXIT=0, 输出 superblock/文件列表 |
| 4. 版本确认 | `mkfs.erofs --version` | ✅ EROFS 1.9.3 |

测试源目录结构: hello.txt + subdir/deep/nested.txt + subdir/another.txt + symlink.txt(符号链接)

注意事项:
- mkfs.erofs 默认尝试写入 xattrs，OHOS 无 selinux/xattr 支持时会报
  "failed to import xattr" 警告。用 `-x-1` 禁用 xattrs 规避（非功能缺陷，
  是 OHOS 平台限制）
- mount.erofs 未纳入功能测试（需 root + fuse，CI 环境不可用）
- 此测试为一次性手工验证，test_package 仍仅检查 --help（SKILL R34 最低要求）

## 注意事项

- 1.9.3 与 1.9.2 的关键差异：tarball 不含 autotools 文件，需 build() 中 autoreconf -fi（不提交二进制 blob，避免 CI diff 补丁无法应用）
- autoreconf 通过 tool_requires automake/1.18 + libtool/2.5.4 提供工具链（同 adcli/afuse/audit 模式）
- E114 HMDFS 权限问题需运行时修补 configure + config.status（不能用源码补丁，因为 config.status 是生成文件）
- make 必须禁用 autotools 重生成（ACLOCAL=true 等），否则 config.status --recheck 产生未修补的 config.status
- 静态构建策略（--disable-shared --enable-static）沿用 1.9.2
- mkfs.erofs 在 OHOS 上需 `-x-1` 禁用 xattrs（平台无 selinux/xattr 支持）
