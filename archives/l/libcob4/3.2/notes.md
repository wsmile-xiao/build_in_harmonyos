# libcob4 3.2 适配笔记

## 编译环境
- 构建系统: autotools（GnuCOBOL 3.2 官方 release tarball）
- 编译日期: 2026-09-21
- 编译器: clang（来自 conan profile `tools.build:compiler_executables.c`，设备上为 Harmonybrew OHOS SDK clang）
- 目标平台: HarmonyOS PC / aarch64-linux-ohos（armv8）
- 状态: built

## 本包要解决什么

任务给的包名是 `libcob4`，而上游并没有一个叫 libcob4 的项目。判定依据在库自己声明的 ABI 上：

```makefile
# libcob/Makefile.am
libcob_la_LDFLAGS = $(COB_FIX_LIBTOOL) -version-info 6:0:2 -no-undefined
```

libtool 的 `-version-info current:revision:age`：

| 量 | 公式 | 本例（6:0:2） |
|----|------|---------------|
| SONAME | `libcob.so.(current-age)` | `libcob.so.4` |
| 真实文件名 | `libcob.so.(current-age).age.revision` | `libcob.so.4.2.0` |

即 `libcob4` = 「ABI 主版本 4 的 libcob」，与 `gnucobol/3.2` 同源同名库。因此本包是**把运行库从编译器包里拆出来的纯库包**：交付 `lib/libcob.so*` 与公共头，不交付 `cobc`/`cobcrun`/copybook/配置目录。

## 上游审计（先于动手）

| 项 | 结论 | 证据 |
|----|------|------|
| 上游身份 | 与 `gnucobol/3.2` 同一份源码 | 同一 tarball，SHA256 `3bb48af4…c2ee2` 逐字一致 |
| 库的 ABI | `libcob.so.4`（真实文件 `libcob.so.4.2.0`） | `libcob/Makefile.am` 的 `-version-info 6:0:2`；gnucobol 3.2 的 test-report 亦记录 `lib/libcob.so.4.2.0` |
| 公共头 | `libcob.h`（伞头，顶层 `include_HEADERS`）+ `libcob/{common,version,cobgetopt}.h`、`libcob/*.def`（子目录 `pkginclude_HEADERS`） | 顶层 `Makefile.am` 与 `libcob/Makefile.am` |
| 测试套件 | `tests/testsuite`（autotest，1226 用例） | 与 gnucobol 同源；**经 `cobc` 驱动**，故不能只构建子目录 |
| 构建产物布局 | `lib/libcob.la|.so*`、`lib/gnucobol/CBL_OC_DUMP.so`、`bin/{cobc,cobcrun,cob-config}`、`share/gnucobol/*` | `make install` 后的目录树 |

## 编译步骤

