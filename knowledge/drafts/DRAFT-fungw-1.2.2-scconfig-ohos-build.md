# scconfig 系项目（fungw / repo.hu 家族）在 OHOS + HMDFS 上的三个必踩坑

> Draft: `DRAFT-FUNGW-122-SCCONFIG-OHOS-BUILD`
> Stem: `fungw-1.2.2-scconfig-ohos-build` — pairs with the same-stem `.kv`

## 基本信息

- **ID**: DRAFT-FUNGW-122-SCCONFIG-OHOS-BUILD
- **严重度**: 2
- **类别**: portability|build-system|ohos-platform|filesystem
- **触发工具**: conan|make|clang|scconfig

## 错误特征

三个坑在日志里长得很像"上游坏了"，其实都是平台/工具链缺口：

```
make: cc: No such file or directory                      # (1) scconfig 自举
./configure: Permission denied (exit 126)                # (1b) +x 位丢失
ln: cannot create symbolic link ... Permission denied    # (2) genht_std.a
ld.lld: error: undefined reference due to
  --no-allow-shlib-undefined: strhash / htsp_init / ...  # (3) .so 漏链 genht
fatal error: 'genht/htsp.h' file not found               # (4) 头文件漏装
```

## 逐个击破

### (1) `./configure` 自举就要 `cc`

项目根的 `configure` 只有 51 字节：

```sh
#!/bin/sh
cd scconfig && make && ./configure "$@"
```

scconfig 用 make 内建变量 `CC`（默认 `cc`）编译 hooks.c。OHOS SDK 只有 clang：

```bash
CC=<clang> sh ./configure --prefix=<prefix> --disable-perl
```

注意两件事：

- `CC` 必须从 conf `tools.build:compiler_executables` 取（R33），不要裸用 `${CC}`；
- 用 `sh ./configure` 而不是 `./configure`：conan 把源码复制进 HMDFS 构建目录时
  会丢掉执行位，直接执行是 exit 126。

### (2) HMDFS 既不支持 symlink 也不支持 hardlink

上游有两处依赖链接：

| 位置 | 命令 | 失败表现 |
|------|------|----------|
| `src_3rd/genht/Makefile` | `genht_std.a: $(LIBA)` → `ln -s` | make **Error 2**（致命） |
| 各 `Makefile` 的 `install_link_` | `sccbox ln -f`（实为硬链接） | **静默失败**，只留下 `.so.X.Y.Z` |

实测（`python3` 直接调）：

```
symlink  FAIL [Errno 13] Permission denied
hardlink FAIL [Errno 1]  Operation not permitted
```

对策：

- `genht_std.a`：先 `make libgenht.a`，再 `cp libgenht.a genht_std.a`，make 看到目标
  已存在且比前提新就跳过那条 `ln -s` 规则；
- SONAME 别名（`.so.X.Y` / `.so.X` / `.so`）在 `package()` 里**复制**生成。

### (3) 上游共享库不自洽：`.so` 漏链 `src_3rd` 目标文件

`libfungw.so.1.2.2` 的链接规则只用了自己的 OBJS，genht 被当成独立静态库
（只有 regression 测试显式链 `genht_std.a`），于是共享库留下未定义符号：

```
ld.lld: error: undefined reference due to --no-allow-shlib-undefined: strhash
>>> referenced by .../p/lib/libfungw.so
```

对策：命令行变量覆盖 `LDFLAGS`（会传给子 make），把 genht 目标文件链进去：

```bash
CC=<clang> make -C libfungw LDFLAGS="-rdynamic -fPIC <src_3rd/genht/*.o>"
CC=<clang> make -C libfungwbind LDFLAGS="-rdynamic -fPIC <src_3rd/genht/*.o>"
```

比"把 libgenht.a 塞给消费者"更稳：静态库补链接虽能过 `--no-allow-shlib-undefined`，
但可执行文件默认不导出符号，运行期 `dlopen` 插件（puplug）时会再报找不到符号。

### (4) 头文件递归依赖没被 install

`libfungw/fungw.h` 直接 `#include <genht/htsp.h>`，但上游 `install_` 只装
`include/libfungw/*.h`，不装 genht 头。`package()` 里补：

```python
copy(self, "*.h", os.path.join(self.source_folder, "src_3rd", "genht"),
     os.path.join(incdir, "genht"))
```

## 顺带：scconfig 没有 --with/--without

语言绑定全靠系统探测，探测到 `/data/service/hnp/bin/perl` 就会开 perl 绑定
（OHOS 没有 libperl 可链）。可用开关见 `libfungwbind/scconfig_hooks.h` 的
`CUSTOM_ARG` 列表：`--disable-perl` / `--disable-lua` / `--disable-python3` /
`--disable-cli` ……

## 验证

```bash
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
conan create . -o shared=False -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

两条链路都绿，且 `build()` 内真实跑了上游 5 个 regression 程序
（`test` / `test_c` / `test_custom` / `multicall`（含 multicall.ref 逐字比对）/
`test_script`（fawk 脚本））。
