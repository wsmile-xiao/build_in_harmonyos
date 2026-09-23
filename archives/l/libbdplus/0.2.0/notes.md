# libbdplus 0.2.0 适配笔记

## 编译环境

- 构建系统: autotools（configure + make，in-source 构建，2022 年 autoconf 生成物）
- 编译日期: 2026-09-16
- 编译器: clang/clang++（待 HMBS 真机预检确认版本）
- 状态: built（配方完成，待真机验证；验证通过前不标 published）
- 源码: https://download.videolan.org/pub/videolan/libbdplus/0.2.0/libbdplus-0.2.0.tar.bz2
- 源码 SHA256: b93eea3eaef33d6e9155d2c34b068c505493aa5a4936e63274f4342ab0f40a58
  （本地下载后实算核对，与 VideoLAN 官方 mirrorlist 该文件哈希逐字一致）
- 上游 Git: https://code.videolan.org/videolan/libbdplus
- 许可证: LGPL-2.1-or-later（COPYING 为 LGPL 2.1 文本，bdplus.h 头声明“2.1 或更高”）

## 定位

VideoLAN 的 BD+ 研究库：实现 BD+ 系统规范，含 BD+ 虚拟机（src/libbdplus/bdsvm/）、
转换表逻辑与 POSIX/Win32/Darwin 三套文件层。libbluray 通过它做 BD+ 内容解密。
主依赖是 libgcrypt（全部密码学原语）+ libgpg-error；libaacs 仅是 noinst 示例
`bdplus_test` 的可选辅助（`--without-libaacs` 时该示例以降级形态照常构建，
且两个示例都不安装）。

## 编译步骤

标准 autotools 流程（conanfile.py 等价逻辑）：

```bash
# 1) build 内生成 libgcrypt-config / gpg-error-config wrapper 并前置到 PATH
./configure \
  --prefix=/ --libdir=/lib --includedir=/include \
  --build=x86_64-pc-linux-gnu --host=aarch64-unknown-linux-gnu \
  --disable-dependency-tracking \
  --without-libaacs \
  --enable-shared --disable-static
make -j1
make install DESTDIR=<package>
```

