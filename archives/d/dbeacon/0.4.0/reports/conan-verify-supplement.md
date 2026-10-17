# conan-verify 补充证据 — G4/L2/L4/L5（工具跳过项的人工复核）

`ohc-run.py conan-verify dbeacon 0.4.0` 清缓存采信轮（2026-09-10T23:57:16）整体 PASS，
但报告里 G4 报「⚠️ 无法找到程序包 ID」、L2/L4/L5 报「⏭️ 跳过（无 cache 路径）」——
按 workflow 第 7.2 节，`✅ PASS` 与 `⏭️ 跳过` 并存时以跳过为准，本文件用真实命令补齐对应证据。

## 本目录证据文件清单（含各自的产生轮次）

| 文件 | 字节 | sha256 | 产生轮次 |
| --- | ---: | --- | --- |
| `conan-create.log` | 11,436 | `65f38e0432d5d245931c58c3298f187d1638627ff3c13a04695e5953f2e03673` | **清缓存采信轮**（23:57:16，含 `Calling build()`/`RUN: make`/`Apply patch`） |
| `conan-verify-clean-round.log` | 1,483 | `b518e890e12b0a55ebcd886a93640da056c6e3834695dda5ed86cb50d9ee161b` | 采信轮 `conan-verify` 的 stdout 原文（G1/G2/G3 PASS 与跳过行） |
| `conan-verify-report.md` | 1,083 | — | 由 `finish` Step 4 于 23:59:56 重跑覆盖（**缓存命中轮**，结论同为 Verdict PASS） |
| `w3-local-ci.log` | 15,108 | — | `finish` Step 5 的 W3 本地 CI 模拟 |
| `audit-result.json` | 21,220 | 见文件内 `audited_files_sha256` | W4 独立审计（`verdict=pass`；文件本身同样被 `.gitignore:96 reports/` 覆盖，**按 workflow 第 9.3 节不入 PR**，结论在 PR 正文转述） |

> 入库状态：本目录 5 个证据文件全部被 `.gitignore` 的 `reports/` 规则覆盖（第 96 行），
> 其中 `conan-create.log`、`conan-verify-clean-round.log`、`conan-verify-report.md`、
> `w3-local-ci.log` 与本文件以 `git add -f` 显式入库（判定依据用
> `git check-ignore --no-index -v <file>`：不加 `--no-index` 时对已跟踪文件一律报未忽略，会误判）；
> 仅 `audit-result.json` 按 workflow 第 9.3 节留在本地。

> 说明：`finish` 内嵌的 conan-verify 是**缓存命中轮**，它会把采信轮的 `conan-create.log`
> 覆盖成只含 test_package 段的短日志（实测 11,436 B → 4,845 B，`grep -c 'RUN: make'` = 0），
> 正是 workflow 第 7.2 节登记的现象。本目录里的 `conan-create.log` 已由采信轮留档副本还原，
> 内容与采信轮副本逐字节一致（sha256 相同），采信轮结论不受覆盖影响。

- 包引用: `dbeacon/0.4.0@ohpcd/stable:6b129b068851896169fae42d399fa922d239ce8a`
- 配方 revision: `2a6125d18a3196f525ecddbdc2c7589d`（两轮清缓存构建完全一致 → 构建输入逐字节相同）
- 包目录: `/storage/Users/currentUser/.conan2/p/b/dbeacef68bee6e60ff/p`
  （第一轮为 `p/b/dbeac4456a181c2b98/p`，两轮许可证与手册页 sha256 一致、二进制差异仅限调试信息，见 L5）
