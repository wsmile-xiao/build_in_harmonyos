# codecrypt 1.8 适配笔记

## 编译环境
- 构建系统: autotools（tarball 无 configure，`bash autogen.sh` 引导生成 Makefile.am + configure）
- 编译日期: 2026-09-09
- 编译器: clang/clang++ 15.0.4 (OHOS SDK)
- 状态: published
- 设备原生探索编译成功 + ccr 二进制全功能实测通过

## 编译步骤

```bash
# 依赖环境（conan，全部制品仓已有二进制）
conan install --requires=gmp/6.3.0.1 --requires=fftw/3.3.11 \
  --requires=cryptopp/8.9.0 --tool-requires=automake/1.18 \
  --tool-requires=libtool/2.5.4 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64

# 引导（tarball 无 configure）
bash autogen.sh

# configure：显式传 triplet 绕过 config.guess 探测
# （config.guess 不识别 HarmonyOS，且 HMDFS tmp 目录下编译器探测会失败）
export CRYPTOPP_CFLAGS="-I<cryptopp>/include"   # pc 名 libcrypto++ vs cryptopp 不匹配
export CRYPTOPP_LIBS="-L<cryptopp>/lib -lcryptopp"
export LIBS="-lfftw3 -lgmp -lcryptopp -lm"       # 不用 AutotoolsDeps 的（含 -lgmpxx）
./configure --prefix=<prefix> --build=aarch64-unknown-linux-ohos --host=aarch64-unknown-linux-ohos

make -j1      # E074: HMDFS jobserver fifo EPERM，必须单线程
make install
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `configure: error: cannot run C compiled programs` (conftest) | conftest 链接共享 gmp/fftw 后运行时加载不到（无 RPATH），且 AutotoolsDeps LIBS 含 `-lgmpxx`（C++ 绑定需 libc++，C 程序加载失败） | LD_LIBRARY_PATH 前置依赖 lib 目录 + LIBS 覆盖为 `-lfftw3 -lgmp -lcryptopp -lm`（codecrypt 只用 C API） |
| 2 | `config.status: could not setup config files machinery` (Permission denied) | E114: HMDFS setgid 把 `umask 077 && mktemp -d` 建的 0700 目录变成 drwx--S---，owner 也不可写 | 生成后替换 configure 中的 `umask 077` 两处（同 abiword/aaphoto 方案） |
| 3 | `src/pwrng.cpp:53: error: use of undeclared identifier 'getpass'` | OHOS musl 无 `readpassphrase.h` 也无 `getpass(3)` | 补丁 0001：`#elif !defined(HAVE_GETPASS)`（特性宏守卫，无平台宏）内联 termios 版 ohos_readpassphrase()（上游注释明示此方案） |
| 4 | `aclocal: Can't locate Automake/Config.pm` | automake/1.18 conan 包的 perl 模块不在默认 @INC | VirtualBuildEnv 自动设置 PERL5LIB/ACLOCAL（配方无需手工处理） |
| 5 | `PKG_CHECK_MODULES([CRYPTOPP],[libcrypto++])` 找不到包 | conan cryptopp 包的 pc 文件名是 `cryptopp.pc` | PKG_CHECK_MODULES 优先采用 CRYPTOPP_CFLAGS/CRYPTOPP_LIBS 环境变量，配方中直接喂路径 |
| 6 | ccr 密钥生成卡在 "Gathering random seed bits" | 默认读阻塞型 `/dev/random` | 测试/CI 用 `CCR_RANDOM_SEED=/dev/urandom` |
| 7 | FMTSEQ h20 变体密钥生成 >10 分钟 | Merkle 树深度 20 一次性密钥预计算量大 | 测试用 h10 变体（FMTSEQ128C）或 SYM 对称路径；非阻塞问题 |

## 源码修改

- `patches/0001-pwrng-OHOS-readpassphrase.patch`（portability）
  - `src/pwrng.cpp`：`#elif !defined(HAVE_GETPASS)` 特性宏分支内联 termios 版 readpassphrase
    （关回显、恢复终端状态；open /dev/tty 失败回退 /dev/stdin）

## 依赖版本

- gmp/6.3.0.1（制品仓）
- fftw/3.3.11（制品仓）
- cryptopp/8.9.0（制品仓，静态 libcryptopp.a）
- automake/1.18 + libtool/2.5.4（tool_requires，制品仓）

## 验证结果

```bash
# 设备原生实测（探索阶段）
$ ./ccr -V
codecrypt 1.8
$ ./ccr -g help | wc -l          # 26 算法全部注册（含 cryptopp SHA/RIPEMD/TIGER 变体）
26+别名/修饰符
$ ./ccr -k                        # MCE + FMTSEQ 密钥生成成功
pubkey  MCEQCMDPC128FO-CUBE256-ARCFOUR   @f406e70e... alice-enc
pubkey  FMTSEQ128C-CUBE256-CUBE128        @ff44afa4... alice-sig
$ echo msg | ./ccr -e -r alice-enc -a; ./ccr -d -a   # 加解密往返 OK
$ echo doc | ./ccr -s -u alice-sig -a; ./ccr -v -a   # 签名验证 "GOOD signature ;-)"
$ ./ccr -S sym.key -g SYM; ccr -S sym.key -e/-d       # 对称往返 OK（test_package 路径）
```

## 上游测试情况（rule4 / N 核验）

上游 v1.8 tarball **无测试套件**：
- src/ 全为产品源码（34 个 .cpp），无 tests/ 目录
- configure.ac / autogen.sh 生成的 Makefile.am 只有 `bin_PROGRAMS = ccr`，无 TESTS/check_PROGRAMS
- `make check` 注册测试数 N = 0（实测）
- 上游仓库无 CI 测试工作流

→ 上游测试 N = 0，test_package 用 ccr 二进制功能实测代替（版本 + 26 算法套件 + 对称加解密往返，R34 实质执行被测包）。

## 注意事项

- 产物是单一 `ccr` CLI（application，无库），commands.json 已在软件级声明（R38）
- cryptopp 保持启用（制品仓已有），全 26 算法可用；如需瘦身可 `--without-cryptopp`（减至 12 算法）
- 测试断言 12 条（版本 1 + 算法 8 + 对称往返 3）
---

**编译结束**: 2026-09-10 00:05
**最终状态**: built
