# bandwidthd 2.0.1-cvs20090917 主机侧验证

## 结果

- 原始 tarball + 0001-0007 补丁链：通过
- `./configure`：通过
- 源码外 `./configure --build=arm64-apple-darwin --host=aarch64-unknown-linux-ohos`：通过，`tcphdr` 字段探测和 `_res` 声明探测通过
- `config.status`：通过，Unix 行尾替代路径成功生成 `Makefile` 和 `config.h`
- `make -j1`：通过
- `test_package/test.sh`：通过，2/2 条断言
- `make check`：上游没有 `check` 目标，不计为测试失败

## WSL OHOS/aarch64 交叉验证

- 目标编译器：`/data/service/hnp/bin/clang`（OHOS SDK clang 15）
- 目标依赖：Conan 缓存中的 OHOS `gd`、`libpcap`、`libpng`
- 构建工具：WSL 原生 clang/make，另安装 bison 3.8.2、flex 2.6.4
- `configure --build=x86_64-pc-linux-gnu --host=aarch64-unknown-linux-ohos`：已用固化 bootstrap 产物验证配置路径
- `make -j1`：通过
- `file bandwidthd`：ARM aarch64 PIE ELF，解释器为 `/lib/ld-musl-aarch64.so.1`

交叉构建实际验证了 3 个源级补丁：跨编译跳过 `AC_CHECK_FILE`、优先检查
`libpng16`、按声明探测 resolver 的 `_res`，以及避免旧式全局数组重复定义。

## 复现命令

在源码解压目录中，先应用 `conandata.yml` 的 0001-0007 补丁，再使用 Homebrew 的 `gd`、`libpcap`、`libpng`：

```bash
CPPFLAGS='-I/opt/homebrew/opt/gd/include -I/opt/homebrew/opt/libpcap/include -I/opt/homebrew/opt/libpng/include' \
LDFLAGS='-L/opt/homebrew/opt/gd/lib -L/opt/homebrew/opt/libpcap/lib -L/opt/homebrew/opt/libpng/lib' \
CFLAGS='-O2 -fgnu89-inline' \
./configure --prefix=/Users/awstme/usr/local
make -j1
PATH="$PWD:$PATH" sh /absolute/path/to/archives/b/bandwidthd/2.0.1-cvs20090917/test_package/test.sh
```

`make -j2` 曾复现 `conf.tab.h` 生成竞态；链接阶段也曾复现 `Credit`、
`FindIp`、`HostIp2CharIp` 未定义。配方分别通过 `make -j1`、
`-fgnu89-inline` 和源级 `extern` 修复固化策略。

## OHOS 边界（2026-08-26 WSL follow-up）

使用 `ci/conan/profiles/ohos-aarch64` 的 WSL `conan create` 已解析并下载
全部目标依赖及 OHOS 构建工具；构建阶段执行 OHOS arm64 `bison` 时失败：

```text
aarch64-binfmt-P: Could not open '/lib/ld-musl-aarch64.so.1'
```

当前配方已移除 `autoconf`/`automake` tool requirements，并直接使用补丁提供的
`configure`，所以本次 configure 已实际通过。使用 Linux build/OHOS host 双 profile
时，ohpcd 没有 Linux x86_64 的 bison/flex binary；改用 WSL 系统 bison/flex 后，
同一配置源码树的 `make -j1` 和最终动态链接通过。

WSL 没有 OpenHarmony 的 musl 动态加载器；尝试使用 Debian musl loader 或 SDK
`libc.so` 作为私有 loader 均发生段错误。因此 WSL 不能执行该 ARM64 ELF，
OHOS/aarch64 的 Conan W3、设备运行和 CI 结果仍必须在 OHOS Worker 上完成，
本报告不将交叉编译链接通过扩大为运行时成功。
