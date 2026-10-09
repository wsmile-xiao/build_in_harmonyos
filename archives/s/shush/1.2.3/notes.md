# shush 1.2.3 适配笔记

## 编译环境

- 构建系统: autotools（Autoconf 2.59 生成的 configure + 手写 Makefile.in，非 automake）
- 编译日期: 2026-09-29
- 编译器: OHOS SDK clang 15（`/data/service/hnp/bin/clang`），目标 aarch64-linux-ohos
- 构建机: x86_64 runner（交叉编译；`qemu-aarch64` 7.2 用户态，未注册 binfmt）
- Conan: 2.29.1（OHOS 适配版），profile `ci/conan/profiles/ohos-aarch64`（-pr:h 与 -pr:b 相同）
- 状态: published（`conan-verify` 判定 PASS：G0-G3 通过，G4 仅告警未定位包 ID，L2/L4/L5 因无 cache 路径跳过；W3 本地 CI 通过）

## 源码

- 官方发布包: `https://web.taranis.org/shush/dist/shush-1.2.3.tgz`
  sha256 `44ff5d74f38772bdd51ce5b9f2f75b260f030d54fd0358e95f35b94c0bc78972`
- 任务给出的 `deb.debian.org/.../shush_1.2.3.orig.tar.gz` 与官方包**逐字节相同**（sha256 一致）；
  配方使用官方 URL（R39 / PF7：不引用 Debian 重打包源）。
- 注意：上游 `src/version.h` 写的是 `1.0`，所以 `shush -V` 打印 `version 1.0`，与发布包版本 1.2.3 不一致，属上游现状。

## 编译步骤

配方 `build()` 实际执行（in-source 构建，上游 Makefile 不支持 VPATH）：

```bash
# 12 个补丁由 apply_conandata_patches 应用
./configure --prefix=/ --with-pcre=<pcre2/10.45 包目录> \
    ac_cv_path_SENDMAIL=NOSENDMAIL ac_cv_path_CRONTAB=NOCRONTAB \
    --host=aarch64-linux-ohos --enable-relaxed-ownership      # 后两项仅 os=OHOS
grep '#define HAVE_PCRE_H 1' src/config.h                     # 配方内校验，缺失即失败
make -j1                                                      # 顶层 make 进 src/ 编译 shush
# package(): 复制 src/shush -> bin/、shush.1 -> share/man/man1/、LICENSE -> licenses/
```

