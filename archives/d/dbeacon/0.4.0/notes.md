# dbeacon 0.4.0 适配笔记

## 编译环境

- 构建系统: makefile（上游为单文件级纯 Makefile，无 configure）
- 编译日期: 2026-09-10
- 编译器: clang 15.0.4（OHOS SDK 26.0.0.18，aarch64-unknown-linux-ohos）
- 目标 profile: `ci/conan/profiles/ohos-aarch64`（os=OHOS 6.0 / arch=armv8 / clang 15 / libc++ / cppstd 17 / Release）
- 状态: built

## 源码与版本口径

- 官方源: `uoaerg/dbeacon` tag `dbeacon-0.4.0`（commit `d366348e7aaaa16ccbcc39d420fb66c40db01965`），
  SHA-256 `70e880832538163a1df12c606e74f4e3bbb5286a17bf4cfebecba95ded74d07b`（43,066 字节，2026-09-10 实测）。
- 该仓库是 Debian `d/watch` 跟踪的上游；原项目站点 `fivebits.net/proj/dbeacon/` 已下线（curl 空响应），
  `hugosantos/dbeacon` 仓库已归档（最后提交 2014-12）且只有 `dbeacon-0.3.9` tag，没有 0.4.0 tag。
- 交叉核对：官方 tag 归档解出的 23 个文件与 Debian `dbeacon_0.4.0.orig.tar.bz2` 内容逐文件 sha256 完全一致
  （Debian orig 是该 tag 归档去掉顶层目录名后的重打包），故 0.4.0 的官方内容以本 tag 为准。
- 上游自报版本串仍是 `0.3.9.2p1`（`dbeacon.cpp` 中 `versionInfo` 未随 0.4.0 发布更新），
  0.4.0 由上游 `Changelog` 首条与官方 tag 界定；消费者测试断言的是制品自报的 `0.3.9.2p1` 指纹。

## 编译步骤

1. 原生探索（设备上直接用 SDK clang 构建 ×86 前的验证）：

   ```bash
   make CXX=clang++ -j1        # 首次失败于 dbeacon.cpp:419（见「问题 1」）
   ```

2. 应用补丁后原生构建通过，产出 `dbeacon`（830,016 字节），`./dbeacon -V` 正常打印版本横幅。

3. Conan 配方 `build()`：`apply_conandata_patches(self)` → `make -j1 CXX='<profile clang++>'`，
   工作目录固定为 `self.source_folder`（上游 Makefile 不支持 out-of-tree 构建）。
   编译器按 R33 从 `tools.build:compiler_executables` 取值（profile 给出 `/data/service/hnp/bin/clang++`），
   不使用 shell `$CXX/$CXXFLAGS`。

4. `package()` 直接拷贝 `dbeacon` → `bin/`、`docs/dbeacon.1` → `share/man/man1/`、`LICENSE` → `licenses/`；
   不调用上游 `install` 目标（该目标依赖 `install -D`，且会写入系统 PREFIX）。

5. `conan create` 干净构建 + test_package（见「验证结果」）。

## 上游测试清点

上游没有测试套件，清点命令与原始输出：

```text
$ find . -type f | wc -l
23
$ find . -iname '*test*' -o -iname 'check*'
./contrib/checkmatrix.sh          # cron 邮件通知部署脚本（调用 xml2txt.pl 比对矩阵），非测试
$ grep -nE '^[A-Za-z_.-]+:' Makefile
all: / dbeacon: / dbeacon.o: / dbeacon.h: / msocket.h: / protocol.h: /
dbeacon_posix.o: / protocol.o: / ssmping.o: / install: / install_mans: / clean:
$ make -n check
make: *** No rule to make target 'check'.  Stop.
```

| 口径 | 数值 |
|------|------|
| 上游测试程序/套件数 | 0 |
| 上游用例数（TOTAL） | 0 |
| 上游 PASS / FAIL / SKIP / NOT_RUN | 0 / 0 / 0 / 0 |

上游无测试用例既不是 PASS 也不是 skip，按 0 个用例申报；消费者验证由 `test_package/` 承担。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `dbeacon.cpp:419` 编译失败：`error: invalid operands to binary expression ('__bind<int &, sockaddr *, int>' and 'int')` | `dbeacon.cpp` 第 42 行 `using namespace std;`，而第 419 行未限定地调用 POSIX `bind(2)`；libc++ 经 `<map>/<string>/<iostream>` 传递引入 `<functional>`，`std::bind` 作为完美转发模板以精确匹配抢占 C 函数符号 | 补丁 `0001-qualify-bind-call-with-global-scope.patch` 将该调用限定为 `::bind(...)`（对 glibc/libstdc++ 与其它 POSIX 平台完全等价） |
| 2 | 编译出现警告 `redirecting incorrect #include <sys/signal.h> to <signal.h>`（`-W#warnings`） | OHOS sysroot 对 glibc 专有的 `<sys/signal.h>` 提供重定向 shim | 无需处理；仅为警告，`dbeacon_posix.cpp`/`dbeacon.cpp` 的后续编译与运行正常 |
| 3 | 其余 6 条警告为上游既有告警（`%llu` 格式串打印 `unsigned long` 5 条、`lc` 变量未使用 1 条） | 上游 2005 年代码在 64 位平台上的既有瑕疵 | 不改上游代码；不引入与适配无关的改动 |

