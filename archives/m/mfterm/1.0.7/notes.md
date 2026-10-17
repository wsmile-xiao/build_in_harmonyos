# mfterm 1.0.7 适配笔记

## 编译环境

- 构建系统：autotools（官方 Release asset 为 make dist 产物、含预生成 configure；配方按上游 `autogen.sh` 以 `AUTOMAKE="automake --foreign" autoreconf -fi` 自举）
- 编译日期：2026-09-20
- 编译器：clang 15（Conan profile `ohos-aarch64` 注入，os=OHOS arch=armv8 libc++）
- 状态：适配完成，本地 conan create 全流程通过
- 产物：单二进制 `bin/mfterm`（application 型，`package_type="application"`）

## 上游信息

- 上游仓库：https://github.com/4zm/mfterm（官方正式源，GPL-3.0-or-later）
- 版本策略：首次适配上游 `1.0.7`，目录与包版本直接使用 `1.0.7`
- 源码归档：https://github.com/4ZM/mfterm/releases/download/v1.0.7/mfterm-1.0.7.tar.gz（官方 Release asset；上游 tag 实为 v1.0.7，`archive/refs/tags/1.0.7.tar.gz` 返回 404）
- sha256：`b6bb74a7ec1f12314dee42973eb5f458055b66b1b41316ae0c5380292b86b248`（本地实际下载 184675 字节实测，与 Homebrew 公布值一致）
- 软件定位：Mifare Classic RFID 标签终端工具（CLI + readline 交互），基于 libnfc；核心功能包括标签读写、MAD 解析、字典攻击、Crypto-1 CBC-MAC 计算（DES 构造）
- 上游依赖（configure.ac）：libnfc>=1.7（nfc_open）、readline（rl_completion_matches）、libcrypto（DES_set_key_unchecked / DES_ncbc_encrypt）
- 代码生成工具：bison（spec_parser.y）+ flex（spec_tokenizer.l）

## 编译步骤

```bash
cd archives/m/mfterm/1.0.7
conan create . -pr:h=../../../../ci/conan/profiles/ohos-aarch64 -pr:b=../../../../ci/conan/profiles/ohos-aarch64 --build=missing
```

配方构建流程：

1. `apply_conandata_patches` 应用 6 文件 -Werror 修复补丁
2. `AUTOMAKE="automake --foreign" BISON_PKGDATADIR=… M4=… autoreconf -fi` 自举（上游 autogen.sh 同款；BISON_PKGDATADIR/M4 见问题 #4）
3. `configure --prefix=/ --build/--host=aarch64-unknown-linux-ohos`（configure.ac 无 AC_CANONICAL_HOST，显式三元组绕开 config.guess 对 HarmonyOS uname 的探测失败；config.sub 支持 `*-linux-ohos`）
4. `make -j1`（E074：HMDFS jobserver fifo EPERM）
5. `make install DESTDIR=<package_folder>` → `bin/mfterm`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | clang C99 下 `-Wconversion`+`-Werror` 编译失败（6 处） | 上游 AM_CFLAGS=`-g -Wall -Wconversion -std=c99 -Werror`，GCC 与 clang 告警口径不同：重复 typedef（readline 8.3 的 rltypedefs.h 已定义 rl_completion_func_t）、K&R 空参数原型 `void print_tag()`、`1<<i && data` 的 int→bool 转换、枚举赋值收窄（mc→abtCmd[0]）、size_t→int 收窄（sector_header_iterator 参数） | `patches/0001-clang-c99-werror-fixes.patch` 最小修复 6 文件：删除重复 typedef、原型补参数类型、`((1<<i) & data) != 0`、显式 `(uint8_t)`/`(int)` 转换；不动 AM_CFLAGS |
| 2 | OpenSSL 3.x DES 弃用告警 + `-Werror` | mac.c 用 DES_set_key_unchecked/DES_ncbc_encrypt 实现 Crypto-1 CBC-MAC，OpenSSL 3.x 全部标记弃用 | mac.c `#pragma GCC diagnostic push` + `ignored "-Wdeprecated-declarations"`（顶部）+ `pop`（文件末尾，成对，仅本翻译单元）；DES 是 Crypto-1 构造核心，不能换 EVP API；锁 openssl/3.5.6（4.x 将移除 DES 低层 API） |
| 3 | OHOS clang 包装器 `-c` 阶段被注入 `-Wl,--code-sign` | OHOS SDK clang 包装器向所有调用追加 code-sign 链接选项，编译阶段触发 `unused-command-line-argument` 告警，与上游 `-Werror` 冲突 | 配方 `tc.extra_cflags.append("-Wno-error=unused-command-line-argument")`——精准放行该单一告警，其余 -Werror 语义不动（E074 关联实践） |
| 4 | bison 生成 parser 失败 | conan bison/3.8.2 以 `--prefix=` 构建，内置 pkgdatadir 指向不存在的 `/share/bison`（m4sugar.m4 加载失败）；OHOS 上 bison spawn m4 报 "A NULL argv[0] was passed through an exec system call" | bootstrap 与 make 命令前缀注入 `BISON_PKGDATADIR=<pkg>/share/bison` + `M4=<m4-pkg>/bin/m4`（conan m4/1.4.19 工具包，ball/1.5.0 同款先例） |
| 5 | configure "cannot run C compiled programs" | configure 编译的 conftest 动态依赖 libusb-1.0.so.0（libnfc 传递依赖），本 worker 无系统 libusb | generate() 里 `Environment().prepend_path("LD_LIBRARY_PATH", <dep libdirs>)` + `vars(self).save_script("mfterm-build-env")`（libnfc/1.8.0 配方同款） |
| 6 | configure 找不到 libnfc/readline/libcrypto | 上游 configure.ac 用 AC_CHECK_LIB 链接检查，conan 静态包需完整 -I/-L/-l 闭包 | generate() 追加 `AutotoolsDeps(self).generate()`（生成 conanautotoolsdeps.sh，聚合 conanbuild.sh 自动 source） |
| 7 | profile 的 `CONFIG_SHELL=/data/service/hnp/bin/bash` 与 `CC=/data/service/hnp/bin/clang` 在本 worker 不存在 | ohos-aarch64 profile 的 [buildenv]/[conf] 路径按 CI worker 标准布局写死，本机无该目录 | m4/1.4.19 范式：`toolchain.environment()` 里以 shutil.which 校验值覆盖 CC/CXX/LD/AR/RANLIB/NM/CONFIG_SHELL/SHELL（写入 conanautotoolstoolchain.sh，聚合脚本中优先生效） |
| 8 | flex 不在构建 PATH | flex/2.6.4 包是 library 型（不贡献 buildenv PATH），且其缓存包 ID 恰好缺 `bin/flex` | 改用 flex/2.6.4.2（其 package_info 用 `buildenv_info.prepend_path("PATH", bindir)` 主动注入）；另加 `_flex_path_prefix()` 兜底 |
| 9 | HMDFS 上 `umask 077 && mktemp -d` 产生不可写目录（E114） | HMDFS 对目录强制 setgid，configure 的临时目录变 drwx--S---，config.status 写入失败 | 生成的 configure 剥离两处 `umask 077`（abiword-plugin-wikipedia/3.0.8 同款 `_drop_umask_077`） |
| 10 | `/tmp` 只读 | OHOS PC worker 的 /tmp 不可写，autoreconf/m4 临时文件失败 | generate() 设 `TMPDIR=<build_folder>/tmp`（m4/1.4.19 同款） |