上游 `make install` 不支持 DESTDIR（会写构建机的 `${prefix}`），所以不调用，改为 `copy()`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `config.sub aarch64-linux-ohos` → `machine 'aarch64-linux' not recognized`；真机上 config.guess 猜不出构建机 | 随包 config.guess(2004-06-11)/config.sub(2004-03-12) 不认 aarch64 与 HarmonyOS（`uname -s` = HarmonyOS） | 补丁 0001/0002（与已合并 jday 2.4 同款，E007/E543） |
| 2 | x86 runner 上裸 configure：`cannot run C compiled programs` | profile 两侧同为 OHOS，conan 不注入三元组，configure 以为是原生编译去运行 aarch64 conftest | OHOS 下配方传 `--host=aarch64-linux-ohos`（不传 --build）：x86 走交叉，aarch64 CI worker 上 `cross_compiling=maybe` 仍可原生探测；configure 只有 AC_HEADER_STDC 一处运行期探测 |
| 3 | PCRE 1 已停止维护，制品仓只有 pcre2 | 上游只支持 `pcre.h`/`pcre_compile` | C 源码移植取自 Debian `03_port_to_pcre2.diff`（Yavor Doganov，Bug #999964）；`configure.ac` 改为 `AC_SEARCH_LIBS([pcre2_compile_8],[pcre2-8])` + `AC_CHECK_HEADERS([pcre2.h])`（带 `PCRE2_CODE_UNIT_WIDTH 8`），再用**原版 Autoconf 2.59** 重生成 `configure`/`config.h.in` |
| 4 | Debian 移植在匹配成功路径漏 `pcre2_match_data_free`；未参与匹配的捕获组会 `continue` 死循环 | Debian 补丁缺陷（`i` 未自增） | 补丁 0006 在 break 前释放；未设置组（`PCRE2_UNSET`）跳过并自增 |
| 5 | `signals.h` 为空表，`timeout=...,SIGTERM` 报 `Invalid "timeout" signal`，作业不会被终止 | `src/Makefile.in` 用 `cat /usr/include/signal.h ... 2>/dev/null \| awk` 读**构建机**头：真机无 /usr/include，x86 Debian 的 bits/signum.h 在 multiarch 目录，都得到空表且不报错 | 补丁 0005：`echo '#include <signal.h>' \| $(CC) $(CPPFLAGS) -E -dM -x c - \| awk -f signals.awk`，并对空表报错（知识草稿 E544-draft-31E6） |
| 6 | 交叉构建把构建机的 `/usr/lib/sendmail`、`/usr/bin/crontab` 烙进二进制 | `AC_PATH_PROG` 在构建机上探测；鸿蒙 PC 上两者都不存在 | 配方传 `ac_cv_path_SENDMAIL=NOSENDMAIL ac_cv_path_CRONTAB=NOCRONTAB`，钉成 configure 在目标机上会得到的值；传输程序运行期由配置项 `sendmail=` 或环境变量 `SHUSH_SENDMAIL` 指定 |
| 7 | 在 HMDFS 上 shush 拒绝一切作业：`someone else owns ...` / `must not be group or world writable!` | `cf.c`/`crontab.c` 要求配置文件属主 == euid 且非组可写；HMDFS 把属主投影为共享身份（20001006）并强制组写位（E011、E453，草稿 e665） | 补丁 0004/0007/0010：新增 `--enable-relaxed-ownership`（默认关闭，配方仅在 OHOS 打开），此时只拒绝**全局可写**文件；安全基线保留，C7 覆盖 |
| 8 | `check.c`: `call to undeclared function 'localtime'`（clang 15 下为错误） | 缺 `<time.h>` | 补丁 0008（同 Debian `02_fix_implicit_declaration_strftime.diff`） |
| 9 | `units.h`: `unknown type name 'u_int'` | musl 仅经 `<sys/types.h>` 提供 `u_int`，`state.c` 包含 units.h 前未包含它 | 补丁 0012 在 units.h 中包含 `<sys/types.h>` |
| 10 | `shush.c`: Debian 移植在 `case` 标签后直接声明 `char ver[24]` 编译失败 | C 标签后不能跟声明 | 补丁 0011 包进块作用域 |
| 11 | config.status 在 HMDFS 上 `umask 077 && mktemp -d` 建的临时目录对自身不可写 | HMDFS UID 投影（E011） | 补丁 0003 同 jday 2.4：`umask 000 && mkdir` |
| 12 | `init-build` 自带下载器对官方站挂起 | urllib 链路问题（curl 与 Conan 的 requests 下载均 0.6 s 完成） | 先用 curl 取包、`EXPECTED_SHA256` 校验后预置；Conan `get()` 不受影响 |

## 源码修改（12 个补丁，均由 `refresh-patch --auto` 生成）

| 补丁 | 内容 |
|---|---|
| 0001-config.guess.patch | 新增 `aarch64:Linux` 与 `aarch64:HarmonyOS|OHOS` 分支 |
| 0002-config.sub.patch | 接受 `aarch64` CPU 与 `linux-ohos` |
| 0003-configure.patch | Autoconf 2.59 对 0004 的重生成结果 + config.status 临时目录 `umask 000 && mkdir` |
| 0004-configure.ac.patch | PCRE2 探测；`--enable-relaxed-ownership` |
| 0005-src-Makefile.in.patch | signals.h 由目标编译器 `-E -dM` 生成并做空表检查 |
| 0006-src-analyzer.c.patch | PCRE2 API（Debian）+ match data 泄漏与未设置捕获组死循环修复 |
| 0007-src-cf.c.patch | `RELAXED_OWNERSHIP` 下仅拒绝全局可写配置文件 |
| 0008-src-check.c.patch | `#include <time.h>` |
| 0009-src-config.h.in.patch | `HAVE_PCRE2_H`/`HAVE_PCRE_H`/`RELAXED_OWNERSHIP` 模板（autoheader 2.59 输出） |
| 0010-src-crontab.c.patch | `RELAXED_OWNERSHIP` 下仅拒绝全局可写配置目录 |
| 0011-src-shush.c.patch | `-V` 打印 PCRE2 版本（Debian）并修正声明位置 |
| 0012-src-units.h.patch | `#include <sys/types.h>` |

