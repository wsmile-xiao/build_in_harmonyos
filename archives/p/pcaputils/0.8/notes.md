# pcaputils 0.8 适配笔记

> 本轮（2026-09-26）：W0 依赖检查、源码/构建系统分析、Conan 配方与
> test_package 准备、**真机 conan create + L1 冒烟验证已通过**。
>
> **当前状态：BUILT-ON-DEVICE — 真机（OHOS aarch64, frp-tip:56267）conan create
> 成功，4 个二进制产出，test_package 冒烟全部通过。无需任何 patch。**

## 真机验证结果（2026-09-26，已通过）

- 设备：HarmonyOS aarch64（frp-tip.com:56267；备选 10.62.178.77:2222 连接超时，未用）。
- 命令：`conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing`（-j1，TMPDIR=$HOME/tmp）。
- 源码 URL：设备上用 Debian orig 地址（Savannah 302→死镜像）；字节与 sha256 与仓库 conandata 一致。
- 构建结果：
  - `pcaputils/0.8` 包构建成功，revision `8d0f3736...`。
  - package() 产出 4 个 ELF aarch64 动态链接二进制（musl ld-musl-aarch64.so.1）：
    - pcapdump 477K、pcapip 510K、pcappick 449K、pcapuc 555K。
  - 链接命令正确注入了 Conan 依赖路径：`-L.../libpcap/p/lib -L.../judy/p/lib ... -lpcap -lJudy`。
- test_package L1 冒烟：`OK: pcapdump/pcapip/pcappick/pcapuc prints usage` →
  `All pcaputils smoke tests passed`。证明动态链接 libpcap/libJudy 成功、二进制可执行。
- **预期的 execinfo.h 问题未出现**：OHOS clang/musl 实际提供了 `<execinfo.h>`，
  util.c 一次编译通过（仅 pcapuc.c 一个 unused-variable warning，无害）。**不需要任何 patch**。
- 内存：设备 23G 内存当时仅剩 ~343M，本包极小（4 个 <600K 二进制，-j1），未触发内存压力。

## 上游信息与源码获取

- 项目：pcaputils（nongnu/Savannah 托管的 pcap 抓包工具集），作者 Robert S. Edmonds。
- 官方发布地址：`https://download.savannah.nongnu.org/releases/pcaputils/pcaputils-0.8.tar.gz`
- 昨日阻塞（Savannah 镜像 404 / waterlan parked / archive.org 不可达）本日的解法：
  从 **Debian pool** 拿到上游原始包 `pcaputils_0.8.orig.tar.gz`（24633 字节）：
  `https://deb.debian.org/debian/pool/main/p/pcaputils/pcaputils_0.8.orig.tar.gz`
- **校验**：本地 sha256 = `7236d896764109b01520fb3e9d8b6ea4622e0a2bfa869968c578b31c2f4624c5`，
  与 Debian PGP 签名的 `pcaputils_0.8-3.dsc`（2026-05-18）中
  `Checksums-Sha256` 记录的 orig tarball 完全一致——即 Debian 2009 年原样导入的上游源码，
  非 Debian 重打包（.orig.tar.gz 是 pristine upstream）。
- conandata.yml 的 `url` 仍写 Savannah 官方地址（R39 官方源优先），sha256 已填真值；
  若 Savannah 在 CI/真机不可达，备用 Debian orig 地址字节相同，可直接替换 url。

## 2. W0 依赖发布检查（已通过）

| 依赖 | 本仓版本 | 状态 | 构建系统 |
|------|----------|------|----------|
| libpcap | 1.10.6 | **published**（cmake） | cmake |
| Judy | 1.0.5 | **published**（autotools，9 个 portability patch） | autotools |

上游 `pcaputils_0.8-3.dsc` 的 Build-Depends：`libpcap0.8-dev`、`libjudy-dev`、
`docbook2x`、`docbook-xml`。docbook* 仅用于生成 doc/ 下的 man/docbook 文档，
本配方不构建 doc/（顶层 Makefile 只 include util/ 和 src/，doc/ 有独立 Makefile 但不被主构建引用），
故关闭文档构建，无需 docbook2x/docbook-xml 依赖。

## 3. 构建系统分析

- **纯 Makefile**（无 configure.ac / CMakeLists.txt / meson.build）。
- 顶层 `Makefile` + `Rules.mk`，子目录 `util/Rules.mk`、`src/Rules.mk`。
- 产物：
  - `util/util.a`：内部静态 helper 库（15 个 .o），**不对外导出**。
  - 4 个 CLI（在 `src/`）：
    - `pcapdump` → `-lpcap`
    - `pcappick` → `-lpcap`
    - `pcapip` → `-lpcap -lJudy`
    - `pcapuc` → `-lpcap -lJudy`
