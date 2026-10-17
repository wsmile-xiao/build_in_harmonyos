# coinor-vol 1.5.4 适配笔记

## 编译环境
- 构建系统: autotools（COIN-OR 递归 configure：顶层 + Vol/ 子目录）
- 编译日期: 2026-09-08
- 编译器: clang/clang++ (15, libc++)
- 状态: built（配方门禁 conan-verify G1-G4 全部 PASS）

## 编译步骤

1. 下载源码: `https://github.com/coin-or/Vol/archive/refs/tags/releases/1.5.4.tar.gz`
   - SHA-256: `93c2afff8ce920de964fee5e679f5c11de3c3f472ebccde62fb513d8d3a9f467`
2. 最小补丁（patches/，由 conanfile.py 的 apply_conandata_patches 应用）：
   - `0001-config.guess.patch` / `0003-Vol-config.guess.patch`：给 2007 版 config.guess
     增加 HarmonyOS (HongMeng) 与 aarch64 Linux 分支（顶层 + Vol/ 子目录各一份）
   - `0002-config.sub.patch` / `0004-Vol-config.sub.patch`：给 2007 版 config.sub
     增加 aarch64 CPU 与 linux-musl OS 识别（3 处，顶层 + Vol/ 子目录各一份）
   - `0005-register-remove.patch`：移除 VolVolume.hpp 中 C++17 已废弃的
     `register` 存储类说明符（3 处：VolMax/VolAbs 模板与 factor() 局部变量），
     否则 clang -std=c++17 下编译失败，且消费者包含头文件时同样受影响
3. configure（关键命令）：
   ```bash
   ./configure --prefix=$DEFAULT_PREFIX --build=aarch64-unknown-linux-musl \
     --disable-shared --enable-static --disable-dependency-tracking
   ```
4. 修补 config.status（顶层 + Vol/）后重跑：mktemp→mkdir -p ./conftmp、umask 077→022
5. `make -j1`
6. `make install`（conan 打包用 autotools.install()）
7. 依赖恢复验证（上游测试入口 osiUnitTest）：以已发布依赖 coin-or/0.108.12 +
   coinutils/2.11.13 增量配置 --with-osi-*/--with-ositests-*/--with-coinutils-*，
   修复 conan relocatable 破坏的 .la 绝对路径（//lib/libCoinUtils.la 等）后
   `make -j1` 成功构建 libOsiVol.a 与 osiUnitTest；运行因外部测试数据包
   COIN-OR Data/Sample（exmip1.mps）不可得而阻塞（registry 无包、官方源 404），
   详见 reports/upstream-test-ledger.md

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 HarmonyOS/aarch64 | 2007 版脚本过旧 | 最小补丁：config.guess 加 HarmonyOS/aarch64 分支、config.sub 加 aarch64/musl 支持（顶层 + Vol/ 各一份） |
| 2 | config.status 报 `confstat*/out: Permission denied` | HMDFS umask/mktemp | sed 修补：mktemp→mkdir -p ./conftmp、umask 077→022，重跑 config.status |
| 3 | clang -std=c++17 下 `register` 关键字报错 | 上游代码使用 C++17 已移除的 register 说明符 | 0005 补丁移除 VolVolume.hpp 中 3 处 register（同时保证消费者可包含头文件） |
| 4 | osiUnitTest 链接 `//lib/libCoinUtils.la` 无效 | conan relocatable 打包改写 .la dependency_libs 绝对路径 | build() 中恢复 .la 内真实绝对路径（coin-or/coinutils 包） |
| 5 | osiUnitTest 运行 Coin6001E 数据缺失 | 外部测试数据包 Data/Sample 不在 registry 且官方源不可达 | 记录为真实外部数据阻塞 + 恢复条件，见测试台账 |

## 源码修改

- `patches/0001-config.guess.patch` / `0003-Vol-config.guess.patch`：HarmonyOS/aarch64 识别
- `patches/0002-config.sub.patch` / `0004-Vol-config.sub.patch`：aarch64/musl 识别
- `patches/0005-register-remove.patch`：移除 register 关键字（C++17 兼容）

## 依赖版本

- 核心 libVol：无强制第三方依赖（CoinUtils/Osi 仅用于可选 OsiVol 接口与测试）
- 可选测试依赖（restore 验证用，已发布在 ohpcd）：coin-or/0.108.12、coinutils/2.11.13、zlib

## 验证结果

### 1. 本地编译与安装（rc=0）
```bash
./configure --prefix=... && make -j1 && make install DESTDIR=...
# 产物: libVol.a, include/coin/VolVolume.hpp, lib/pkgconfig/vol.pc
```

### 2. Conan 配方门禁（ohc-run.py conan-verify，G1-G4 全 PASS）
- G1 配方完整性: PASS
- G2 conan create 干净构建（含 test_package 消费者测试）: PASS
  - test_package 真实调用 VOL_problem::solve（TinyHook 单约束子问题），1/1 Test Passed
- G3 系统同名库隔离 (R26): PASS
- G4 产物完整性: PASS

