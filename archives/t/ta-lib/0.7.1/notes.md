# ta-lib 0.7.1 编译笔记（OHOS PC / aarch64）

## 基本信息
- 上游: https://github.com/ta-lib/ta-lib tag v0.7.1（0.7.x 新系，非 0.6.x SourceForge 老系）
- 构建系统: autotools（tarball 自带 configure，无需 autogen）
- 依赖: 无（纯 C 数学库，仅 libm）
- 许可: BSD-3-Clause

## 下载
- URL: https://github.com/ta-lib/ta-lib/releases/download/v0.7.1/ta-lib-0.7.1-src.tar.gz
- sha256: 508981a5b85edab42ecee0b2d9c7dcd2c4ae9831e859e1aa4e549232734c27e1
- `tar tzf` 完整性验证通过（301 个条目）

## 关键问题与解决方案

### 问题 1: config.sub 不识别 ohos 三元组
- 现象: `configure: error: /bin/sh ./config.sub aarch64-unknown-linux-ohos failed`
  （`Invalid configuration: OS 'ohos' not recognized`）
- 根因: tarball 自带 config.sub 是 2022-01-09 版，OS 列表无 ohos
- 补丁 0001-config.sub-ohos.patch（两处，均验证过）:
  1. 基础 OS 接受列表加 `ohos*`:
     `ohos* | gnu* | android* | bsd* | ...`（advancecomp 0002 同款）
  2. kernel-OS 组合校验加 `linux-ohos*`:
     `| linux-musl* | linux-relibc* | linux-uclibc* | linux-ohos* )`
- 注意: 只加两处其中一处都不够（分别报 OS not recognized / Kernel not known to work with OS）

### 问题 2: config.guess 无法识别 HarmonyOS（预先规避，未触发）
- tarball 的 config.guess（2022-01-09）无 HarmonyOS 分支。
- 规避: configure 显式传 `--build=aarch64-unknown-linux-ohos --host=aarch64-unknown-linux-ohos`，
  guess 探测永不运行（litecoin/codecrypt 先例），无需改 config.guess。

### 问题 3: E114 umask 077 坑（conan 缓存目录下实际触发）
- 现象: conan create 中 config.status 报
  `./confXXXXXX/subs1.awk: Permission denied` → `could not setup config files machinery`
- 根因: configure 的 config.status 模板用 `umask 077 && mktemp -d` 建临时目录；
  HMDFS 上（conan 缓存 ~/.conan2 在 HMDFS）0700 目录即使属主也不可写。
  注意: 探索构建时 $TMPDIR（本地 temp 卷）下未触发，HMDFS 下必触发——环境差异。
- 解决: conanfile build() 中 configure 运行前两处 replace_in_file 拿掉 umask 077
  （codecrypt 1.8 / objfw 1.5.7 先例）:
  1. `tmp=\`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null\`` → `tmp=\`mktemp -d "./confXXXXXX" 2>/dev/null\``
  2. `(umask 077 && mkdir "$tmp")` → `mkdir "$tmp"`

## 构建步骤（探索实测，全部成功）
```bash
chmod 0o755 configure   # tarball 解压为 -rwxrwx---（组执行位），E126
./configure --build=aarch64-unknown-linux-ohos --host=aarch64-unknown-linux-ohos --prefix=<prefix>
make -j1                # E074: HMDFS 无 jobserver fifo
make install DESTDIR=<staging>
```

## 上游测试
- ta_regtest V0.7.1（src/tools/ta_regtest，noinst，随 make 构建）:
  `LD_LIBRARY_PATH=src/.libs ./src/tools/ta_regtest/.libs/ta_regtest`
- 输出 `* All tests succeeded. Enjoy the library. *`（rc=0）
- 覆盖: math/vector/dcperiod/dcphase/trendline/trendmode、全部均线、aroon/correl/beta/midprice、
  cci/willr/ultosc/natr、bop/avgprice、rsi/cmo、imi、min/max/minindex/maxindex/minmax/minmaxindex/midpoint、
  po/apo、adx/adxr/di/dm/dx、sar/sarext、stoch/stochf/stochrsi、mfi/ad/adosc、phasor/sine、trix、
  macd/macdfix/macdext、mom/roc/rocp/rocr/rocr100、trange/atr、stddev/var、avgdev、bbands、
  period boundary、全部 candlestick
- 警告 `Warning: Code profiling not supported for this platform.` 为已知非阻塞（0.6.4 相同）

## conan 配方要点
- in-tree autotools（basic_layout + Autotools），shared 默认 True（0.7.1 ABI 0:0:0）
- 无外部依赖 → requirements() 为空；无 build_requires（tarball 自带 configure）
- package(): DESTDIR staging 一次 install + copy2 字节级拷贝（保 fs-verity 签名，litecoin 先例）；
  剔除 .la（conan 管理依赖信息）
- 上游 ta_regtest 在 build() 内跑（can_run 判断，纯数学本机可跑）
- 产物: include/ta-lib/*.h（6 个头文件含 ta_config.h 生成物）+ lib/libta-lib.so 或 .a
- package_info: libs=["ta-lib"]，cmake_target_name ta-lib::ta-lib，pkg_config_name ta-lib
- ta_regtest 不安装（noinst）→ commands.json 不需要（库类型）

## 产物清单
- lib/libta-lib.so.0.0.0 (+.so.0/.so 符号链接) 或 libta-lib.a
- include/ta-lib/: ta_abstract.h ta_common.h ta_defs.h ta_func.h ta_func_unguarded.h ta_libc.h ta_config.h
- lib/pkgconfig/ta-lib.pc

---
**编译结束**: 2026-09-13
**最终状态**: built（上游回归测试全绿）
