# avr-libc 2.2.1 HarmonyOS 交叉工具链适配知识草稿

> 状态：draft
> 适用范围：在 HarmonyOS/aarch64 主机上使用 Conan 构建 AVR 目标端
> `avr-libc` sysroot。本文只记录 `avr-libc` 2.2.1 直接相关的适配知识。

## 1. 先确认产物边界

`avr-libc` 的构建主机是 HarmonyOS/aarch64，但头文件、CRT 对象和静态库的
目标架构是 AVR。它不是 OHOS 原生 C 运行库，也不能由 OHOS Clang 直接链接。
配方应把它建模为交叉开发资源：

- 使用 `package_type = "unknown"`，避免把包误判为 OHOS 原生 library。
- 清空 `cpp_info.includedirs`、`libdirs` 和 `libs`，不向原生消费者
  注入 AVR 路径。
- 通过 `resdirs = ["avr"]` 和 `AVR_LIBC_ROOT=<package>/avr` 显式暴露 sysroot。
- `test_package` 必须调用 AVR 工具生成 AVR ELF，不能用 OHOS 编译器运行原生
  consumer。

如果忽略这个边界，最常见的后果是 OHOS profile 中的 Clang 覆盖 `avr-gcc`，
或者 AVR 的头文件和静态库进入原生链接路径。

## 2. W0 依赖必须按拓扑拆分

本库所需工具链顺序为：

```text
avr-binutils/2.43.1
        |
        v
avr-gcc-bootstrap/14.2.0 (C-only stage 1)
        |
        v
avr-libc/2.2.1
```

`avr-binutils` 和 `avr-gcc-bootstrap` 是独立 issue/PR 和独立制品，不能把它们的
配方、补丁或源码混入 `avr-libc`。Autotools 则通过已发布的
`autoconf/2.72`、`automake/1.18` `tool_requires` 提供。

阶段一 GCC 只包含 C 前端，没有 `avr-g++` 和 `cc1plus`。因此 C++ 测试缺失
应归因于完整 AVR GCC/C++ 依赖尚未适配，而不是通过修改 `avr-libc` 绕过。

## 3. HMDFS 上的 Autotools 启动问题

上游 tag snapshot 包含 `configure.ac`、`Makefile.am` 和 `bootstrap`，但不包含
生成后的顶层 `configure`。构建必须先执行 bootstrap；在 HMDFS 上需要同时处理
脚本权限、解释器派发和临时目录权限。

### 3.1 不依赖脚本执行位

Conan Autotools 包中的 wrapper 和真实 Perl 脚本在 HMDFS 上可能是 0640，直接
执行会报 `Permission denied`。可靠做法是：

1. 从 `tool_requires` 精确解析 `.autoconf-real`、`.autoheader-real`、
   `.autom4te-real`、`.aclocal-real` 和 `.automake-real`。
2. 用可执行的 HNP Perl 显式解释这些脚本；OHOS 上 M4 使用
   `/data/service/hnp/bin/m4`。
3. `AUTOHEADER` 内部调用 `AUTOM4TE` 时，不能把含参数的整条命令再次作为单个
   引号参数；应保留 `$autom4te --language=autoconf` 的命令展开语义。
4. 对上游 shell 脚本使用 `sh bootstrap`、`sh ./devtools/configure` 和
   `sh ./devtools/gen-avr-lib-tree.sh`，不依赖文件模式位。

### 3.2 保留随机临时目录，但避免 `umask 077`

Autoconf 生成的 `configure` 会用 `umask 077 && mktemp -d` 创建临时目录。
HMDFS 的权限语义可能把该目录变成当前构建进程不可写的 setgid 目录，随后
`config.status` 创建 `subs1.awk` 失败。

修复原则不是使用固定目录，也不是关闭随机化，而是保留
`mktemp -d "./confXXXXXX"`，只让它继承 runner 的常规 umask。`devtools/configure` 和
bootstrap 后生成的顶层 `configure` 都要处理，因为二者各自执行一次
Autoconf 配置流程。

### 3.3 关闭 dependency tracking

HMDFS 上 Automake 依赖文件的原子更新会失败。对 OHOS 构建添加
`--disable-dependency-tracking`；这不减少最终编译的 device/multilib 目录，
只关闭编译期 `.deps` 跟踪。

## 4. `avr-gcc -B` 的 binutils 派发目录

仅把 `avr-as`、`avr-ld` 放入 `PATH` 不够。`avr-gcc -B<dir>/` 会在该前缀下
寻找无前缀的 `as`、`ld`、`nm`，链接时还需要 AVR linker scripts。

配方在 build folder 内建立临时派发根：

```text
.avr-binutils-dispatch/
  bin/
    as    <- avr-as
    ld    <- avr-ld
    nm    <- avr-nm
  avr/lib/ldscripts/
```

然后以 `avr-gcc -B<dispatch>/bin/` 编译。派发目录只服务本次构建和测试，不进入
最终 `avr-libc` 包；工具和 linker scripts 仍由独立的 `avr-binutils` 包负责。

## 5. 完整 multilib 构建的资源策略

`bootstrap` 会生成大量 MCU/device 子目录，完整构建共遍历 470 个递归目录。
真机单线程构建在一小时窗口内无法完成，本次用 `make -j4` 在共享设备上取得
可接受的 CPU 使用和完成时间。不要通过删减 MCU 目录换取速度，否则产物覆盖
和上游测试结论都会失真。

冷缓存运行还可能因源码下载占用约 12 分钟而在安装阶段触发 3600 秒外层超时。
判断这类超时时应先确认编译和测试是否已结束，再用已校验源码缓存重跑完整的
build、test、install、package 和 consumer；不能把仅完成测试的超时运行记为
最终 CI 通过。