构建期另做一件 OHOS 适配：`configure` 内 2 处 `umask 077` 改写为 `umask 022`
（E129/E011，ezstream/libgcrypt/cyrus 已验证做法；HMDFS 上 077 产生的
`drwx--S---` 暂存目录会导致 config.status 写 subs1.awk 报 Permission denied），
外加 `os.umask(0o022)` 双保险。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 硬失败 `libgcrypt not found on system`（预期） | configure.ac 用 AC_PATH_PROG 找 `libgcrypt-config` 脚本，而 libgcrypt ≥ 1.10 不再提供该脚本（clamz/0.5 已记录） | build 内按依赖 cpp_info 实际路径生成 `libgcrypt-config` wrapper，只回答 configure 实际用的 `--cflags/--libs`（另带 `--version/--prefix` 常规探针）；gpg-error 同理（gpgme config-overrides 同构） |
| 2 | 自带 config.guess（2018 版）无 ohos 识别（预期） | `uname -s` 在真机返回非 Linux 字符串时 guess 失败或输出不可 canonicalize 的三元组 | 初版用相等 `--build/--host` 走 E007 fallback（原生构建）；该路线已在两轮预检中证伪（见 #8），现改真交叉模式，config.guess 仍靠显式双三元组绕过 |
| 3 | libaacs 可选依赖无处可取 | 仓库内 libaacs 只有 hints、无可消费配方；且它只服务于 noinst 示例 | `--without-libaacs`（configure 官方选项；示例以降级形态构建，不进安装产物） |
| 4 | 上游无自动化测试套件 | 顶层 Makefile.am 无 TESTS/check_PROGRAMS，无 tests 目录；src/examples 只有两个手写 noinst 程序（bdplus_test 需真实 BD 碟片+密钥才能跑） | 按 no_tests 口径申报（MANIFEST.yml 完整审计 + 双 marker），test_package 提供 4 项消费者验证 |
| 5 | 依赖版本选型 | 多个 libgcrypt/libgpg-error 版本并存 | libgcrypt/1.11.0 + libgpg-error/1.55：与 gcr-base“远程已发布二进制”实证一致，且与 libgcrypt/1.11.0 自身 `requires libgpg-error/1.55` 同值，无版本冲突 |
| 6 | 真机 compile 报 `/bin/sh: Out of memory`（stderr 仅此一行） | 受限真机 fork/exec 时内存不足；本包虽小，默认 -O2/-g 会放大 cc1 常驻与目标体积 | generate() 追加 `extra_cflags -O1 -g0`（最后生效，不改 API/ABI），build 保持 `-j1` 禁止提速 |
| 7 | 真机 compile 首项 AC_PROG_CC 即报 `cannot run C compiled programs`，伴随 `/tmp/shtxnwv5.tmp: Read-only file system`（2026-09-17 预检） | 真机 /tmp 为只读 erofs，且 HMBS 默认 TMPDIR 落在 HMDFS 上 conftest 写 dummy.c 报 Permission denied；configure 首个编译运行探针即失败，与三元组无关 | build() 开头创建 `build_folder/_tmp` 并覆盖 `TMPDIR/TMP/TEMP`（libgcrypt/1.11.0 同机实证），仅替换临时文件根目录，不删测试 |
| 8 | 上述 TMPDIR 重定向后预检仍在同一位置失败（2026-09-17 第二轮，configure 本身经实测几乎无 `/tmp` 硬编码，1 处仅为注释） | 相等 `--build/--host` 强制 `cross_compiling=no`，configure 必须 EXECUTE conftest；日志显示编译本身已产出 `a.out`，死在运行环节。根因在执行环节（沙箱不可执行/HMDFS 权限/签名/安全弹窗其一），与编译无关 | 改走真交叉模式：`--build=x86_64-pc-linux-gnu` + `--host=aarch64-unknown-linux-gnu`（build 别名仅作交叉判定用，本包无 build-time 工具）。安全前提已审计：configure.ac 与生成 configure 中 `AC_RUN_IFELSE/AC_TRY_RUN` 计数均为 0，`AC_FUNC_STRERROR_R` 定义的宏无源文件使用，`SYS` 仅分 win32/darwin；其余探针全是编译/链接型，交叉模式下照常执行。TMPDIR 重定向保留（编译器临时文件仍需要） |
| 9 | 真交叉后 configure 一次通过，`make` 链 `libbdplus.la` 时报 `libtool: error: '//lib/libgpg-error.la' is not a valid libtool archive`（2026-09-17 第三轮） | Conan 缓存的 `libgcrypt.la/libgpg-error.la` 残留不可重定位的 `libdir='//lib'` 元数据；libtool 优先用可见 `.la` 而非同目录 `.so`，顺着陈旧路径读 `//lib/*.la` 即失败（E236，`library was moved` 同征）。即 notes 待观察项 1 的命中 | 按 E236 修：generate() 内把两依赖的 `lib*.so*`/`lib*.a` 以普通文件拷贝（symlink 解析掉）实体化到 `build_folder/bdplus-private-libs`（无 `.la`），wrapper 的 `--libs` 改答 `-L<私有目录> -l...` 并保底补齐 `-l` 所需的无版本 `lib*.so` 别名；Conan 缓存不动，最终包照常删 `.la` |
| 10 | 上述私有目录生效后**同一错误原样复现**（2026-09-17 第四轮：`was moved` + `sed: can't read //lib/libgpg-error.la` 逐字相同） | 上一方案假设“wrapper `--libs` 的 `-L<私有>` 足以让 libtool 避开毒 `.la`”被证伪：`AutotoolsDeps` 仍把缓存 `-L` 注入 `LDFLAGS`，而 automake 把 `AM_LDFLAGS/LDFLAGS` 排在 wrapper `LIBS/LIBADD` 之前，libtool 按 `-L` 顺序逐目录先探 `.la` 后探 `.a`（ezstream 1.0.2 五轮诊断结论），故仍先命中缓存毒 `.la` | 换路线（经验1 adapt）：generate() **不再生成 `AutotoolsDeps`**，依赖头/库只经 wrapper 进 configure（`-I<缓存>/include`、`-L<私有> -l...`），从源头消除竞争 `-L`；build() 另加 `_scrub_cache_libdirs` 兜底：只删含 `*.la` 的 `-L`（工具链/sysroot `-L` 保留），并把 `-L<私有>` 前置到 `LDFLAGS/LIBS`。不碰 Conan 缓存（不用 ekg2 原地改 `.la` 路线） |