### 3. HarmonyOS 专项测试用例（tests/ohos_test.cpp，真实可执行）
```bash
clang++ -std=c++17 -stdlib=libc++ -Wall -I Vol/inc -I Vol/src \
  -I <coinutils>/include/coin Vol/test/ohos_test.cpp Vol/src/.libs/libVol.a \
  -lm -o $TMPDIR/ohos_test_coinorvol
$TMPDIR/ohos_test_coinorvol   # rc=0
```
输出: `OHOS TEST PASS: coinor-vol 1.5.4 volume algorithm on HarmonyOS (value=0.000000 dual[0]=0.000000 primal[0]=0.835282 viol[0]=0.164718 rc=0)`
- 断言 5 项：solve rc=0、三向量齐备、拉格朗日值/对偶/原始解均有限、值域合理、数值极限正常
- 源码 SHA-256: `7c8964ea4e7710701dd4f082e6346adce07b3f958d46d4cc2d1b486df92dd763`
- 二进制 SHA-256: `2a2cd8331aec6d3642fb70fae88dd98258d20e62adec0da13aff1604ed7f02b2`
- 运行日志 SHA-256: `6621d72c5d8d999a966ffea4f129416d0b1bcba7424fbe95afe0c131fe3595af`

### 4. 上游测试台账
详见 `reports/upstream-test-ledger.md`：全量通过率 0/1=0%
（唯一独立上游用例 OsiVolSolverInterfaceUnitTest 受 COIN_HAS_OSITESTS 门控，
默认配置未实例化；恢复构建成功后运行因外部 Data/Sample 数据包不可得阻塞，
非当前库适配缺陷）
---

**编译结束**: 2026-09-08 11:44
**最终状态**: built

---

## R02 补记（CI configure 失败归因与修复，2026-09-09）

### CI 失败现象（PR #8922，构建 #42277）

- 官方归档经 gh-proxy 镜像下载、解压、5 个补丁应用全部成功
- `configure` 在首个 C 编译器测试处失败：
  `checking for C compiler default output file name... configure: error: C compiler cannot create executables`
- conan `build()` 返回 Error 77；CI 输出不含 config.log 首个错误

### 本地等价复现（同一官方 tarball sha256=93c2afff...，同一 configure 命令）

| 环境 | TMPDIR | 结果 | config.log 首错 |
|------|--------|------|-----------------|
| 可写目录 | `$HOME/tmp` | 通过（a.out / works yes） | — |
| 只读目录（复现 CI） | `/tmp`（erofs 只读） | **Error 77，同一 configure 行** | `clang-15: error: unable to make temporary file: Read-only file system` |
| 不存在目录（复现 CI） | `$HOME/tmp/不存在` | **Error 77，同一 configure 行** | `clang-15: error: unable to make temporary file: No such file or directory` |

- 复现日志：`/storage/Users/currentUser/tmp/r02-evB/runB.log`（rc=77）、
  `/storage/Users/currentUser/tmp/r02-evC/runC.log`（rc=77）
- config.log SHA-256：RUN_B `d279d58bdabc3456ba5dfe31a39fa248abcc2428b5e688986f97c9a51519e10a`、
  RUN_C `f72d1e1b233f0206e92bd39f02148957cfb45a90f71cc2a75cee2ce8623de368`

### 根因与责任归属

- **根因**：配方 `build()` 把 `TMPDIR` 硬编码为 `$HOME/tmp`（E002 建议的 HMDFS
  规避），但 CI worker 沙箱下该路径不存在或不可写；clang 创建临时文件失败 →
  configure 首个编译测试 `C compiler cannot create executables` → Error 77
- **责任**：当前库配方构建配置（TMPDIR 选择未验证可写性），非 CI 工具链/sysroot/
  链接器/权限环境的独立缺陷；编译器本身（clang 15.0.4）可用（`--version` rc=0）
- **curl 缺失**仅使预下载告警（`No such file or directory: 'curl'`），conan 自动
  回退官方/镜像下载，与本次失败无关

### 最小修复（conanfile.py build()）

- 候选 TMPDIR：`$HOME/tmp` → conan `build_folder/.tmp`（CI worker 可写）
- 用**真实文件写入探测**（HMDFS 忽略 chmod 与 `os.access(X_OK)`，见 E046/R49）
  验证候选可写，失败则回退下一候选；两候选均不可写才退回 `$HOME/tmp`
- 本地全量复验：修复后 conan create（同一官方 tarball，predl 字节等价）
  `checking for C compiler default output file name... a.out` /
  `C compiler works... yes` / `Package created` / test_package 1/1 Passed（rc=0），
  日志 `/storage/Users/currentUser/tmp/r02-fixed-conan.log`
- 回退探测单测：HOME=/tmp（erofs 只读）→ `$HOME/tmp` 探测失败 → 正确回退
  `build_folder/.tmp`（rc=0）

### 受影响门禁

- 本地 W3/conan create：复验通过（上述日志）
- 远端 CI：需推送后 `/rebuild` 复验；若 CI worker 的 `build_folder` 亦不可写
  （不可能，conan 已在该目录落盘源码与补丁），才会残留阻塞
