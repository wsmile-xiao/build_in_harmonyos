# libvoikko 4.3.3 适配笔记

## 基本信息
- 上游：https://voikko.puimula.org/
- 源码：https://www.puimula.org/voikko-sources/libvoikko/libvoikko-4.3.3.tar.gz
- sha256：`d1162965c61de44f72162fd87ec1394bd4f90f87bc8152d13fe4ae692fdc73fa`
- 语言：C++17，对外纯 C ABI（voikko.h）
- 构建系统：GNU Autotools

## W0 依赖检查
最小配置下无任何强制 Conan 依赖。VFST 后端内置；HFST/VISLCG3/Lttoolbox 均关闭。
pthread/m 为 bionic 系统库。

## 真机构建结果（2026-09-26，设备 frp-tip.com:56267，aarch64）
`conan create` 通过：编译 → 链接 → 安装 → test_package 全绿。
产物：`lib/libvoikko.so.1.16.3` + `.so`/`.so.1` 软链、`include/libvoikko/*.h`、`lib/pkgconfig/libvoikko.pc`。
test_package：dlopen libvoikko.so → dlsym voikkoInit/voikkoTerminate → `voikkoInit("fi")`
在无词典环境下正确返回 `NULL` + 错误串 "No valid dictionaries were found"，断言通过。

## 构建中实际踩到并解决的坑（按顺序）
1. **profile bash 路径失效**：`ohos-aarch64` profile 把 CONFIG_SHELL/SHELL 设为
   `/data/service/hnp/bin/bash`，该设备上不存在。autoconf configure 会在第 ~139 行
   `exec $CONFIG_SHELL` 自重执行，直接 127。
   → configure 命令行内联 `CONFIG_SHELL=/bin/sh SHELL=/bin/sh`（/bin/sh 为 Toybox ash）。
2. **编译器路径失效**：profile `tools.build:compiler_executables` 指向
   `/data/service/hnp/bin/clang{,++}`，同样不存在；真实 clang 在
   `/storage/Users/currentUser/usr/local/bin/clang{,++}`。
   → 构建命令用 `-c tools.build:compiler_executables={...}` 覆盖（环境 workaround，
     未硬编码进配方；正式 shadow CI 若以 root/标准镜像跑可能无需此覆盖）。
3. **config.status 临时目录 Permission denied**：config.status 跑
   `(umask 077 && mktemp -d ./confXXXXXX)`。本设备 /storage 挂载上构建 uid(20020108)
   不属主 umask-077 目录（出来是 drwx--S---），写 subs*.awk 失败，且非属主无法 chmod。
   → 在 build() 里写 mktemp shim：内部 `umask 022` 后 exec 真实 mktemp；并用
     `PATH=<shim>:$PATH` 内联前置（profile buildenv 会 prepend 自己的 PATH，光改
     os.environ 会被 shadow）。
4. **-Werror**：configure.ac 追加 `-Wall -Werror -pedantic`，clang-15 把 OHOS 链接期
   专用的 `-Wl,--code-sign`/`-fuse-ld=lld` 当作纯编译期未用参数警告，被 -Werror 升级成错误。
   → 构建前 `sed -i 's/ -Werror//g' ../configure`。正式化时应改为 patches/*.patch
     （改 configure.ac 后用 refresh-patch --auto）。
5. **安装前缀**：手动调 configure 时若漏 `--prefix=/ --libdir=/lib --includedir=/include`，
   make install 会落到 `$pkg/usr/local/...`，conan cpp_info 找不到库。
6. **test.c**：`voikkoTerminate(NULL)` 不保证空指针安全，会段错误；已去掉该调用。

## 仍待正式 shadow CI 确认
- 上述 1/2/3 含设备特定路径，正式隔离 runner（可能 root + 标准镜像）下可能不需要；
  若不需要，应把 mktemp shim 的绝对路径、sed -Werror 等收敛为标准 patches/。
- `-Werror` 的 sed 应转为正式 patch。
- 静态库选项未测（默认 shared=True）。
- 未 `conan upload`（W3 之后由 CI 做）。

## 复现命令（本设备）
```sh
export PATH=$HOME/.local/bin:/data/service/hnp/bin:/storage/Users/currentUser/usr/local/bin:$PATH
export TMPDIR=$HOME/tmp-voikko
cd <recipe dir>
conan create . --user=ohpcd --channel=stable \
  -pr:h=$HOME/.conan2/profiles/ohos-aarch64 \
  -pr:b=$HOME/.conan2/profiles/ohos-aarch64 \
  -c 'tools.build:compiler_executables={"c":"/storage/Users/currentUser/usr/local/bin/clang","cpp":"/storage/Users/currentUser/usr/local/bin/clang++"}' \
  --build=missing
```
