# librdata

## 简介
librdata 是读写 R 语言数据文件（`.RData` / `.rds`，R 序列化的 data.frame）的 C 库，
上游来自 ReadStat 项目拆分，被 pyreadr 等绑定使用。支持 REAL / INT32 / STRING /
LOGICAL / TIMESTAMP / DATE / FACTOR 等列型，支持读 gzip / bzip2 / xz 压缩的 RData。

## OHOS 适配
- **上游快照不含 `configure`**（GitHub archive 只是 git tree 快照），配方的
  `build()` 先 `autoreconf --force --install` 自举，再 configure/make/make check；
- 补丁 `0001-configure.ac.patch`：上游 `AM_ICONV` 依赖 GNU gettext 的 `iconv.m4`，
  该文件不在 OHOS 构建工具闭包内（autoreconf 报
  `possibly undefined macro: AM_ICONV`）；改为直接探测 libc 的
  `iconv.h` + `iconv()/iconv_open()/iconv_close()`，保留硬失败语义；
- 配方在 autoreconf **之后**就地去掉生成 `configure` 里的 `umask 077`
  （HMDFS 会把该临时目录落成不可写的 `drwx--S---`，`config.status` 随即失败）；
- 显式传 `--build/--host=aarch64-unknown-linux-ohos`：`config.guess` 在本设备
  HMDFS 上创建 `dummy.c` 会 Permission denied；
- 三个压缩后端（zlib / bzip2 / liblzma）走 Conan 静态依赖：OHOS SDK sysroot 的
  `libz.so` 是 stub（SONAME=`libz.so`、符号同址、`/system/lib64` 下没有该文件），
  若让上游 `AC_CHECK_LIB` 命中它会被写进 `DT_NEEDED`，运行期装载失败。

## 依赖
- 链接期（全部静态内链，运行期无额外 `.so` 依赖）：
  `zlib/1.3.1.1`、`bzip2/1.0.8.2`、`liblzma/5.8.1`
- 构建期：`automake/1.18`、`libtool/2.5.4`（autoconf 由 HNP 工具链提供）

## 选项
- `shared`（默认 `False`）：`False` 出 `lib/librdata.a`，`True` 出
  `lib/librdata.so.0.0.0` + `librdata.so.0`（SONAME=`librdata.so.0`）+ `librdata.so`

## 功能验证
```bash
conan create archives/l/librdata/0-20210223-git-85757dc6 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# 交付物
find "$(conan cache path librdata/0-20210223-git-85757dc6)" -name 'librdata*' -o -name 'rdata.h'
```

## 参考
- 主页: https://github.com/WizardMac/librdata
- 本版本快照 commit: 4a80bf3894c9250195a564017f2136fd85757dc6（2021-02-23）