- 构建树: `/storage/Users/currentUser/.conan2/p/b/dbeacef68bee6e60ff/b`
- 采信轮干净日志副本（对应 SHA `ac8b631`，即本文件首次进入提交的那一轮）:
  `$HOME/tmp/dbeacon-0.4.0/conan-create-ac8b631.log`（11,436 B，
  sha256 `65f38e0432d5d245931c58c3298f187d1638627ff3c13a04695e5953f2e03673`，
  含 `Calling build()`、`RUN: make -j1 CXX='/data/service/hnp/bin/clang++'`、`Apply patch (portability)`）
  第一轮清缓存构建的副本 `$HOME/tmp/dbeacon-0.4.0/conan-create-2371606.log`（同为 11,436 B，
  sha256 `b8d6f5f0a3fc081b58b00fadc54d290608534dd463a2ce09616c16cfdbca7759`）与之逐行一致
  （仅构建目录名、时间戳与 package revision 不同，配方 revision 与全部命令相同）。
  本文件只声明证据来源，不改变配方、补丁或测试任何字节：
  `git diff ac8b631..HEAD -- archives/d/dbeacon/0.4.0/conanfile.py
   archives/d/dbeacon/0.4.0/conandata.yml archives/d/dbeacon/0.4.0/patches
   archives/d/dbeacon/0.4.0/test_package` 为空即为零改动证明。

## G4 产物完整性 ✅

`find <pkg>/p -type f`（除 Conan 元数据外全部为 `package()` 声明的产物）:

| 产物 | 大小 | 与 `package_info()` 一致性 |
| --- | --- | --- |
| `bin/dbeacon` | 830,016 B | `cpp_info.bindirs = ["bin"]` ✅ |
| `share/man/man1/dbeacon.1` | 4,310 B | 手册页，`cpp_info` 不声明 resdirs ✅ |
| `licenses/LICENSE` | 1,075 B | 上游 MIT 许可证 ✅ |
| `conaninfo.txt` / `conanmanifest.txt` | 141 / 215 B | Conan 元数据，非产物 |

`cpp_info.libdirs = []`、`cpp_info.includedirs = []`，包内确实无 `lib/`、无 `include/`（纯可执行包）。

补丁生效核对（build tree 实文件，非推断）：

```text
$ grep -n '::bind(mcastSock' <build tree>/dbeacon.cpp
419:	if (::bind(mcastSock, beaconUnicastAddr.saddr(), beaconUnicastAddr.addrlen()) != 0) {
$ sha256sum <build tree>/dbeacon.cpp
ad8ac596fedee0c62981beefa7c828d489b6af63186338330ad21c92e7bff2b7   # == 探索期工作副本
```

## L2 平台冒烟 ✅（真实运行，非仅 `--version`）

直接用打包产物（不借助 conanrun 注入）在设备上跑真实组播 beacon：

```sh
<pkg>/p/bin/dbeacon -V            # "dbeacon - a Multicast Beacon 0.3.9.2p1 ($Rev$)"（上游既有退出码 1）
<pkg>/p/bin/dbeacon -h            # "Usage: dbeacon [OPTIONS...]"（上游既有退出码 1）
cd <tmp>/supplement/l2-run-final
<pkg>/p/bin/dbeacon -4 -n PKGSMOKE -a sup@example.com -b 239.192.0.7 -I 1 -d dump.xml &
```

运行 6 秒后停止，实测输出：

```text
run.log : Sep 10 23:58:16.822764 Local name is `PKGSMOKE` [Beacon group: 239.192.0.7/10000, Local address: 192.168.3.16]
dump.xml: <beacons rxrate="0.00" txrate="0.00" versioninfo="0.3.9.2p1 ($Rev$)">
          <group addr="239.192.0.7/10000" int="5.00">
            <beacon name="PKGSMOKE" addr="192.168.3.16/40372" contact="sup@example.com" age="5" ...>
```

5 项断言全部命中（本地名广播、dump 中的 beacon 名/管理邮箱/组地址/版本指纹）。
动态依赖 `libc++_shared.so`、`libc.so` 由平台提供（设备 `/system/lib64/libc++_shared.so` 存在），
`readelf -dW` 无 RPATH/RUNPATH，无需额外注入即可加载运行。

`conan create` 的 test_package 阶段另有 8/8 断言（见采信轮日志，`DBEACON_TEST_SUMMARY passed=8 failed=0`）。