编译共 7 条警告（clang 汇总行 `7 warnings generated.`）：1 条 OHOS sysroot 重定向（问题 2）
+ 6 条上游既有告警。复算命令：

```sh
grep -o "warning: [a-z-]*" <采信轮 conan-create 日志> | sort | uniq -c
#       5 warning: format
#       1 warning: redirecting
#       1 warning: variable
```

## W4 独立审计意见处置

独立审计（`reports/audit-result.json`，`verdict=pass`，P0=0 / P1=0）提出的非阻断项处置如下；
审计结论对应的 SHA 为 `4aab44c1c693e076fe3cc8df3a1069a9e2f3119c`，
其后只改动本笔记与补充证据文件的文字，**配方、补丁、测试文件与 conandata 逐字节未变**
（`git diff 4aab44c1..<最终 SHA> -- conanfile.py conandata.yml patches/ test_package/` 为空），
故采信轮验证与审计结论继续有效。

| 级别 | 审计意见 | 处置 |
|------|----------|------|
| P2 | 被本文档引用的 3 个证据文件被 `.gitignore` 的 `reports/` 规则排除、未进 PR | **已修**：`conan-create.log`、`conan-verify-report.md`、`conan-verify-clean-round.log`、`w3-local-ci.log` 以 `git add -f` 入库；`audit-result.json` 按 workflow 第 9.3 节仍不入库，结论在 PR 正文转述 |
| P3 | 补充证据引用的报告时间戳与磁盘文件不一致 | **已修**：`conan-verify-report.md` 由 `finish` Step 4 于 23:59:56 重写（缓存命中轮），补充证据已改为按文件分别标明产生轮次；采信轮（23:57:16）的 stdout 另存为 `reports/conan-verify-clean-round.log` |
| P3 | 本笔记「其余 7 条警告」计数有误 | **已修**：改为 6 条并给出 `grep -o "warning: [a-z-]*" \| sort \| uniq -c` 的复算输出（见上文） |
| P3 | `test_package/test.sh` 用 `set -uo pipefail`（无 `-e`） | **有意为之，不修**：`dbeacon -V`/`-h` 上游本身返回 1，`set -e` 会让正常探测中断；脚本用显式 `fail` 计数与末尾非零退出码兜底判定，并已在脚本头部注释说明 |
| P3 | `build()` 的最末回退为裸命令名 `"clang++"` | **不修**：profile `ci/conan/profiles/ohos-aarch64` 的 `tools.build:compiler_executables` 恒提供 `cpp`，回退分支只在完全没有 conf 时生效，且与仓库既有 raw-makefile 包（darkhttpd、clac）写法一致；改动配方会变更 recipe revision 并使采信轮验证失效，收益不抵成本 |

## 源码修改

仅 1 个补丁（`patches/0001-qualify-bind-call-with-global-scope.patch`，`strip: 1`）：

```diff
@@ -416,7 +416,7 @@
-	if (bind(mcastSock, beaconUnicastAddr.saddr(), beaconUnicastAddr.addrlen()) != 0) {
+	if (::bind(mcastSock, beaconUnicastAddr.saddr(), beaconUnicastAddr.addrlen()) != 0) {
```

- 单行、非平台条件编译（无 `#ifdef __OHOS__`），不改变任何平台的行为。
- 本地按 Conan 实际执行路径用 patch_ng 库调用验证：`patch_ng.fromfile(...).apply(strip=1, root=<pristine tree>)`
  返回 True，且修补后 `dbeacon.cpp` 的 sha256 与探索树工作副本一致。
- 补丁与 `conandata.yml` 的 `patch_file` 一一对应（`patches/` 目录仅此一个文件）。

## 依赖版本

无第三方依赖。dbeacon 仅链接平台 C/C++ 运行时（libc++/libm 由 libc++ 传递引入），
`libraries()` 为空，`cpp_info` 不声明 libs/includedirs。

## 验证结果