补丁中没有 `__OHOS__`（R8/PF5）。关于 0003 修改生成文件：`autoconf` 不作为构建依赖（制品仓的 autoconf/2.72
依赖 OHOS 版 perl/m4，x86 runner 无法执行），因此把 `configure.ac` 与重生成的 `configure` 同步提交；
可复现性证据：用 autoconf 2.59 从**原始** `configure.ac` 重生成，与随包 `configure` 只差第 2 行来源注释
（`From configure.ac Id: ...`），重生成结果保留了该行原文。

## 依赖版本

- `pcre2/10.45`（制品仓已发布，W0 `conan download --only-recipe` 验证；静态库 `libpcre2-8.a`，
  只链接 `-lpcre2-8`，不链接 `libpcre2-posix`——后者只导出 `pcre2_reg*`，不会劫持 libc 的 `regcomp`）
- 运行期依赖：仅 `libc.so`（`llvm-readelf -d`：NEEDED 只有 libc.so，无 RPATH/RUNPATH）

## 上游测试清点（R51）

- 发布包共 55 个文件：无 `tests/` 目录；`Makefile.in` 与 `src/Makefile.in` 的目标只有
  shush / pure / ifparser_test / depend / clean / distclean / install，**无 check/test 目标**，无 ctest/pytest 注册。
- 唯一的测试形态文件 `src/ifparser_test.c` 是开发桩：`tests[]` 为空数组，只解析一个写死的表达式并打印
  `= <结果> (<返回码>)`，没有任何断言；其 `make ifparser_test` 规则链接不全
  （`undefined symbol: error / myassert / variable_get`）。手工补齐对象文件后在 qemu 下运行输出 `= 0 (0)`。
  不计为测试。
- 结论：上游可运行测试 **0**（已清点，不是 UNKNOWN）。功能验证由 test_package 的消费者用例补齐。

## 验证结果

### conan-verify（x86_64 runner）

判定 PASS：G0/G1/G2/G3 通过；G4 报告「无法找到程序包 ID」（仅告警）；L2/L4/L5 在 conan-verify 内因「无 cache 路径」
跳过。W3 本地 CI（build_and_test.sh）中 L0/L1/L1e/L5 通过、L2 跳过（交付物在 x86 上无法执行，且冒烟只试
`--version/--help`）、L4 告警（config.guess 补丁中上游原有文本被危险函数正则误命中）。`conan create` 完成打包：`bin/shush`（aarch64 PIE，解释器
`/lib/ld-musl-aarch64.so.1`，NEEDED 仅 `libc.so`）、`share/man/man1/shush.1`、`licenses/LICENSE`。
configure 实测：`checking for library containing pcre2_compile_8... -lpcre2-8`、`checking for pcre2.h... yes`、
`checking for sendmail... (cached) NOSENDMAIL`、`checking host system type... aarch64-unknown-linux-ohos`。

### test_package（消费者用例 C1-C8，`test_package/test_shush.c`）

一个消费者程序，由 test_package 用 OHOS 工具链编译；`test()` 以
`test_shush run <pkg>/bin/shush <test_shush> <workdir>` 运行：它写 shush 配置，让打包的 shush 托管自己的
`job` 角色、把报告投递给自己的 `sendmail -t -i` 角色，再检查退出码、投递的邮件、保留的日志和诊断输出。

- C1 `-V` 报告 PCRE2 10.x 运行时
- C2 报告主流程：PCRE2 规则（`(?i)`、`\s`、`\d`）+ POSIX 规则计数驱动 `if=`，一封 HTML 报告，捕获组加粗
- C3〔鸿蒙特有〕`-k` 保留的输出日志落在 `$TMPDIR`（鸿蒙 `/tmp` 只读）
- C4〔鸿蒙特有〕配置无 `sendmail` 时经 `SHUSH_SENDMAIL` 投递（鸿蒙 PC 无 MTA）
- C5〔鸿蒙特有〕无任何传输程序时回落到配方钉死的 `NOSENDMAIL` 并给出诊断
- C6〔鸿蒙特有〕`timeout=2s,SIGTERM` 经目标信号表解析并终止作业（`$exit == -15`）
- C7〔鸿蒙特有〕a 组可写配置被接受；b 全局可写配置仍被拒（先 stat 实际权限位，构造不出时报 NOT RUN）
- C8〔鸿蒙特有〕`-u` 定时任务管理：无 crontab → 退出码 1 + 诊断，不挂起、不报成功

**执行证据**