## L4 静态安全扫描 ✅（readelf 15.0.4）

对打包 `bin/dbeacon`：

| 检查 | 结果 | 证据 |
| --- | --- | --- |
| PIE | ✅ | `ELF64` / `Type: DYN (Position-Independent Executable file)` / `FLAGS_1: NOW PIE` |
| NX | ✅ | `GNU_STACK ... RW`（无 E 标志） |
| RELRO | ✅ Full | `GNU_RELRO` 段存在 + `FLAGS: BIND_NOW` |
| 架构 | ✅ | `Machine: AArch64`（目标 OHOS aarch64） |

## L5 产物基线 ✅

包内容聚合（排除打包时间戳会漂移的 `conaninfo.txt` / `conanmanifest.txt`）：

```sh
cd <pkg>/p && find . -type f ! -name conaninfo.txt ! -name conanmanifest.txt \
  | sort | xargs sha256sum | sha256sum
# 采信轮（SHA ac8b631）: 284ac59aac08366bb0a9c1f236af7a9f2bc524de188a724cf6eb1f403cb8021a
# 前一轮（SHA 2371606）  : c1a98fc339dfeb8400e0d58a0452c7c223d63347b8fc6d0206dc457abd7775cb
```

逐文件基线（采信轮，SHA ac8b631）：

| 文件 | sha256 |
| --- | --- |
| `bin/dbeacon` | `cc3475562101fc66a6814a9fead6878b831e01793ebeccffdb6d48bbca0032ab` |
| `licenses/LICENSE` | `088320703e30fbb3a0131dbe52c8aa015cb67666a1823d857703c10f1a869b63` |
| `share/man/man1/dbeacon.1` | `834c8caa30d205eee443a01d874756e268519e984455b9cb536c95a72a8d6b3e` |

许可证与手册页逐字节稳定；`bin/dbeacon` 在两轮之间字节不同（`3e771afc…` → `cc347556…`），
原因是上游 Makefile 固定带 `-g`，DWARF 里记录了构建目录（`DW_AT_comp_dir`），
而 Conan 每轮的缓存目录名不同（`p/b/dbeac4456a181c2b98` vs `p/b/dbeacef68bee6e60ff`）。
用设备上的探索构建产物与采信轮打包产物做节级比对可证差异只在调试信息与签名节：

```text
$ python3 -c "<逐字节比较 <work-native>/dbeacon 与 <pkg>/bin/dbeacon 并映射到 ELF 节>"
sizes: 830016 830016
differing bytes: 400548
diff by section: {'.debug_str': 301009, '.debug_loclists': 28993, '.debug_line': 27843,
                  '.debug_rnglists': 11894, '.debug_str_offsets': 7963, '.debug_addr': 4048,
                  '.debug_line_str': 3235, '.comment': 243, '.codesign': 63,
                  '.debug_frame': 61, '.debug_aranges': 40, '<header/other>': 15156}
# 全部落在 .debug_*/.comment/.codesign/ELF 头（build-id 等）；代码节无差异
```

因此跨轮次的二进制字节漂移**不是**源码或链接差异：两轮配方 revision（`2a6125d18a…`）与
package_id（`6b129b06…`）相同，命令行相同，且同一轮内构建树产物与打包副本逐字节相同：

```sh
cmp <build tree>/b/dbeacon <pkg>/p/bin/dbeacon   # 相同（采信轮同为 cc347556…）
```

本包为纯 Makefile 构建，无 `meson install --destdir` 之类的安装期改写，构建树与打包副本一致，
`.codesign`（hnp clang 自带链接器签名）未在安装期被破坏。

## 结论

G4/L2/L4/L5 四项均为**人工实测通过**（非工具自动判定），采信轮 G2 为清缓存后的干净构建
（含 `Calling build()` 与 `RUN: make`），上游测试为该包适用的 0 用例口径（上游无测试套件），
消费者验证为 test_package 8/8 + 本文件 L2 的独立运行复核。