```text
$ conan create archives/d/dbeacon/0.4.0 -pr:h=<ohos-aarch64> -pr:b=<ohos-aarch64> \
      --build=missing --user=ohpcd --channel=stable
...
dbeacon.cpp:419 修复后 clang++ -g -Wall -O2 -c/-o 四个 TU 全部编译并链接成功
RUN: make -j1 CXX='/data/service/hnp/bin/clang++'
Apply patch (portability): Qualify the POSIX bind() call ...
...
========= Testing the package =========
[test] dbeacon -V
PASS: version banner identifies the beacon
PASS: artifact self-reported version string
[test] dbeacon -h
PASS: usage line
PASS: multicast group option is documented
[test] dbeacon IPv4 multicast run -> dump.xml
PASS: dump.xml carries the self-reported version fingerprint
PASS: dump.xml announces the local beacon name
PASS: dump.xml carries the administration contact
PASS: dump.xml reports the joined multicast group
DBEACON_TEST_SUMMARY passed=8 failed=0
RESULT: PASS (8 assertions)
```

- 上游测试：0 个用例（上游无测试套件，清点见上）。
- 新增消费者测试：8/8 通过（`test_package/test.sh`，统计单位为断言；取数命令：
  `grep -c '^PASS:' <test_package 日志>`，并核对脚本自打印的 `DBEACON_TEST_SUMMARY passed=8 failed=0`）。
- 运行验证：设备真实 IPv4 组播运行（`-b 239.192.0.1 -I 1 -d dump.xml`）产出 dump.xml，
  内容含 `versioninfo="0.3.9.2p1 (`、`<beacon name="OHOSTEST"`、`contact="ohos@example.com"`、
  `<group addr="239.192.0.1/10000"`；日志行 `Local name is \`OHOSTEST\` [Beacon group: 239.192.0.1/10000, ...]`。

复现命令（证据指针；详细基线与独立复跑证据见 `reports/conan-verify-supplement.md`，
采信轮 `conan-create.log` 的留档副本路径与 sha256 也记录在该文件中）：

```text
RUN: make -j1 CXX='/data/service/hnp/bin/clang++'
Apply patch (portability)
[test] dbeacon -V
DBEACON_TEST_SUMMARY passed=8 failed=0
```

### W3 本地 CI 模拟（`finish` Step 5，日志 `reports/w3-local-ci.log`）

| 门禁 | 结果 | 证据行 |
|------|------|--------|
| L0 结构/测试文件/配方检查 | PASS | `L0_RESULT=pass: all checks passed` |
| L1a/L1b test_package 真实执行 | PASS | `L1a: test_package was executed by conan create` |
| L1c 上游 `make check`/`ctest` | 不适用 | `L1c: No upstream make check/ctest in log`（上游无测试套件，0 用例口径） |
| L1e 破坏性反向验证（R34） | PASS | `L1e: Negative test confirmed — test genuinely depends on dbeacon`（移走 `bin/` 后测试如预期失败） |
| L4 补丁危险函数扫描 | PASS | `L4_RESULT=pass: patches clean` |
| L5 产物基线 | PASS | `L5_RESULT=pass: bin/ has content` |
| L2 冒烟探针（非阻塞） | warn | `[warn] L2: dbeacon --version/--help failed (non-blocking)`，构建总判定 `Pass rate: 100.0% (1/1)` |

L2 的 warn 是探针口径问题而非功能问题：`ci/conan/build_and_test.sh` 的 L2 只尝试 GNU 风格
`--version` / `--help` 并要求退出码 0，而 dbeacon 的长选项是单横线形态（`-version`、`-help`，
见 `dbeacon.cpp` 的 getopt 表），且上游对 `-V`/`-h` 打印后本身就返回 1。
真实功能验证由 `test_package`（8/8）与补充证据中的独立 L2 运行提供。

## 交付物

| 文件 | 说明 |
|------|------|
| `bin/dbeacon` | 组播 beacon 命令行程序（OHOS aarch64 动态可执行文件） |
| `share/man/man1/dbeacon.1` | 上游手册页 |
| `licenses/LICENSE` | 上游 MIT 许可证 |

## 注意事项

- dbeacon 是长驻服务型程序：`-V`/`-h` 打印后上游自身以退出码 1 结束，`无参数` 以 255 结束（上游既有行为），
  消费者测试只以输出内容判定，不用退出码判定。
- 需要 IPv4/IPv6 组播能力的运行环境；设备上默认接口可加入组播组，故测试为真实运行而非桩测试。
- 上游 `contrib/matrix.pl`、`contrib/checkmatrix.sh` 是 Apache CGI/定时脚本，依赖 Perl CGI 模块，
  不属于本包交付物（`package()` 只安装二进制、手册页与许可证）。
