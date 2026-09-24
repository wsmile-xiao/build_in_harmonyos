# nacl 20110221 适配笔记

## 编译环境
- 构建系统: 上游自带 `./do` 探测式脚本（无 makefile / configure / cmake / autotools）
- 编译日期: 2026-09-22
- 编译器: clang 15.0.4（aarch64-unknown-linux-ohos，OHOS SDK 26.0.0.18）
- 真机: HarmonyOS PC aarch64，`CONAN_HOME=~/work/psj/ch-nacl`
- 状态: built

## 编译步骤
```sh
conan create archives/n/nacl/20110221 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing --build=nacl
```
配方 `build()` 里依次做三件事，全部有产物断言：
1. `apply_conandata_patches` + `sh do`（上游一体化构建：探测编译器 → 逐实现编译 →
   跑 `crypto_*/try.c` 与 `crypto_*/*/checksum` 对拍 → 只把通过且最快的实现归档 →
   编 `commandline/` 与 `tests/` 并与 `.out` 对拍 → curvecp）
2. 定位 `build/<短主机名>/{lib,include}/default`，解析 `data` 里逐实现的自检结论并打印
3. 生成 `n5525_upstream_tests.sh`，把 `tests/` 下 53 个程序（31 个 `.c` + 22 个 `.cpp`）
   按上游链接方式（`libnacl.a` + 树内 `cpucycles.o`/`randombytes.o` + `-lm`）逐个编译、
   运行，stdout 与 `tests/<name>.out` **逐字节**比较；任一偏差直接让 create 失败

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `./do` 18 秒退出、`libnacl.a` 只有 1KB 桩、`include/` 空 | `okcompilers/{c,cpp,archivers}` 探测表只有 `gcc -m64/-m32`、`g++`、`spu-gcc` 和 AIX `ar -X64`，OHOS 只有 clang；探测不到编译器 → `okabi` 为空 → 后面所有循环零次 | 补丁 0001：c/cpp 各加**一行** clang（多行会按每个编译器建一个 ABI 把整套构建重复多遍），archivers 追加 `llvm-ar`（保留 `ar`，逐个试） |
| 2 | `find: bad arg '-name'`，实现目录一个都找不到 | toybox `find` 不支持 `-follow`（`./do` 用它发现 `api.h`） | 补丁 0002：去掉 `-follow`。官方 tarball 内 **0 个符号链接**（`tar tvjf \| grep -c '^l'` = 0），文件集合不变 |
| 3 | `crypto_int32.h`/`crypto_int64.h` 不生成，37 个实现全部编译报错 | `inttypes/crypto_int32.c` 靠有符号自增溢出（`x+=x` 直到 0）判断宽度；clang `-O2` 按「有符号溢出是 UB」折叠掉，探测程序返回 100 | 补丁 0001 的 clang 行带 `-fwrapv`（djb 系软件的标配，libmceliece 同理） |
| 4 | `lib/default/cpucycles.o` 缺失 → 所有 `try` 链接失败 → `libnacl.a` 归档 0 个实现 | `cpucycles/do` 的候选后端在 OHOS 全军覆没：`monotoniccpuinfo`/`monotonic` 要 `<sys/sysctl.h>`（musl 无），`gettimeofday` 能编但 `osfreq()` 读不到频率返回 0 → `cpucycles()==0` → `test.c` 判 100 | 补丁 0003：`monotonic.c` 去掉 BSD `sysctlbyname`，改 `osfreq()`，取不到时按 `CLOCK_MONOTONIC` 纳秒记 1e9 |
| 5 | 上游 53 个测试只跑得了 33 个 | 22 个 `.cpp` 里有 20 个写裸 `main()`：C 侧只是 implicit-int 警告，C++ 侧 clang 判 **硬错误** `a type specifier is required for all declarations` | 补丁 0004：给 20 个上游测试程序补 `int main()`（不改任何断言与输出；实测 22/22 全通过） |
| 6 | 消费者缺 `randombytes` / `cpucycles_*` 符号 | `./do` 的链接方式本来就是 `libnacl.a` + `lib/default/{cpucycles,randombytes}.o` 三个对象，那两个 `.o` 不进归档；`crypto_box_keypair`/`crypto_sign_keypair` 确实引用 `randombytes` | `package()` 用 `do` 实际选中的同一个 ar（读 `bin/okar-default`）把两个 `.o` 合入交付的 `libnacl.a` → 消费者只需 `-lnacl -lm` |
| 7 | `Package ... folder must exist` / 半死缓存 | 并发 create 被中断会把 `CONAN_HOME` 打成「有元数据无目录」 | 设备侧 runner 先 `pgrep -f "conan create"` 排队（每 10 分钟轮询，等到空闲才起），且本会话用独立 `ch-nacl`，共享 `~/.conan2` 只读 |
| 8 | 生成的测试驱动里 `-I` 只有一个生效 | toybox sh 把未加引号的 `INCS=-Ia -Ib` 解析成「赋值 + 执行命令 `-Ib`」，于是第二个 `-I` 变成命令名报 `inaccessible or not found` | 驱动脚本的多词赋值统一加引号（`INCS="-Ia -Ib"`），命令处仍用不带引号的展开做分词 |