1. `conan create` 的 test 阶段（x86_64 runner，交付的动态产物）：两个 ELF 的产物检查通过；运行期用例
   输出 `SKIP runtime cases C1-C8: host x86_64 cannot execute ...`——**本地未实跑交付产物，由 CI 执行**，
   skip 不计为通过。
2. 同源 `.o` 静态重链副本（`conan create` 构建目录中与交付物相同的 18 个 `.o` + `libpcre2-8.a`，
   `-static` 重链；构建树 `src/shush` 与包内 `bin/shush` `cmp` 一致）+ 同一 `test_shush.c` 的静态编译，
   `qemu-aarch64` 实跑（宿主 sh 包装脚本把 `shush`/`test_shush` 转交 qemu）：

   ```text
   $ qemu-aarch64 test_shush run wrap/shush wrap/test_shush work
   PASS [C1] ... PASS [C2] ... PASS [C3] ... PASS [C4] ... PASS [C5] ...
   PASS [C6] ... after 4.1s ... PASS [C7a] ... PASS [C7b] ... PASS [C8] ...
   shush consumer test: passed=9 failed=0 notrun=0
   EXIT=0
   ```

   这**不等于交付产物已实跑**：静态副本与交付物同源同编译参数，但链接方式不同（静态 musl）。
3. 反向对照（同一消费者程序，qemu 静态副本）：
   - 上游式构建（无 relaxed-ownership、未钉 sendmail/crontab、构建机信号空表）：C5/C6/C7a/C7b FAIL
     （`config.h` 中 `SENDMAIL` 为构建机的 `/usr/lib/sendmail`；C6 作业跑满 60.1 s）；
   - `--without-pcre` 构建：C1/C2/C3 FAIL（`#pcre` 规则被拒）。
   说明用例能区分每个适配点，不是空断言。

## 邮件发送与定时任务在鸿蒙 PC 上的可用性

- **邮件发送：可用，但需要自带传输程序。** 鸿蒙 PC 没有 MTA/sendmail；shush 通过配置项 `sendmail=<程序>`
  或环境变量 `SHUSH_SENDMAIL` 调用任意 sendmail 兼容程序（参数 `-t -i`，邮件经 stdin）。未配置时回落到
  `NOSENDMAIL` 并在 stderr 报 `execv(NOSENDMAIL): No such file or directory`（C4/C5）。
  上游 `exec()` 失败路径有个既有缺陷：`kill(SIGKILL, getpid())` 参数颠倒，随后 `sleep(5)` 再 `abort()`，
  所以这种失败要等约 5 秒，未修改（非本平台问题）。
- **定时任务：不可用。** 鸿蒙 PC 没有 crontab/crond，`CRONTAB` 钉为 `NOCRONTAB`；另外 OHOS musl 的
  `tmpfile()` 固定使用 `/data/local/tmp/tmpfile_XXXXXX`（不看 `TMPDIR`）。`shush -i/-u/-r` 以退出码 1 结束并
  给出诊断（C8）。作业需由外部调度器触发，shush 本身（运行、分析、报告）不依赖 cron。
- **syslog**：默认 facility 为 cron；musl 的 `syslog()` 在连不上 `/dev/log` 时静默丢弃（未设 LOG_CONS）。
  C2 特意在默认 syslog 下运行，CI 真机上由它验证该路径不影响作业与报告。
- **临时文件**：运行日志写 `$TMPDIR`（缺省 `/tmp`，鸿蒙上只读），使用时需设置 `TMPDIR`（C3）。

## 交付物

`archives/s/shush/`：`commands.json`（软件级，CLI 包）、`README.md`、`manifest.yaml`；
`archives/s/shush/1.2.3/`：`conanfile.py`、`conandata.yml`、`patches/`（12）、`test_package/`
（`conanfile.py`、`CMakeLists.txt`、`test_shush.c`、`MANIFEST.yml`）、`manifest.yaml`、`notes.md`；
知识草稿 `knowledge/drafts/E544-draft-31E6.{kv,md}`。

## 注意事项

- 配置文件与配置目录在鸿蒙 PC 上位于 HMDFS 时，会被投影为共享属主并带组写位；本包只拒绝全局可写文件。
- `timeout`/`lock` 中的信号名来自构建期生成的目标信号表；`-dM` 会多带出一个 `STKSZ` 名字（非信号，无害）。
- CI（aarch64 worker）上 C1-C8 首次执行交付的动态产物；C7b 在 HMDFS 上若 `chmod 0666` 被忽略会报 NOT RUN（不计通过）。
