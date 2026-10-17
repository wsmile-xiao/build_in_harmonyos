# zlib 1.3.2 验证报告（上游测试 + test_package）

## 环境

- OpenHarmony / HarmonyOS PC（aarch64，真机）：`uname -a` → `HarmonyOS localhost HongMeng Kernel 1.12.0 #1 SMP ... aarch64 Toybox`
- 编译器：clang 15.0.4，默认目标三元组 `aarch64-unknown-linux-ohos`
- Conan 2.29.1（OHOS 适配版），profile `ci/conan/profiles/ohos-aarch64`
- 源码：`zlib-1.3.2.tar.gz`，sha256 `bb329a0a2cd0274d05519d61c667c062e06990d72e125ee2dfa8de64f0119d16`（官方值）
- 构建配置：`./configure --static --prefix=/`，`CC=clang`，`CFLAGS="-fPIC -O2"`，`make -j1`

## 1. 上游测试（实际执行）

### 1.1 测试入口核验

`Makefile.in` 中：

```
check: test
test: all teststatic test64        # ./configure --static 后改写（SHAREDLIB 为空）
teststatic: static                 # echo hello world | ./minigzip | ./minigzip -d && ./example
test64: all64                      # echo hello world | ./minigzip64 | ./minigzip64 -d && ./example64
testshared: shared                 # 仅 shared 配置进入 test 目标；--static 下 SHAREDLIB 为空
```

> 说明：上游 `Makefile.in` 原始 `test:` 为 `all teststatic testshared`，`configure --static`
> 会把 `SHAREDLIB/SHAREDLIBV/SHAREDLIBM` 置空并把 `test:` 改写为 `all teststatic test64`
> （生成的 `Makefile` 第 75/81 行：`all: static all64`、`test: all teststatic test64`）。
> 因此 `make check` 在静态配置下实际执行 teststatic + test64；`testshared`（examplesh/minigzipsh）
> 不参与，单独执行必然失败（无 libz.so），不属于本次测试范围。

### 1.2 测试命令与结果

| 命令 | 日志 | 退出码 |
|------|------|--------|
| `make check` | `evidence/21-make-check.log` | 0 |
| `make teststatic` | `evidence/22-make-teststatic.log` | 0 |
| `make test64` | `evidence/24-make-test64.log` | 0 |
| `clang -fPIC -O2 -I. -o infcover test/infcover.c libz.a && ./infcover` | `evidence/25-infcover.log` | 0 |
| `make testshared`（--static 下不适用，仅作记录） | `evidence/23-make-testshared.log` | 2（无 libz.so，非本配置用例） |

### 1.3 逐项用例统计（所有上游样例，无漏测）

| # | 用例（上游样例） | 来源文件 | 触发目标 | 结果 |
|---|------------------|----------|----------|------|
| 1 | `minigzip` 往返压缩/解压（`echo hello world \| ./minigzip \| ./minigzip -d`） | test/minigzip.c | teststatic | PASS |
| 2 | `example` 全功能演示（uncompress/gzread/gzgets+seek/inflate/large_inflate/inflateSync/字典） | test/example.c | teststatic | PASS |
| 3 | `minigzip64` 往返压缩/解压（`-D_FILE_OFFSET_BITS=64`） | test/minigzip.c | test64 | PASS |
| 4 | `example64` 全功能演示（64 位大文件模式） | test/example.c | test64 | PASS |
| 5 | `infcover` inflate/inflateBack 全覆盖用例（76 条用例行） | test/infcover.c | make cover 的测试程序（make check 之外，本次一并执行） | PASS |

- 用例总数：5（程序级；其中 4 项由上游 `make check` 驱动，1 项为上游 `make cover` 的测试程序）
- 通过：5
- 失败：0
- 跳过：0
- `example`/`example64` 内部逐项输出（均 OK）：`uncompress()`、`gzread()`、`gzgets() after gzseek`、
  `inflate()`、`large_inflate()`、`after inflateSync()`、`inflate with dictionary`
- `make check` 汇总输出：`*** zlib test OK ***` + `*** zlib 64-bit test OK ***`
- `infcover` 输出 76 条用例行（`inflate init`、`prime`、`bad gzip method` … `copy direct from output`），
  无断言失败、退出码 0

## 2. test_package（消费者视角）

| 测试 | 源文件 | 命令 | 用例数 | 通过 | 失败 | 跳过 |
|------|--------|------|--------|------|------|------|
| 静态库消费者冒烟 | test.c | `./test_probe` | 1 | 1 | 0 | 0 |
| 鸿蒙特有测试 | test_ohos.c（+ ohos_pic_probe.c） | `./test_ohos ./libz_ohos_probe.so` | 14 | 14 | 0 | 0 |

鸿蒙特有用例明细（`test_ohos.c`）：

- D1 编译期 `__OHOS__` 断言（目标 `aarch64-linux-ohos`）
- D2 `uname().sysname == "HarmonyOS"`（确证跑在鸿蒙运行时）
- D3 `zlibVersion() == "1.3.2"`
- D4.1–D4.4 `deflateInit`/`deflate(Z_FINISH)`/`inflateInit`/`inflate` 往返一致
- D5.1–D5.4 `compress2`/`uncompress` 往返 + crc32（0xCBF43926）/adler32（0x091E01DE）标准向量
- D6.1–D6.3 由静态 `libz.a` 编成的 `.so` 探针 dlopen/dlsym/取值 —— 验证 `libz.a` 为 PIC，
  可被下游共享库吸收（本配方 OHOS 适配的核心结论）

## 3. 门禁结果

| 门禁 | 命令 | 结果 |
|------|------|------|
| conan create（强制重建） | `conan create archives/z/zlib/1.3.2 -pr:h=... -pr:b=... --build=zlib/1.3.2` | exit 0，无 ERROR |
| conan-verify | `ohc-run.py conan-verify zlib 1.3.2` | exit 0，G0–G4 + L2/L4/L5 全 PASS |
| W3 本地 CI 模拟 | `ohc-run.py finish`（内含 `ci/conan/build_and_test.sh`） | exit 0，`.ci-result.json` = `{"exit_code": 0, ...}` |

## 4. 结论

上游 `make check`（teststatic + test64）与额外上游样例 `infcover` 全部执行并通过；
test_package 15 项检查（含 14 项鸿蒙特有检查）全部通过；conan create / conan-verify / W3 全绿。
本配方可在 OpenHarmony aarch64 上消费。