## 依赖
- **无外部依赖**（R36 空 `requires`）。nacl 树内自带 `cpucycles/`、`randombytes/`、`inttypes/`
  三套可移植后端，全部编进 `libnacl.a`。
- 制品仓的 `libcpucycles/20260625`（上游 `cpucycles.cr.yp.to`）与本库无构建关系：
  本库用树内 `cpucycles/monotonic.c`，导出符号 `cpucycles_monotonic*`，
  与外部 libcpucycles 的 `cpucycles` 函数指针不同名，不冲突；
  但同一 TU 同时包含两套 `cpucycles.h` 时以先包含者的宏为准，不要混用。

## 交付产物
- `lib/libnacl.a`（含树内 randombytes/cpucycles 对象，静态）
- `include/nacl/*.h`（42 个头：11 个 operation 级 `crypto_*.h` + 逐实现 `crypto_*_<primitive>.h`
  + `crypto_int*.h`/`crypto_uint*.h` + `randombytes.h` + `cpucycles.h`）
- `cpp_info.libs = ["nacl"]`，`system_libs = ["m"]`，`includedirs = ["include","include/nacl"]`
- 不打 `bin/`（库，L0k 不要求 commands.json；上游 `commandline/nacl-sha256`、`nacl-sha512`
  只是随 `./do` 构建的示例工具）

## 验证结果（真机 HarmonyOS PC aarch64）
```
CREATE_EXIT:0
N5525_UPSTREAM_TESTS runnable=53 pass=53 fail=0 nolink=0
nacl consumer checks=59 failures=0        # test_package/test.c
nacl c++ consumer checks=20 failures=0    # test_package/test.cpp
```
上游 `./do` 逐实现自检（`build/*/data`，字段 7 = try / tryfails）：
```
N5525_TRY selfcheck_ok=26 selfcheck_mismatch=0 selfcheck_unknown=1 build_or_run_rejected=0
```
另有上游 measure 写出的 1351 条计时记录（`cycles`/`xor_cycles`/`verify_cycles`/`open_cycles`）。

## 注意事项
- 版本 `20110221` 就是上游 tarball 文件名（`https://hyperelliptic.org/nacl/nacl-20110221.tar.bz2`，
  sha256 `4f277f89735c8b0b8a6bbd043b3efb3fa1cc68a9a5da6a076507d067fc3b3bf8`），
  真机与本机 md5 对拍一致（`7efb5715561c3d10dafd3fa97b4f2d20`），不存在「用 main 顶替」问题。
- `./do` **对任何失败都只记日志并 0 退出**，所以退出码 0 不代表构建成功；配方必须自己断言
  `build/*/lib/*/libnacl.a` 存在、`try` 计数、以及 53 个测试的逐字节对拍结果。
- `tests/` 里 `core*`（Salsa20 内核）等程序包含的是各原语专用头，靠 `used`/`selected`
  标记决定哪些实现进归档：`crypto_core`/`crypto_scalarmult`/`crypto_verify` 没有 `selected`
  → 不生成 operation 级头，消费者必须用 `crypto_scalarmult_curve25519.h` 这类专用头
  （配方与消费者测试都按上游做法）。
- CI worker 上没有 `~/work/shared/bin` 那套 ar/ranlib/ld shim；配方不假设它们：archiver 取自
  `do` 实际探测成功的 `bin/okar-<abi>`，编译器取自 `tools.build:compiler_executables`
  （CI profile 指向 `/data/service/hnp/bin/clang`），探测表里 `ar`/`llvm-ar` 都会各试一次。
- 上游 `crypto_sign` 的 `try` 自检按 checksum 对拍通过（本次 `randombytes` 走 `/dev/urandom`），
  `tests/` 没有 sign 程序；本配方的消费者测试补了 keypair/sign/open + 篡改与错 pk 两条负向用例。
