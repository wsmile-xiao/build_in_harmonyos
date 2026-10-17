# DRAFT-E590-libyal-optional-dep-autodetect-ohos：libyal 可选依赖在 OHOS 上的探测读数与静态假绿

> 状态：DRAFT，路径 B（贡献创新）候选，最终分类与知识条目编号以官方审核为准
> 触发库：`libfsapfs/20240429`（libyal 家族，APFS 访问库）
> 主题：zlib/libcrypto 这类**外部可选依赖**的自动探测在 OHOS 上到底读出了什么、该怎么取舍、
> 以及「静态构建会静默关掉它们」这一假绿面

## 新增问题

libyal 每个库的 `configure.ac` 都把外部能力做成「可选 + 自动探测」：
`AX_ZLIB_CHECK_ENABLE` / `AX_LIBCRYPTO_CHECK_ENABLE` 的默认值是 `auto-detect`，
探测不到就**静默降级**——构建照常成功、退出码 0、日志里也没有 error。
后果有两层：

1. **设备与 CI 的能力集合可能不同**，而所有机械门禁（G0/G1/G2/L2/L4/L5、`make check`）
   都照样通过；这是一种只体现在 configure 摘要里的假绿。
2. **同族先例的 flag 会被照抄**。libbde 与 libfvde 的配方为保持「零外部依赖」显式传了
   `--with-openssl=no`；照抄到 libfsapfs 就会在没有复核的情况下改变被交付包的能力集合。

实测 libfsapfs 20240429 在 OHOS 真机上的读数与「照抄先例」的直觉相反：
**zlib 有（来自 OHOS NDK sysroot），libcrypto 没有，但加密能力并没有丢**——
AES/MD5/SHA256 由发布包内嵌的 `libcaes`/`libhmac` 提供，摘要里显示 `local`。

还有第三层，属于 m4 宏自身的分支：`AX_ZLIB_CHECK_LIB` 与 `AX_LIBCRYPTO_CHECK_LIB`
的第一行就是

```m4
[test "x$ac_cv_enable_shared_libs" = xno || test "x$ac_cv_with_zlib" = xno],
[ac_cv_zlib=no],
```

也就是说 **只要构建 `shared=False`（静态），两项能力都会被无条件置 `no`**，
无论系统里有没有 zlib/openssl，而且 configure 不会给出任何警告。

## 可复用方法

### 1. 先只跑 configure，读能力摘要

不要把「探测」混进完整构建：一次 configure 探针（约 1 分钟）就能拿到全部读数，
比在 `conan create` 失败后再回头猜便宜得多。

```sh
mkdir -p "$TASK_DIR/probe" && cd "$TASK_DIR/probe"
tar xzf "$TASK_DIR/src-download/libfsapfs-experimental-20240429.tar.gz"
cd libfsapfs-20240429
sed -i 's/umask 077/umask 022/' configure && chmod 755 configure
(umask 022; CC=/data/service/hnp/bin/clang CONFIG_SHELL=/data/service/hnp/bin/bash \
   SHELL=/data/service/hnp/bin/bash /data/service/hnp/bin/bash ./configure \
   --disable-python --with-libfuse=no --enable-static-executables=no \
   --enable-shared --disable-static \
   --build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu) \
   > configure.log 2>&1
sed -n '/^Building:/,/^Features:/p' configure.log
```

（`$TASK_DIR` 是任务持久目录；设备 `/tmp` 只读，不要用 `/tmp`。）

### 2. 三条判读规则

| 日志形态 | 不要读成 | 正确读法 |
|---|---|---|
| `checking for zlib >= 1.2.5... no` | 「没有 zlib」 | 这只是 pkg-config 没有 `zlib.pc`；紧接着的 `checking for zlib.h... yes` / `checking for uncompress in -lz... yes` 才是结论 |
| `checking for openssl >= 1.0... no` + `openssl/opensslv.h... no` | 「加密支持被禁用」 | 只说明没有 OpenSSL；libyal 的 AES/MD5/SHA256 由内嵌 libcaes/libhmac 提供，摘要显示 `local` 即证明能力在 |
| 摘要里 `DEFLATE compression support: no` | 「上游不支持压缩」 | 先查是不是 `shared=False`（m4 第一行按 shared 无条件关闭）或显式传了 `--with-zlib=no` |

### 3. 确认探测到的头文件来自哪里（设备特供 vs SDK 基线）

同一读数在不同环境含义完全不同。用 clang 自己的 include 搜索路径取证：

```sh
/data/service/hnp/bin/clang -E -v -x c /dev/null 2>&1 \
  | sed -n '/#include <\.\.\.> search starts here/,/End of search list/p'
```

libfsapfs 的 `zlib.h` 命中 `.../ohos-sdk_<版本>/ohos/native/llvm/bin/../../sysroot/usr/include`，
即 **OHOS NDK sysroot**，不是 harmonybrew 之类的设备特供路径——CI worker 用同一 SDK，
所以「设备读到 zlib」可以迁移到 CI，不属「设备绿 ≠ CI 绿」那一类。

### 4. 取舍必须留痕

- 保留自动探测（本例）：在 `notes.md` 里逐字记下摘要，并在 PR 里说明交付物能力集合
  （DEFLATE=zlib、AES-ECB/AES-XTS/MD5/SHA256=local、FUSE=no）。
- 确要关闭能力：显式传 flag，同时在 `manifest.yaml` 的 `build.configure_options`
  与 `notes.md` 写明「关了哪一个、为什么、影响哪些功能、未覆盖范围不得写成 PASS」。
- **不要**只留一个 flag 就交付——评审无法从日志复核取舍依据。

## 与既有条目的边界

- `E277`（发布包闭包）解决的是「**内嵌**的本地 libyal 组件如何证明闭包完整、不误拆依赖」；
  本条处理的是**外部可选依赖**的探测读数与取舍留痕，对象与判据都不同。
- `E007`（OHOS 三元组）、`E011`（HMDFS umask）、`E087`（CONFIG_SHELL）、`E228`（libtool `.libs`）
  分别解决别的机制，本条只引用其结果，不重复申报。
- `DRAFT-libfsntfs-release-archive-closure` 的测试能力分层（fixture 缺失 → SKIP 而非 FAIL）
  与本条正交：那条管「输入数据缺不缺」，本条管「可选特性开没开」。

## 实证（设备真机，2026-09-20）

能力摘要逐字：

```text
   DEFLATE compression support:                 zlib
   libhmac support:                             local
   MD5 support:                                 local
   SHA256 support:                              local
   libcaes support:                             local
   AES-ECB support:                             local
   AES-XTS support:                             local
   FUSE support:                                no
```

探测过程逐字：

```text
checking for zlib >= 1.2.5... no
checking for zlib.h... yes
checking for zlibVersion in -lz... yes
checking for uncompress in -lz... yes
checking for openssl >= 1.0... no
checking for openssl/opensslv.h... no
checking for openssl/evp.h... no
```

本包最终取舍：保持 auto-detect，配方 `configure_args` 只有
`--disable-python` / `--with-libfuse=no` / `--enable-static-executables=no` + GNU 三元组，
未传 `--with-openssl`/`--with-zlib`。