## 源码修改

无。零补丁适配（全部 OHOS 适配都在 conanfile.py 内完成：wrapper 脚本、configure 参数、umask 改写）。

## 依赖版本

- libgcrypt/1.11.0（直接依赖，transitive_headers/libs；提供全部密码学原语）
- libgpg-error/1.55（直接依赖，与 libgcrypt 自身要求同值；gpg-error.h 被 gcrypt.h 公开包含）
- system_libs: pthread（Linux/OHOS，gpgme 同款）

## 验证结果

本地 Windows 环境未执行编译与测试（按规范，真机验证由 HMBS 后台统一执行，
且除 rsync/ssh 方式外不允许在本机运行 conan）。

test_package 设计（test_bdplus.c，4 项真实 API 验证，待真机实测）：

| # | 验证项 | 断言 |
|---|--------|------|
| 1 | 运行期版本正确 | `bdplus_get_version` 返回 0/2/0 |
| 2 | 编译期/运行期版本一致 | `BDPLUS_VERSION_MAJOR/MINOR/MICRO` 宏 == 运行期值（证明头与库同源，非桩） |
| 3 | 空句柄守卫 | `bdplus_get_code_gen/date/is_cached(NULL)` 均返回 -1 |
| 4 | 错误路径+资源释放 | `bdplus_init(不存在路径, NULL, 16字节VID)` 返回 NULL（会真实走 libgcrypt 初始化、配置加载与文件层，备有桩证伪说明见下），且 `bdplus_free(NULL)` 安全返回 |

证伪设计：测试二进制以“CHECK-OK: <名>”逐项计数，conanfile 数行数，
行数不足或退出码非零即判失败；`bdplus_init` 若意外返回非 NULL（如下一节），
第 4 项显式 FAIL。test_package 另复发 `HMBS_UPSTREAM_TEST_RESULT(no_tests)`，
防止主配方缓存命中轮次缺 marker。

## 交付物

待真机预检产生（预期：lib/libbdplus.so.0 + include/libbdplus/{bdplus.h,bdplus-version.h} + lib/pkgconfig/libbdplus.pc + licenses/COPYING）。

## 注意事项

- 本轮未提交、未推送，待 HMBS 真机全部门禁通过后统一提交。
- 真机待观察项（有证据再动，不盲改）：
  1. ~~libgpg-error/1.55 包内若带 `libgpg-error.la` 且 dependency_libs 含陈旧绝对路径，libtool 链 libbdplus.la 时可能复现 ezstream E236 故障~~→**已命中并修复（见 #9，E236 私有 la-free 目录）**；
  2. 若真机要求 ELF 附 `.codesign` 才能执行，按 libgcrypt/1.12.2 `_postprocess_ohos_elfs`
     （patchelf 去 rpath + binary-sign-tool 自签）补后处理；
  3. 若 clang 15 对 2022 年代码报隐式声明 error，按 cyrus 做法降级
     `-Wno-error=implicit-function-declaration`（当前未加：configure.ac 自带
     `-Werror=implicit-function-declaration` 会覆盖外层同族 flag，加了也无效，
     需改 configure.ac 才有意义，真机命中再议）。
- PR 正文测试数字一律以真机预检日志为准，本轮不填。
