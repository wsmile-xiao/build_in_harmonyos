# open-simh 3.12-3 适配笔记

## 编译环境
- 构建系统: makefile（纯 GNU make，无 configure）
- 编译日期: 2026-09-11
- 编译器: /data/service/hnp/bin/clang（aarch64-unknown-linux-ohos 目标）
- 状态: published（conan-verify G0-G4+L2/L4/L5 全过）

## 软件背景
- 上游：open-simh/simh tag v3.12-3（SIMH 历史计算机模拟器套件，open-simh 是
  simh/simh 的官方开源延续组织；v3.12-3 只存在于 open-simh/simh，simh/simh
  仓库最新 tag 是 v3.12-2）
- 语言：纯 C（246 个 .c，lang-preflight 判定 c）
- 依赖：零外部依赖（自包含；pthread 走 OHOS musl sysroot 自带的 libc）
- 产物：24 个模拟器可执行文件（application 类型）

## 编译步骤

```bash
# 交叉编译（CC 通过 make 变量 GCC= 注入；NONETWORK=1 关闭 libpcap 依赖；
# TESTS=0 跳过测试钩子；CFLAGS_G=-fcommon 处理老 C 代码）
make -j1 GCC=clang NONETWORK=1 TESTS=0 CFLAGS_G=-fcommon all
# 产物在 BIN/ 下：pdp1 pdp4 pdp7 pdp8 pdp9 pdp15 pdp11 pdp10 vax vax780
#   nova eclipse i1401 i1620 altair gri i7094 id16 uc15 id32 sds lgp h316 sigma
```

构建策略说明（大件裁剪）：SIMH makefile 的默认 all 目标即 24 个模拟器，
单目标编译约 15s（-j4 全量 11s），无需进一步裁剪。makefile 平台探测基于
`uname`（本机 HarmonyOS 报 "HarmonyOS"），走 Linux 分支的 GNU 扩展路径；
无 pcap/SDL2/editline 头文件时自动降级（网络→stub、视频→SIM_MAJOR==3
本就禁用），NONETWORK=1 显式跳过 libpcap 探测避免误链主机库。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | uc15 目标链接失败：`ld.lld: error: duplicate symbol: uc15_memsize`（12 处重复） | PDP11/pDP11 源码老 C 风格 tentative definition：pdp11_defs.h 在 `#if defined(UC15)` 块里写了 `uint32 uc15_memsize;`（无 extern），每个包含该头的 .c 都产生一个公共符号；gcc 默认合并 common 符号而 clang≥15 默认 `-fno-common`，lld 严格报重复 | make 变量 `CFLAGS_G=-fcommon` 恢复 C99 前的公共符号合并语义（makefile 的 CC 行展开为 `${GCC} ${CC_STD} -U__STRICT_ANSI__ ${CFLAGS_G} ...`，CFLAGS_G 恰好是通用 flags 插槽）。24/24 目标全绿 |
| 2 | makefile 无 install 目标 | 上游约定用户直接在源码树 BIN/ 下运行 | package() 中将 24 个二进制手工 shutil.copy2 到 package_folder/bin/ |
| 3 | tag 地址 404 | 任务给的 simh/simh 仓库无 v3.12-3（只有 v3.12-2） | 实际上游是 open-simh/simh（开源延续组织），v3.12-3 tag 存在；conandata.yml URL 用 open-simh 官方源 |

## 源码修改

无补丁（patches_applied: []）。全部兼容性处理通过 make 变量注入完成：
- `CFLAGS_G=-fcommon`：恢复 tentative definition 合并（见问题 1）
- `NONETWORK=1`：跳过 libpcap 网络支持（OHOS 无 pcap，SIMH 优雅降级）
- `TESTS=0`：v3.12-3 源码树无 tests/*.ini，测试钩子无事可做

## 依赖版本

- 零三方依赖（conan requires 为空）
- OHOS SDK sysroot（musl）：libc/libm/libpthread/librt 由平台提供

## 验证结果

```bash
$ conan create archives/o/open-simh/3.12-3 -pr:h=ci/conan/profiles/ohos-aarch64 ...
# Package '6b129b068851896169fae42d399fa922d239ce8a' created
# package(): Packaged 24 files

$ test_package/test_simh.py <pkg>/bin
SIMH smoke test: 25/25 assertions passed
All simulator banners and pdp11 register deposit/step verified.
```

测试口径（rule4）：
- 上游构建系统注册测试目标数 N=0 —— SIMH v3.12-3 的 makefile 虽定义了
  RegisterSanityCheck 钩子（find_test = tests/<sim>_test.ini），但 v3.12-3
  源码树不含任何 *.ini（regress 测试体系是 simh v4 引入的）
- 适配后自建测试：25 项断言（24 个模拟器 banner 冒烟 + pdp11 指令级
  功能验证：deposit MOV #0173,R0 → step → examine r0 == 000173），25/25 通过

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方（application，纯 make 构建） |
| conandata.yml | 源码 URL + sha256 |
| test_package/ | L1 测试（test_simh.py，25 断言） |
| reports/conan-verify-report.md | 8 道门禁验证报告（PASS） |

## 注意事项
- ci/config/build_timeouts.txt 未改动（全量构建 <5 分钟，远低于 3600s 默认预算）
- 产物为未 strip 的 ELF（OHOS MAC 拒绝对已装二进制 strip，参照 abduco 先例）
- 若未来需要网络支持（pdp11 XU/XQ 以太网），需先适配 libpcap 到制品仓
---

**编译结束**: 2026-09-11 10:33
**最终状态**: built

## 提交流程记录（W4 审计修正）
- 2026-09-11：W4 审计 P2-001（import 顺序）已修复并 amend；P0/P1 清零，审计 verdict=pass