- 关键 Makefile 变量：
  - `CC = gcc`（硬编码，必须命令行覆盖为 clang）
  - `CFLAGS ?= -O2 -ggdb -Wall`（可命令行覆盖）
  - `CF_ALL = $(CFLAGS) -Wextra -std=gnu99 -I.`
  - `LF_ALL = -rdynamic -Wl,--as-needed -Wl,-z,defs`（`=` 赋值，但命令行可覆盖）
  - 链接行 `$(CC) $(LF_ALL) $(LF_TGT) -o $@ $^ $(LL_TGT) $(LL_ALL)`——**没有 LDFLAGS 位**，
    故 `-L` 路径必须通过覆盖 `LF_ALL` 注入。
- **无 install 目标**：配方在 package() 手工 copy 4 个二进制到 `bin/`。
- 无 `make check` / 测试套件（上游无 tests/ 目录）。

## 4. 配方设计要点（conanfile.py）

- `package_type = "application"`，`requires libpcap/1.10.6` + `judy/1.0.5`。
- build() 从 `self.dependencies[...].cpp_info` 取 include/lib 目录，在命令行注入：
  - `make CC=clang AR=llvm-ar -j1 CFLAGS='-O2 ... -I<...>' LF_ALL='-rdynamic -L<...> ...'`
  - 符合 R33（不依赖 shell 环境变量，编译器/标志来自 Conan）。
- package() 把 `src/{pcapdump,pcapip,pcappick,pcapuc}` 拷到 `package_folder/bin`。
- package_info 只声明 `bindirs=["bin"]`（无对外库）。
- 软件级 `commands.json` 已按 R38 创建（type=tool）。

## 5. 已知/预期的真机首编问题（未真机编译，静态分析推断）

1. **`util/util.c` 包含 `<execinfo.h>` 并调用 `backtrace()`/`backtrace_symbols_fd()`**：
   这是 glibc 扩展，musl/OHOS 无此头文件，会直接编译失败。
   但 `util_print_backtrace()` 在整个代码库中**只有定义和声明、无任何调用点**（死代码）。
   → 真机首编预计在此报错；修复方式：打 patch 删除该函数体（或 `#ifdef __GLIBC__` 守卫），
   然后用 `refresh-patch --auto` 固化为 `patches/0001-no-execinfo.patch`。
2. `<endian.h>`：musl 提供，预计无碍。
3. `daemon(0,0)`（daemon.c）：POSIX，musl 提供，预计无碍。
4. 无 libm 调用（grep 确认），不需要 `-lm`。

## 6. test_package 设计（实质冒烟，非空壳）

- `test_package/conanfile.py`：`requires(tested_reference_str)`，generators=VirtualRunEnv，
  test() 执行 `sh test.sh`。
- `test.sh`：对 4 个二进制逐个无参数运行。上游参数解析在缺少抓包源时会打印
  `Usage: <tool> <options>` 到 stderr 并以 EXIT_FAILURE 退出。脚本 grep 断言输出含 `Usage:`。
  这证明：二进制是 OHOS ELF、动态链接 libpcap/libJudy 成功（否则 loader 直接崩）、
  到达了自身参数解析代码路径。
- `MANIFEST.yml` 声明 upstream test_type=none（上游无测试套件）。

## 7. 本机已完成的验证

- [x] 源码 tarball 下载成功（Debian pool），sha256 与 PGP 签名 .dsc 一致。
- [x] 解包确认目录结构、Makefile、4 个 CLI、内部 util.a。
- [x] W0：libpcap/1.10.6、judy/1.0.5 在本仓均为 published。
- [x] conanfile.py / conandata.yml / test_package/{conanfile.py,test.sh,MANIFEST.yml} /
      commands.json 已写。
- [ ] conanfile.py 语法（本机无 OHOS conan，仅做 python 编译检查——见下）。
- [ ] 真机 conan create / shadow CI（本轮不做，等真机窗口）。

## 8. 下一步真机 / shadow CI 命令（源码就绪后）

```sh
# 0) SSH 到真机（项目 AGENTS.md）
ssh -T -p 56267 -i ~/.ssh/id_rsa currentUser@frp-tip.com

# 1) 单包 shadow CI（必须用 CI_PACKAGES，勿裸跑全仓）
CI_PACKAGES="archives/p/pcaputils/0.8" zsh ci/conan/build_and_test.sh

# 或隔离 conan create 直验（profile：ohos-aarch64）
$HOME/.local/bin/conan create archives/p/pcaputils/0.8 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing
```

真机注意事项（来自避坑指南，首轮必查）：
- 远端命令整体用单引号包住；`/tmp` 只读，临时文件写 `$HOME/tmp/`，设 `TMPDIR`/`TMPPREFIX`。
- `--try-lock` 返回 75 = 真机忙，错峰重试，不强抢。
- runner stdout 为空时看 `$HOME/ohos-test-runs/<RUN_ID>/logs/`。
- 首编预计在 `util/util.c` 的 `<execinfo.h` 处失败 → 打 stub patch 后 `refresh-patch --auto` 固化。

## 9. 阻塞点小结

- 无外部硬阻塞：源码已拿到、依赖已发布、配方已就绪。
- 待真机窗口做：conan create 验证 + 修复 execinfo.h patch + L1 冒烟 + shadow CI 单包。
- 分支：`feat/pcaputils-0.8`，worktree：`D:\harmonyos\worktrees\pcaputils`。
