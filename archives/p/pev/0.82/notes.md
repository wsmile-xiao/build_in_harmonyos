# pev 0.82 适配笔记

## 上游与源码

- 项目：pev —— PE 文件分析工具箱。上游仓库已由 `merces/pev` 迁移至
  `mentebinaria/readpe`（前者 2023-04 起清空为指针仓库、无任何 tag；
  `git ls-remote --tags` 实测 v0.82 存在于 readpe）。
- 源码：`https://github.com/mentebinaria/readpe/archive/refs/tags/v0.82.tar.gz`
  sha256 `6ee625acedb3cbe636afe41f854b6eed5aac466d7fad52e3a48557083f8acecc`。
- 许可：GPL-2.0-or-later + LICENSE.OpenSSL（OpenSSL 链接例外）。

## 编译环境
- 构建系统: makefile（纯 Makefile 三层：顶层 → lib/libpe → src → src/plugins）
- 编译日期: 2026-09-21
- 编译器: clang 15.0.4（aarch64 OHOS）
- 依赖: openssl/3.5.6（libpe EVP 哈希与 pesec 的唯一外部硬依赖；
  libpe/libfuzzy/libudis86 均内嵌于源码树，无 submodule）
- 状态: built

## 编译步骤

配方 `build()`（无 configure）：

```bash
make -j1 PLATFORM_OS=Linux CC=<conan clang> \
     CFLAGS="-I<openssl>/include" \
     LDFLAGS="-L<openssl>/lib -Wl,-rpath,<openssl>/lib" \
     AR=llvm-ar
```

- `PLATFORM_OS=Linux`：见下表问题 #1。
- 上游 Makefile 的 `override CFLAGS/LDFLAGS +=` 会把配方传入的值**前置**后追加，
  因此 `-L<openssl>/lib` 先于 `-lssl -lcrypto` 生效，命中 Conan 制品而非系统残留。
- libpe 静态归档（0003/R26）：包内无任何 libpe*.so，插件符号经工具
  `--export-dynamic` 导出的 `.dynsym` 解析。