```bash
# 配方内命令（R9）：完整 configure + make + 上游 check，
# install 阶段才收敛到 libcob 子目录
./configure --enable-shared --disable-static \
            --with-math=gmp --with-curses=no --with-json=no \
            --with-db=no --with-xml2=no
make -j1
make MAKEINFO=true -j1 check

# package 阶段（只取运行库）
make -C libcob install DESTDIR=<package_folder>
cp libcob.h <package_folder>/include/     # 顶层伞头不在 libcob 子目录的 install 里
rm -f <package_folder>/lib/libcob.la <package_folder>/lib/libcob.a
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 包名 `libcob4` 在上游找不到对应项目 | `libcob4` 不是项目名，而是 `libcob` 的 ABI 主版本号（SONAME `libcob.so.4`） | 由 `libcob/Makefile.am` 的 `-version-info 6:0:2` 反推 SONAME（`current-age`），确认本包 = GnuCOBOL 运行库；conan `name = "libcob4"` 与目录名一致（L0m-4） |
| 2 | 想「只构建 libcob 子目录」以加快构建，会与「上游测试必须真跑」冲突 | GnuCOBOL 的 `tests/testsuite` 是经 `cobc` 驱动的编译器测试套件，只 `make -C libcob` 拿不到 `cobc` | build() 仍走完整 `configure + make -j1 + make check`，**只在 install/package 阶段收敛**为 `make -C libcob install`；上游 1226 用例照跑（见 `test_package/MANIFEST.yml` 与 `reports/`） |
| 3 | `make -C libcob install` 装不出 `include/libcob.h` | 伞头文件由顶层 `Makefile.am` 的 `include_HEADERS = libcob.h` 安装，不属于 `libcob/` 子目录 | `package()` 里手工 `copy(libcob.h → include/)`；`libcob/*.h` 仍由子目录的 `pkginclude_HEADERS` 安装 |
| 4 | 装了 `libcob.la` / `libcob.a` 这类非交付物 | `make install` 会带上 libtool 归档与静态库 | `package()` 里显式删除 `lib/libcob.la`、`lib/libcob.a`（本包为共享库包，`--disable-static`） |
| 5 | `configure` 里有一处被写坏的非 ASCII 字节 | 上游 `configure` 中 `clang <0xFC>rototype warning`（Latin-1）在部分 host shell/awk 下报语法错 | 与 gnucobol/3.2 同款处理：构建期把这两处替换为 ASCII；并预置生成文件 mtime，避免 `make` 因补丁改动 `configure.ac` 而重新生成 `configure`（那会把替换抹掉） |
| 6 | HarmonyOS 的 `fmemopen` 存在但不可用，临时目录可能只读/不存在 | 上游只做 `stat + S_ISDIR` 判断，会选中一个不可写目录 | 沿用 gnucobol 的 `0004-libcob-call.c.patch`（临时文件回退）与 `0005-libcob-common.c.patch`（`access(W_OK)` 检查）；`test_package` 对「可用 / 不存在 / 指向普通文件 / 只读」四类 `TMPDIR` 各起一个进程做断言 |
| 7 | 临时目录断言在一个进程里只能测一次 | `libcob/common.c` 的 `cob_gettmpdir()` 把解析结果缓存在 `static tmpdir` | `cob_temp_name()` 的断言放进 shell 驱动 `test_libcob.sh`，每条断言各起一个新进程（`test_libcob tmpdir` 模式） |
| 8 | 自动 strip 会破坏 HarmonyOS ELF 签名 | `llvm-strip` 改写 ELF 使签名失效 | 与 gnucobol 一致，OHOS 下 `environment().define("STRIP", ":")` |
| 9 | 以 root 跑测试时 `chmod 500` 造不出「不可写目录」，patch 0005 的断言会假失败 | `access(W_OK)` 对 root 恒真 | `test_libcob.sh` 里先用 `[ -w "$dir" ]` 探测；探测到权限位被忽略时该格如实记为 skip（TAP 仍计 pass），并在输出里写明原因 |

## 源码修改

无平台宏、无新增补丁。7 个补丁与 `gnucobol/3.2` 逐字相同（都是上游源码在 OHOS 上的可移植性修复，不是为了本包新写的）：

`0001` config.guess、`0002` config.sub、`0003` config.status 的 TMPDIR、`0004` libcob 临时文件回退、`0005` 拒绝只读临时目录、`0006`/`0007` configure 期 fmemopen 运行时探测。

## 依赖版本

| 依赖 | 版本 | 用途 |
|------|------|------|
| gmp | 6.3.0 | GnuCOBOL 的任意精度算术（`--with-math=gmp`），静态 PIC 链入 libcob，无运行期 `.so` 依赖 |

ohpcd 已发布的 OHOS armv8 binary（`conan list ... -r ohpcd` 核实）。

## 验证结果

```text
# 上游测试（与 gnucobol/3.2 同源同套件，本包真跑）
1226 tests behaved as expected
56 tests were skipped
0 unexpected failures

# test_package
#   ctest：api 模式（cob_init/tidy 状态机、cob_malloc/free 往返、
#          cob_get_field_str 边界截断、cob_sys_getpid 与 libc getpid 一致）
#   sh test_libcob.sh：13 条 TAP
1..13
ok - test_libcob api exits 0 (…)
ok - api mode ran without dynamic loader errors
ok - cob_temp_name() uses a writable TMPDIR (…)
ok - cob_temp_name() returns an absolute path
ok - libcob re-exports the resolved directory through TMPDIR (…)
ok - non-existent TMPDIR degrades to a usable directory (…)      ← 鸿蒙：HMFS 上 TMPDIR 可能不存在
ok - TMPDIR pointing at a regular file is rejected (…)            ← 鸿蒙
ok - unwritable TMPDIR falls back to a usable directory (…)       ← 鸿蒙：HMFS 只读挂载 / patch 0005
ok - lib/libcob.so.4 present (runtime SONAME, ABI 4)
ok - lib/libcob.so.4.2.0 present (libtool ABI file name)
ok - lib/libcob.so present (link-time name for -lcob)
ok - include/libcob.h and include/libcob/common.h present
ok - package ships no compiler/executables (library-only package)
```

## 交付物

| 文件 | 说明 |
|------|------|
| lib/libcob.so.4.2.0 | 运行时库本体（arm64 ELF 共享库） |
| lib/libcob.so.4 | SONAME 链接 |
| lib/libcob.so | 链接期名字（`-lcob`） |
| include/libcob.h + include/libcob/*.h/.def | 公开 C API 头 |

## 注意事项

- 本包**不含**编译器。要编译 COBOL 源码请依赖 `gnucobol/3.2`（它同时提供 `cobc`/`cobcrun`/`cob-config` 与 copybook/配置目录）。
- 与 `gnucobol/3.2` 的 `lib/libcob.so*` 是同一份产物；两个包可以共存，若同时依赖请注意消费方只应 `requires` 其中一个，以免同一个 soname 出现两份。
- `test_package` 中「只读 TMPDIR」一格的 skip 是**环境相关**的（以 root 运行时 `chmod` 无法造成不可写）；在非 root 的 CI worker 上是实跑断言。
- 本包无命令行产物，因此没有软件级 `commands.json`（R38 只针对可执行命令）。
