# tgl 2.0.1-git20160323.ffb04cac 适配笔记

## 编译环境
- 构建系统: autotools（源码包内含已生成的 `configure`）
- 编译日期: 2026-10-03
- 编译器: clang 15.0.4（`/data/service/hnp/bin/clang`），原生构建 aarch64 / HarmonyOS 6.0
- 状态: built

## 版本说明
- 上游: https://github.com/vysheng/tgl ，快照 commit `ffb04cac`（2016-03-23）；Debian 包
  `2.0.1+git20160323.ffb04cac-6`，本配方沿用赛事版本号 `2.0.1-git20160323.ffb04cac`（首次适配，R37）。
- 源码: `https://deb.debian.org/debian/pool/main/t/tgl/tgl_2.0.1+git20160323.ffb04cac.orig.tar.xz`
  （Debian 官方归档，与上游 git 快照一致），sha256
  `fdaa7ae13faede841d98c604be8ad1804b2827ce6816ec03c8770ec6d1562a22`。
- 上游 `tgl.h` 的 `TGL_VERSION` 是 `2.1.0`，与快照日期版本（2.0.1-git…）不同，属上游现状。

## 编译步骤
```bash
# 依赖（制品仓已发布）
#   openssl/3.5.6.1、zlib/1.3.1、libevent/2.1.13（--enable-libevent 需要）
# 构建期工具（制品仓已发布）
#   tl-parser/0.0.0-git20210107.1933e76f
conan create archives/t/tgl/2.0.1-git20160323.ffb04cac \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `make` 找不到 `tl-parser` 可执行文件 | 上游从 `tl-parser` git 子模块编译，而 release tarball 里 `tl-parser/` 只是空目录 | 补丁 0001：`${EXE}/tl-parser` 改为指向制品仓 `tl-parser` 包的可执行文件（`TL_PARSER=... make`） |
| 2 | `generate.c`/`mtproto-utils.c` 找不到 `tl-parser/tl-tl.h`、`tl-parser/portable_endian.h` | 同 1，两个头都在子模块里（Debian 由 `libtl-parser-dev` 提供 `/usr/include/tl-parser/`） | 补丁 0007：按依赖的 `tl-parser` 同一 revision 逐字补齐这两个头（仅构建期使用，不安装） |
| 3 | 上游没有 `install` 目标，无法打包 | 2016 年的 Makefile 只产出 `libs/libtgl.a`、`libs/libtgl.so` | 补丁 0002：新增 `install` 目标（库 + 全部公共头，保持 `<tgl/...>` 目录结构） |
| 4 | clang 15 下 `-Werror` 直接编译失败 | 上游面向上古 GCC，`-Wall -Wextra -Werror` 在 clang 15 下产生大量新告警 | 补丁 0002：去掉 `-Werror`（保留 `-Wall -Wextra`） |
| 5 | `bin/generate` 在 Release 构建下 SIGSEGV | 上游生成器用「带副作用的 assert」驱动 schema 解析（`assert (get_int () == TLS_SCHEMA_V2)`），`-DNDEBUG` 下这些调用被删掉，解析整体错位 | 补丁 0002：在 `${CFLAGS}` 之后追加 `-UNDEBUG`，恢复断言 |
| 6 | `crypto/rsa_pem_openssl.c` 编译失败 | OpenSSL 1.1 起 `RSA`(rsa_st) 结构不透明 | 补丁 0003：改用 `RSA_set0_key`/`RSA_get0_key`（Debian 同款修复） |
| 7 | `tgl_do_send_document` 里 `tgl_peer_id_t` 部分未初始化 | 只赋了 `peer_id`，其余成员未初始化即被整体拷贝（UB） | 补丁 0004：改用聚合初始化（Debian / 上游 PR 150 同款） |
| 8 | `configure` 报 `working directory cannot be determined` | HMDFS 下 Conan 构建目录里 `getcwd()` 失败，autoconf 的 `pwd` 判定直接退出 | 补丁 0005：`pwd` 失败时回退 `$PWD`（build() 里预置 `os.environ["PWD"]`）；同时把 config.status 临时目录的 `umask 077` 改 `022`（HMDFS 新目录强制 setgid，077 目录连属主都写不进去） |
| 9 | `configure` 报 `cannot run C compiled programs` | 鸿蒙只允许运行已签名的可执行文件，刚链接出的 conftest 无法执行（E064） | 补丁 0006：保留编译器可用性判定结果，改为 `cross_compiling=yes` 并给 warning 继续（与 at/atd 配方同款） |
| 10 | 链接报 `undefined symbol: rpl_malloc/rpl_realloc` | 交叉编译模式下 `AC_FUNC_MALLOC`/`AC_FUNC_REALLOC` 的运行探针被跳过，autoconf 回退成「libc 实现有问题」，把 `malloc`/`realloc` 定义成 `rpl_*` | configure 传 `ac_cv_func_malloc_0_nonnull=yes ac_cv_func_realloc_0_nonnull=yes`（autoconf 官方答案） |
| 11 | 构建期运行 `bin/generate` 报 `Error loading shared library libevent.so` | 生成器链接了 Conan 的共享依赖，`make` 期间不在运行环境里 | build() 里 `make` 前 `source conanrun.sh`，把依赖库搜索路径带进构建环境 |
| 12 | 编译 `crypto/*.c` 报 `../config.h` 找不到 | 上游是源码内构建，而 Conan 默认在 `build-release/` 子目录里 configure | `layout()` 把构建目录设为源码根（`self.folders.build = "."`），与上游一致 |
| 13 | 链接 `libs/libtgl.so` 报 `relocation … cannot be used against symbol 'z_errmsg'; recompile with -fPIC` | 制品仓的 `zlib/1.3.1` 按 R26 以静态且非 PIC 的方式交付，无法链进共享库 | 配方声明 `package_type = "static-library"`，`make`/`install` 传 `LIB_LIST=libs/libtgl.a`，只交付静态库（上游仍同时构建 `.a` 与 `.so`，本包只安装 `.a`） |

## 源码修改
- `patches/0001-makefile-use-system-tl-parser.patch` — 用制品仓 `tl-parser` 工具替代缺失的子模块
- `patches/0002-makefile-install-target-and-compiler-flags.patch` — 新增 `install` 目标；去 `-Werror`；追加 `-UNDEBUG`
- `patches/0003-openssl-1.1-opaque-rsa.patch` — OpenSSL 1.1+ 不透明 RSA API
- `patches/0004-queries-initialize-peer-id.patch` — `tgl_peer_id_t` 完整初始化
- `patches/0005-configure-hmdfs-pwd-tmpdir.patch` — HMDFS `pwd` 回退 `$PWD`、临时目录 `umask 022`
- `patches/0006-configure-cross-compiling-conftest.patch` — conftest 无法执行时继续交叉编译模式
- `patches/0007-add-tl-parser-schema-header.patch` — 补齐子模块里的两个头（`tl-tl.h`、`portable_endian.h`）

## 依赖版本
- openssl/3.5.6.1（TLS/加密）、zlib/1.3.1（gzip）、libevent/2.1.13（`--enable-libevent` 的网络与定时器实现）
- 构建期工具：tl-parser/0.0.0-git20210107.1933e76f（`tool_requires`）

## 验证结果
```bash
conan create archives/t/tgl/2.0.1-git20160323.ffb04cac \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# CREATE_RC=0
# package(): Packaged 1 '.a' file: libtgl.a  + include/tgl/**（公共头 46 个文件）

# 消费者用例（test_package，静态链接 libtgl）
ok 1..12 - TGL_VERSION / tgl_state_alloc / peer id 辅助函数 / peer tree 插入·查询·遍历 / 内存统计 / 释放
12 checks, 0 failures
```

上游测试：该 2016 快照**不含测试套件**（没有 `tests/` 目录，`Makefile.in`/`Makefile.tl-parser` 里没有
`check` 目标、`check_PROGRAMS`、`TESTS`），因此按 TEST_QUALITY_SPEC 的要求在 `build()` 中内置审计命令
（`grep` + `find`）把「无上游测试」这一事实写进 `conan create` 日志，并补充消费者用例作为可用性验证。
详见 `test_package/MANIFEST.yml` 与 `reports/test-report.md`。

## 注意事项
- 只交付静态库 `libtgl.a`（原因见问题 13）；头文件按 `<tgl/tgl.h>`、`<tgl/crypto/*.h>`、`<tgl/auto/*.h>` 布局安装。
- `tl-parser` 生成器只在构建期使用，不进入交付产物；`bin/generate` 同理。

---

### 对话 #1 — 编译协作者 (implementer)

**请求**: 在鸿蒙 PC 上完成 tgl `2.0.1-git20160323.ffb04cac` 的适配（Conan 配方 + 消费者用例 + 门禁自检），
上游测试口径必须真实（有测试就全跑，没有就说明原因并自行补充）。

**执行摘要**:
1. 依赖预检（W0/R36）：`openssl`、`zlib`、`libevent`、`tl-parser` 均已在 ohpcd 制品仓发布，无需自行导入；
   tgl 自身的 `tl-parser` 是 git 子模块且 release tarball 里为空目录，因此用制品仓的 `tl-parser` 包替代。
2. 构建链路：autotools（源码包内含 configure）→ 7 个补丁 → `conan create` rc=0，交付静态库 `libtgl.a`
   与 46 个公共头文件。
3. 上游测试清点（R51）：该 2016 快照没有 `tests/` 目录，`Makefile.in` / `Makefile.tl-parser` 里也没有
   `check` 目标、`check_PROGRAMS`、`TESTS`，即上游可运行用例 N=0；按规范在 `build()` 内置 `grep` + `find`
   审计把这一事实写进 `conan create` 日志，并补充消费者用例 12 条断言（100% 通过）。
4. 关键问题与证据：
   - `bin/generate` 在 Release 默认的 `-DNDEBUG` 下 SIGSEGV：用 `-O0/-O1/-O2/-O3 × 有无 NDEBUG` 二分验证
     定位为「带副作用的 assert」（`assert (get_int () == TLS_SCHEMA_V2)`），补丁在 `${CFLAGS}` 后追加 `-UNDEBUG`。
   - `libtgl.so` 链接失败：制品仓 `zlib/1.3.1` 按 R26 是非 PIC 静态库，`ld.lld` 报
     `relocation R_AARCH64_ADR_PREL_PG_HI21 cannot be used against symbol 'z_errmsg'`，因此本包声明为
     `static-library`，只交付 `.a`。
   - HMDFS 下 `configure` 的 `pwd` 判定失败（`working directory cannot be determined`）与 `conftest` 无法执行
     （E064，鸿蒙只运行已签名二进制）分别用补丁 0005 / 0006 处置，与 adms/at 配方同款。
5. 质量门禁：`conan-verify` G0-G3 通过；W3 本地 CI 模拟通过（`.ci-result.json` exit_code=0）；
   W4 独立审计见 `reports/audit-result.json`。

**产出文件**: `conanfile.py`、`conandata.yml`、`patches/`（7 个补丁）、`test_package/`
（`conanfile.py` + `CMakeLists.txt` + `test_tgl.c` + `MANIFEST.yml`）、`notes.md`、`manifest.yaml`、
`reports/test-report.md`、`packaging/tgl-2.0.1-git20160323.ffb04cac-ohos-aarch64.tar.gz`。