## 6. 测试 MCU 与 multilib 必须匹配

上游 `tests/simulate` 有 462 个测试源：406 个 C、53 个 C++、3 个汇编。上游
默认 `runtest.sh` 编译/链接清单只有 338 个，不代表全部可编译源码。

本次 MCU 选择过程给出以下可复用判断：

| MCU | 结果 | 原因 |
|---|---:|---|
| ATmega128 | 无法作为当前基线 | 需要 stage-1 GCC 未提供的 avr51 multilib |
| ATmega328P | 默认清单 334/338 | 4 个 malloc/realloc 源码只支持 ATmega128 或 AT90S8515 |
| AT90S8515 | C/汇编 409/409 | 使用已有基础 multilib，并满足上述 4 个用例的上游条件 |

最终在 `runtest.sh -c` 下显式加入 `util`、`pgmread`、`pgmread-near`、
`pgmread-far` 等非默认目录，编译链接全部 409 个 C/汇编源。结果是：

- 可执行 C/汇编源码：409/409 通过，通过率 100%。
- 全部源码编译链接覆盖：409/462，覆盖率 88.53%。
- 未执行 C++：53 个，原因是独立的 C-only bootstrap GCC 不含 C++ 前端。
- 未执行 AVR 运行时：462 个，原因是 `avrtest`/`simulavr` 尚无独立适配包，
  且 AVR ELF 不能在 OHOS/aarch64 主机原生执行。

后两项是有证据的依赖边界，不是不通过测试。PR 中应分别报告“执行通过率”和
“源码覆盖率”，不能用 100% 通过率掩盖未执行范围。

## 7. consumer 应验证什么

`test_package` 使用包内 ATmega328P 的 CRT、`libc.a`、`libm.a` 和 device archive
实际编译链接 ELF，并进行结构和符号断言：

- `avr-objdump -f` 必须报告 `architecture: avr`。
- `avr-nm -g` 必须包含 `memcpy=T`、`strlen=T`、`sin=W`。
- `sin=W` 是当前链接结果中的预期弱符号，若错误要求强 `T` 会产生假失败。
- consumer 也要建立与配方相同的无前缀 binutils 派发目录，并限制 GCC 返回的
  multilib 相对路径不能逃逸包内 `avr/lib`。

该测试证明 Conan 包可以被 AVR 工具链实际消费，比只检查文件存在更强；但它
仍是编译链接测试，不替代模拟器上的机器码执行。

## 8. 故障定位速查

| 现象 | 优先诊断 | 处理 |
|---|---|---|
| Autoconf/Automake `Permission denied` | 真实 Perl 脚本无执行位 | HNP Perl 显式解释 `.xxx-real` |
| autoheader 无法调用 autom4te | 带参数命令被整体引用 | 修正 `$autom4te` 的命令展开 |
| `config.status` 无法创建 `subs1.awk` | HMDFS 与 `umask 077` 临时目录冲突 | 保留 `mktemp`，继承常规 umask |
| `avr-gcc` 找不到 `as`/`ld` | `-B` 下缺无前缀工具 | 建立临时 dispatch `bin` |
| 链接器找不到脚本 | dispatch 根缺 `avr/lib/ldscripts` | 从 avr-binutils 包复制到临时根 |
| 单线程一小时超时 | 470 目录串行构建 | 使用经过真机验证的 `-j4` |
| ATmega128 测试失败 | 缺 avr51 multilib | 选择依赖已支持且符合源码条件的 MCU |
| 仅 4 个 allocator 用例失败 | MCU 条件不满足 | 使用 AT90S8515，勿误判 libc 回归 |
| consumer 中 `sin` 检查失败 | 弱符号被要求为强符号 | 断言 `sin=W` |

## 9. 最终验证证据与复现

2026-08-21 的 r25 单包 Shadow CI 重新执行完整 470 目录构建、409 个上游
C/汇编编译链接测试、安装打包和 1 个 consumer：

```text
upstream compile/link: 409/409 (100%)
consumer:             1/1 (100%)
executed checks:      410/410 (100%)
source coverage:      409/462 (88.53%)
Build Summary:        Total 1, Success 1, Failed 0
G0=pass L0=pass L1=pass L2=skip L4=pass L5=pass
```

L2 `skip` 只来自文档辅助程序 `avr-man` 不接受 `--version`/`--help`；核心交付物
是 AVR sysroot，已由完整可执行源码集和 consumer 覆盖。

仓库标准单包命令：

```sh
CI_PACKAGES="archives/a/avr-libc/2.2.1" zsh ci/conan/build_and_test.sh
```

详细运行标识、迭代失败原因和覆盖边界见 `../reports/shadow-ci.md`。配方实现见
`../conanfile.py`，consumer 实现见 `../test_package/conanfile.py`。

## 10. 适配复核清单

- [ ] 明确产物是 AVR sysroot，不向 OHOS 原生 `cpp_info` 注入 AVR include/lib。
- [ ] `avr-binutils`、C-only bootstrap GCC 和 `avr-libc` 保持独立 issue/PR。
- [ ] bootstrap 的 Perl/M4、脚本执行位和 HMDFS 临时目录问题均已处理。
- [ ] `avr-gcc -B` 派发根同时包含无前缀工具和 linker scripts。
- [ ] 完整 470 目录构建未被裁剪，并使用真机可承受的并行度。
- [ ] 测试同时报告执行通过率、全源码覆盖率和未执行原因。
- [ ] consumer 生成真实 AVR ELF，并验证架构、CRT/库和关键符号。
- [ ] 真机 CI 使用单包锁和 `CI_PACKAGES`，不扫描全仓。