- `package()` 手工收集：11 个 CLI → `bin/`；5 个输出插件 →
  `lib/pev/plugins/`；`src/userdb.txt` → `share/pev/`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | OHOS 设备 `uname -s` = `HarmonyOS`，libpe.so 与 5 个输出插件**不会被链接**（静默：make 不报错，src 链接 `-lpe` 时才爆） | 上游三处 `PLATFORM_OS := $(shell uname \| cut -d_ -f1)` 的 ifeq 分支只有 Linux/*BSD/GNU/Darwin/CYGWIN，无 HarmonyOS 臂 | `PLATFORM_OS` 为非 override 变量，make 命令行传 `PLATFORM_OS=Linux`（命令行变量优先级最高，随 MAKEFLAGS 传递到全部子 make）；与仓内 abiword-plugin-* 用 `--host=aarch64-unknown-linux-ohos` 三元组覆盖 config.guess 同一口径，零补丁 |
| 2 | 全部 11 个工具运行即 `exit(EXIT_FAILURE)`（若插件目录缺失） | `include/common.h` 的 `PEV_INITIALIZE` 宏：`plugins_load_all()` 对 `opendir(PLUGINSDIR)` 失败返回 -1 → `exit(EXIT_FAILURE)`；text 默认输出也依赖插件；`PLUGINSDIR`/`SHAREDIR` 是编译期 `-D` 常量，而 Conan 缓存在构建后把包目录从 `p/b/<hash>/p` 搬到 `p/<hash>/p`——任何构建期绝对路径烘焙必然悬空 | 补丁 0002：烘焙路径存在时保持原行为，否则经 `/proc/self/exe` 回退到可执行文件相对路径（`../lib/pev/plugins`、`../share/pev/userdb.txt`），包保持可重定位；test_package 的 `readpe -f json` 用例即验证插件 dlopen |
| 3 | 上游 `make install` 会 gzip 压缩 man 页并装符号链接树，且 HMDFS/交叉前缀下行为冗余 | 上游 install 目标为全功能安装 | `package()` 手工按产物收集（bin/lib/plugins/userdb），不调用上游 install；man 页不打包（工具包惯例，commands.json 面向 CLI） |

## 源码修改

- `patches/0001-lib-libpe-error.c.patch`：`lib/libpe/error.c` 的 `strerror_r`
  分支判据由 `_GNU_SOURCE`/`__DARWIN_C_LEVEL` 改为 `__GLIBC__`——musl（OHOS
  libc）即使定义 `_GNU_SOURCE` 也只提供 POSIX 形态 `strerror_r`（返回 `int`），
  原代码按 glibc GNU 形态（返回 `char *`）赋值，clang 报
  `incompatible integer to pointer conversion` 硬错误。musl/BSD/macOS 走
  XSI 形态（写入用户缓冲区）。判据刻意不用 `__OHOS__` 宏（平台宏纪律），
  `__GLIBC__` 是 glibc 专属自定义宏，musl 全形态下均未定义。
- `patches/0002-relocatable-pluginsdir-sharedir.patch`：`include/config.h`、
  `src/config.c`、`src/pepack.c` 新增 `pev_config_baked_or_relocatable()`——
  烘焙路径（`PLUGINSDIR`/`SHAREDIR "/userdb.txt"`）存在时原样使用，否则经
  `/proc/self/exe` 推导 `<exedir>/../lib/pev/plugins`、`<exedir>/../share/pev/userdb.txt`
  回退（仅 `__linux__` 分支启用，非 Linux 行为不变）。动因：Conan 包缓存在
  构建后搬移包目录，编译期烘焙的绝对路径在终态必然失效；DESTDIR/staging
  安装同样受益。
- `patches/0003-libpe-static-r26.patch`：`lib/libpe/Makefile`（Linux 等 POSIX
  分支的共享库链接规则改为 `$(AR) rcs libpe.a`，新增 `AR ?= ar`，clean 补
  `libpe.a`）+ `src/Makefile`（LDFLAGS 追加 `-Wl,--export-dynamic`）。动因：
  设备系统 `/lib64/libpe.so` 已存在（1.4MB，2024-06-06），R26 禁止包内输出
  同名动态库；而插件 dlopen 依赖进程内 `pe_*` 符号，故走「静态 libpe + 导出
  动态符号」组合——动态链接的可执行文件经 `--export-dynamic` 把符号放进
  `.dynsym`，musl 加载器 dlopen 时从全局作用域解析，插件行为不变。
  配方传 `AR=llvm-ar`（R33 同口径）。

## 依赖版本

- openssl/3.5.6（仓内 96 处先例引用的主流版本；libpe 走 EVP API，兼容 3.x，
  仅 `EVP_MD_CTX_init` 等 deprecated 声明告警，无错误）

## 验证结果

见 `reports/test-report.md`（采信轮后回填）：conan create 全链路 +
test_package 烟测 + 上游 `tests/run.sh pe32` 全量用例统计。

## 注意事项

- 包内**不输出任何 `libpe*.so`**（0003 静态化，R26）：产物 = `bin/` 11 工具 +
  `lib/pev/plugins/` 5 插件 + `share/pev/userdb.txt`。
- 插件 .so 未链接 `-lpe`（上游有意）：`pe_*` 符号在 dlopen 时由宿主进程全局
  符号表解析；静态化后依赖 `--export-dynamic` 把工具内符号放进 `.dynsym`。
- test_package 的 PE 样本由 `test_package/pe32_sample.py`（`test()` 经
  `self.run` 实际执行）在**运行期生成**的最小 PE32（2560 字节，.text/.data/.rsrc
  三节 + 最小资源树），不携带二进制夹具入库；该脚本同时是 CI L0c 门禁
  （`build_and_test.sh` 扫 test_package 白名单后缀、排除 conanfile.py）
  所要求的测试源。
---

**编译结束**: 2026-09-21 20:48
**最终状态**: built
