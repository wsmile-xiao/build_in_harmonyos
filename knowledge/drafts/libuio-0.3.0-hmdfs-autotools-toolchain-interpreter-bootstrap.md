# libuio 0.3.0 — HMDFS 拒脚本 exec：autotools 工具包解释器驱动自举（draft）

**Category**: build-system | autotools | conan | ohos · **Severity**: 3 · **Tool**: autoreconf/aclocal/libtoolize/conan

## 症状

GitHub tag 归档（无 configure）的 Autotools 包在 HMDFS conan 缓存真机上构建，
`bash autogen.sh`（autoreconf）首障即死，三段式连环报错：

```text
Can't exec "/storage/.../.conan2/p/autom.../p/bin/aclocal": Permission denied
autoreconf: error: aclocal failed with exit status: 13
# （修好 aclocal 后）
libtoolize: error: $pkgauxdir is not a directory: '.../share/libtool-conan/build-aux'
# （修好 _lt_pkgdatadir 后）
libtoolize: error: linking '.../build-aux/ltmain.sh' to './' failed
autoreconf: error: sh failed with exit status: 1
```

## 根因（四层叠加）

1. **HMDFS 拒绝一切 #! 脚本直接 exec**（仅 ELF 可执行；/data 与 ELF 不受限）
   → conan 缓存（HMDFS）里 automake/libtool 包的 sh shim 与 perl 脚本全部调不起。
2. automake 包 `@INC` 烤死为 `//share/automake-1.18`（prefix 置空），1.18 又没有
   `automake_perllibdir` 环境口 → 直接 perl 运行 `.aclocal-real` 报
   `Can't locate Automake/Config.pm`。
3. **libtool/2.5.4 制品包损坏**：`_lt_pkgdatadir` 指向空的 `share/libtool-conan`，
   真身在 `share/libtool`，且缺 libtoolize 期望的 `m4/` 子目录（宏在 `share/aclocal`）。
4. 上游 autogen.sh 用 `autoreconf -s`（--symlink）——HMDFS 拒绝 link(2)。

## 对策

autoreconf 尊重 `$ACLOCAL/$AUTOMAKE/$LIBTOOLIZE` 覆盖，配方内联 env 前缀驱动
"解释器+脚本+重定位参数"形态（**必须内联前缀**，`Environment().vars().apply()`
穿透不了 conanbuild 包装）：

```text
ACLOCAL="perl -I<pkg>/share/automake-1.18 <pkg>/bin/.aclocal-real
         --automake-acdir=<pkg>/share/aclocal-1.18 --system-acdir=<pkg>/share/aclocal"
AUTOMAKE="perl -I<pkg>/share/automake-1.18 <pkg>/bin/.automake-real
          --libdir=<pkg>/share/automake-1.18"        # 注意是 --libdir
LIBTOOLIZE="sh <lt_pkg>/bin/libtoolize"
_lt_pkgdatadir=<build>/ltdata        # 配方拼装 build-aux/ + libltdl/ + m4/ 三件套
```

ltdata 拼装注意：conan `copy()` 用目录名做 pattern 拷不动目录，须先
`mkdir` 目标目录再 `copy("*", src, dst)`。绕开 autogen.sh 的 `-s`：
`mkdir -p m4 && touch ChangeLog && autoreconf -f -i`。TMPDIR 必须指可写目录
（/tmp 只读，libtoolize 的 sh 临时文件会挂）。

完整可抄实现：`archives/l/libuio/0.3.0/conanfile.py` 的 `_ohos_autogen_env()`。

## 适用面

一切"归档无 configure、需 autoreconf"的包在 HMDFS 真机/CI 上构建。
libisal 2.31.1 曾因此判死走 Makefile.unx 路线，本条可回迁标准 Autotools。
普通存储（CI 工作机若非 HMDFS）不受影响。