## 源码修改

- `patches/0001-clang-c99-werror-fixes.patch`（6 文件，最小修复，仅编译性问题，无行为变更）
  - `mfterm.c`：删除与 readline 8.3 rltypedefs.h 重复的 `rl_completion_func_t` typedef
  - `tag.h`/`tag.c`：`void print_tag()` → `void print_tag(mf_size_t size)`；`1<<i && data` → `((1<<i) & data) != 0`
  - `mifare.c`：`abtCmd[0] = mc` → `(uint8_t)mc`
  - `mifare_ctrl.c`：三处 `sector_header_iterator(size)` → `((int)size)`
  - `mac.c`：`#pragma GCC diagnostic push/ignored/pop` 成对抑制 OpenSSL 3.x DES 弃用告警（Crypto-1 核心，不可换 API）
- `conanfile.py`
  - `package_type="application"`、`basic_layout`、`AutotoolsToolchain` + `AutotoolsDeps` + LD_LIBRARY_PATH 注入
  - `requirements`: libnfc/1.8.0 + readline/8.3 + openssl/3.5.6（均已发布制品仓，conan list 核验）
  - `build_requires`: bison/3.8.2 + flex/2.6.4.2 + m4/1.4.19（系统 autoconf/automake，abiword 先例）
  - `package_info`: `bindirs=["bin"]`（CLI 工具无库导出，m1ddc/libnfc-tools 同款）
- `test_package/`
  - `conanfile.py`：两段式（libnfc-tools 范式）——鸿蒙特有测试 + 消费者冒烟
  - `harmonyos_specific_test.c`：编译期 `__OHOS__`/`__aarch64__` 硬绑定 + 运行时校验安装产物 ELF64/EM_AARCH64、PT_INTERP=`/lib/ld-musl-aarch64.so.1`、`.note.ohos.ident` 段、NEEDED 含 libusb-1.0.so.0 与 libc.so，并链接 libnfc 调 `nfc_version()` 验证依赖 ABI（9 checks）
  - `run_mfterm_test.sh`：真实执行 mfterm——--version/--help、`mac key 00×8` + `mac compute 0`（Crypto-1 CBC-MAC 算法断言：全零密钥→`8c a6`、全 ff 密钥→`ca aa`，两密钥不同 MAC 证明密钥真实参与计算，2026-09-20 OHOS aarch64 真机实测回填）、quit 优雅退出
  - `MANIFEST.yml`：上游测试审计（上游未提供正式自动测试）+ test_package 断言清点（assertion_count: 14）

## 上游测试审计

- 上游未提供正式自动测试：源码树无 test/ 目录，Makefile.am 无 TESTS 目标，configure.ac 无 CUTTER/Check/CMocka 等框架引用，README.md 与 debian/ 无测试入口
- 不伪造上游测试数量（validation.upstream_tests.total = 0）；验证由 test_package 消费者冒烟（5 测试点）+ 鸿蒙特有测试（9 checks）补齐

## 知识库判定

- 本次适配遇到的所有问题均命中知识库既有条目或仓库已有配方先例（E074/E114 相关实践、ball 的 bison BISON_PKGDATADIR/M4、m4 的 profile 坏值覆盖、libnfc 的 LD_LIBRARY_PATH 注入、abiword 的 umask 剥离、libnfc-tools 的 AutotoolsDeps 注入）
- 无合适的新知识点：未发现鸿蒙特有且未被覆盖的可复用问题，未创建知识库草稿（保持路径 A 基础适配，不为积分强行创建）

## 本机前置核验

```text
conan create（ohos-aarch64 profile）: 全流程通过
  configure/build/install/package: OK
  test_package: HarmonyOS-specific test: 9 checks, 0 failures
                mfterm consumer smoke test: DONE（5/5 ok，含 MAC 算法断言）
py_compile: passed
git diff --check: passed
```
