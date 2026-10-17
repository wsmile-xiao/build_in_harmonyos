# pcc-libs 1.2.0-devel-20211015 适配笔记

## 编译环境

- 构建系统: autotools
- 编译日期: 2026-10-02
- 编译地点: HarmonyOS PC 真机（aarch64，musl），非交叉模拟
- 目标: aarch64-linux-ohos（host profile `ohos-aarch64`，build 与 host 同 profile）
- 编译器: OHOS SDK clang 15（`--target=aarch64-linux-ohos`）
- 状态: built（conan create 含 test_package 全绿，消费者断言 60/60 真机原生执行通过，其中鸿蒙特有用例 14/14）

## 源码来源（R39 说明，重要）

本配方使用 **官方上游仓库 PortableCC/pcc-libs**（github.com/PortableCC/pcc-libs），
固定在 commit `5fd7d9e3441968c03914cdc1e963ea55a943284b`（2021-10-14）——
与任务版本 `1.2.0-devel-20211015`（2021-10-15 快照）对应的最后一个提交。

选择依据（均有实测证据）：

1. 仓库全部提交作者是 pcc 维护者本人 Anders Magnusson
   `<ragge@tethuvudet.se>`（GitHub API 可查）；Wikipedia 与项目索引均把
   github.com/portablecc 列为 pcc 的仓库。
2. 历史发行站点 pcc.ludd.ltu.se 已无法解析（2026-10-02 实测 DNS 失败），
   无法作为可复现来源。
3. github.com/IanHarvey/pcc-libs 是个人导入镜像（README 自述 "THIS IS NOT
   MY CODE"，内容为 2018-09 的 CVS 快照），按 R39 "禁止个人 fork" 不采用。
   早期开发曾在该镜像上进行，切换到官方树后补丁集重新生成并全量复验。

官方仓库 devel 线无 tag/release，故用 commit 归档 URL + sha256 锁定，
无论分支后续如何移动都可以复现同一棵源码树。

## 上游测试清点（R51 申报）

结论：**上游没有测试套件。**

清点证据（在官方 5fd7d9e34419 解压树上核对）：

```
$ find . -type d \( -name tests -o -name test \)
（无输出）
$ grep -rn 'check:' --include='Makefile*' .
（无输出）
$ grep -rn 'ctest\|pytest\|AC_CONFIG_TESTDIR' .
（无输出）
$ grep -n 'TESTS\|check_PROGRAMS' Makefile.in */Makefile.in
（无输出）
```

因此 R51 的"上游测试"部分没有可运行对象；本任务的实测覆盖来自
`test_package/` 的消费者断言（46 条，真机原生执行，全部通过）。

## 编译步骤

```bash
# 配方内部实际执行（静态/共享开关由 conan 工具链按 options.shared 自动注入，
# 上游 configure 不识别这两个开关，仅以 warning 忽略；库本身只产 .a）
./configure --host=aarch64-linux-ohos
make
make install
```

`--host` 是配方唯一显式传入的平台参数，build 三元组由补丁 0001 增强后的
`config.guess` 在真机上原生识别为 `aarch64-unknown-linux-ohos`。
没有使用 `--build=` 强行绕过的做法——官方知识库 E007 明确禁止。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `system 'ohos' not recognized` | 上游 config.sub 不认识 OHOS | 补丁 0001：config.sub 增加 `linux-ohos*` 内核-OS 组合、`ohos-linux` 别名与 `-linux-ohos*` OS 列表项 |
| 2 | config.guess 在真机上报 `unable to guess system type` | `uname -s` 返回 HarmonyOS，2021 年代 config.guess 不识别；且该年代分支是 `echo`/`exit` 风格，末尾没有 `echo $GUESS` | 补丁 0001：增加 `*:HarmonyOS:*:*` 分支，按该年代风格 `echo "${MACHINE}-unknown-linux-ohos"; exit ;;` |
| 3 | `'aarch64-unknown-linux-ohos' is not (yet) supported` | 平台白名单只有 linux/darwin/… 等 | 补丁 0002：configure.ac **与预生成的 configure** 同时加 `linux-ohos*` 分支（该仓库把 configure 一并签入，构建不会跑 autoreconf，只改 .ac 完全无效） |
| 4 | `ohos*)` 分支不生效 | `config.sub` 把目标 OS 规范化为 `linux-ohos`，而 shell 的 `case` 模式是**前缀匹配**，`linux*)` 会先生效 | 分支名改为 `linux-ohos*` 并放在 `linux*)` 之前 |
| 5 | `#error FIXME long double` | cxmuldiv.c 只实现 x87 与 128 位大端布局 | 补丁 0003：增加 `__LDBL_MANT_DIG__ == 113` 分支（IEEE binary128，小端） |
| 6 | 复数例程段错误（`__muldc3`/`__mulxc3`） | signbit.c 用 `__FLOAT_WORD_ORDER__` 选字序，但 **clang 不定义该宏**；未定义 ≈ 0，恒等于"非小端"，`__signbitl/__signbitd` 读到尾数位 | 补丁 0004：新增 `PCC_FLOAT_WORD_ORDER`，优先 `__FLOAT_WORD_ORDER__`，回退 `__BYTE_ORDER__` |
| 7 | 双精度算术全部返回垃圾值（真机实测，addsf3 正确而 adddf3 错误） | 上游 `libsoftfloat/arch/aarch64/aarch64-gcc.h` 用 32 位 ARM 宏 `__VFP_FP__`/`__ARMEB__` 判断是否对 double 做 FPA 字交换；aarch64 编译器两个宏都不定义，误入字交换分支，所有 double 位模式被前后 32 位对调 | 补丁 0005：把 `__aarch64__` 加入自然序（无交换）条件。此问题单精度不受影响、比较函数恰好幸存，只有真机运行消费者断言才暴露 |
| 8 | csu 不产出任何目标文件 | csu/Makefile.in 只在 `csu/$(TARGOS)/` 存在时才构建 | 补丁 0006：新增 `csu/ohos`，ctor 与 dtor 表项宽度统一由 `__SIZEOF_POINTER__` 决定（上游 `__x86_64__` 判据在 aarch64 上会让 dtor 表项保持 32 位，本补丁一并修正） |
| 9 | conan 报 `target file does not exist` | `diff -uN` 的裸补丁头缺少新建文件标记 | 补丁改用 `git diff` 风格头（`diff --git` + `new file mode` + `--- /dev/null`） |

## 源码修改

七个补丁，全部为"追加平台分支"或"修复可移植性缺陷"，不删除任何平台既有代码：

| 补丁 | 文件 | 内容 |
|------|------|------|
| 0001 | config.guess, config.sub | 识别 HarmonyOS 与 `linux-ohos` 三元组 |
| 0002 | configure, configure.ac | 增加 `linux-ohos*` 平台分支 |
| 0003 | libpcc/cxmuldiv.c | 增加 IEEE binary128 的 long double 位布局、符号清除/缩放与 logb 解码 |
| 0004 | libpcc/signbit.c | 字节序判断在无 `__FLOAT_WORD_ORDER__` 时回退到 `__BYTE_ORDER__` |
| 0005 | libsoftfloat/arch/aarch64/aarch64-gcc.h | AArch64 恒取自然序，禁用 FPA 字交换 |
| 0006 | csu/ohos/* | 新增 OHOS 启动代码目录（5 个文件），ctor/dtor 表宽统一按指针宽度 |
| 0007 | configure | config.status 的临时目录改用 `umask 022` 创建（HMDFS 上 2700 目录创建者自己不可写） |

说明：上游自 2020-06（"libpcc support for aarch64, from Odidev"）已自带
`libsoftfloat/arch/aarch64` 目录，因此不需要（也不应该）新建该目录——
早期开发时针对 2018 镜像树的"新增 aarch64 目录"补丁在官方树上作废，
替换为上表 0005 的最小修复。

补丁 0007 说明（对应知识条目 E114 / E011）：autoconf 生成 `config.status` 时以
`umask 077 && mktemp -d "./confXXXXXX"` 创建临时目录，在 HMDFS 类存储上得到的是
`drwx--S---`(2700) 目录——**创建它的进程自己也无法在其中写文件**，于是
`./config.status: line 586: ./confXXXXXX/subs1.awk: Permission denied` →
`config.status: error: could not setup config files machinery`。把两处
`umask 077` 改为 `umask 022`（含 `mkdir` 回退分支）即可，这也是本仓库 1375 个
既有补丁采用的同一做法。该修改只影响临时目录权限，不改变任何构建语义。

## 依赖版本

无外部依赖。pcc-libs 是纯 C 运行时，只使用目标 C 库与编译器内建函数。

## 上游缺陷（非适配引入，未修改）

在**未修改的官方树**上真机原生复现：

| 函数 | 现象 | 复现方式 |
|------|------|----------|
| `__divsf3` | 任何除法都返回 0（`divsf3(3.0f, 2.0f) == 0.0f`） | 官方树 aarch64 原生构建，直接链接 `libpccsoftfloat.a` 调用 |

勘误：早期在 2018 镜像快照上记录的 `__divdf3 返回 0` 与 `__ltdf2 不对称`
两个现象，在官方 2021-10 树上**不复现**（实测 `__divdf3(3.0, 2.0) == 1.5`、
`__ltdf2(3.0, 2.0) == 0`），系镜像树源码较旧所致，不应记为官方上游缺陷。

`__divsf3` 未在本次修改，以免超出"适配"范围并改变上游语义；消费者测试
对它不做断言。

## 验证结果（真机）

```bash
$ conan create . -pr:h=ci/conan/profiles/ohos-aarch64 \
                -pr:b=ci/conan/profiles/ohos-aarch64 --build='pcc-libs/*'
...
pcc-libs/1.2.0-devel-20211015: package(): Packaged 2 '.a' files: libpccsoftfloat.a, libpcc.a
pcc-libs/1.2.0-devel-20211015: package(): Packaged 6 '.o' files
pcc-libs/1.2.0-devel-20211015: package(): Packaged 11 '.h' files
...
======== Launching test_package ========
pcc-libs consumer checks (aarch64-linux-ohos)
60/60 assertions passed
14/14 OHOS-specific assertions passed
HMBS_TEST_PACKAGE_RESULT={"total":60,"passed":60,"failed":0,"skipped":0,"ohosCases":14,"ohosPassed":14}
```

产物架构核验（llvm-readelf / llvm-ar）：

```
crtbegin.o / crtend.o : ELF64, Machine: AArch64
libpcc.a              : 24 members，全部 ELF64 / AArch64
libpccsoftfloat.a     : 27 members，全部 ELF64 / AArch64
```

安装布局：`<prefix>/lib/pcc/aarch64-unknown-linux-ohos/1.2.0.DEVEL/{lib,include}`。

## 注意事项

- 配方刻意**不**声明 `cpp_info.libs`：该运行时不是常规 `-lpcc` 库，若按常规库
  暴露，下游 CMakeDeps 会生成错误的 `-I/-L` 组合；运行时目录通过
  `PCC_LIBS_ROOT` 环境变量对外暴露，test_package 会交叉核对。
- pcc-libs 是给 pcc 编译器用的运行时。"用 pcc 编译程序并链接 libpcc" 的
  端到端路径需要可运行的 pcc（pcc 自身无 aarch64 后端，属另一个任务），
  本任务以消费者断言覆盖运行时 API。
- 若因评审意见需要改配方重新上传，按 R37 递增版本号
  （`1.2.0-devel-20211015.1`），不要复用同一版本号。
---

**编译结束**: 2026-10-02 23:34
**最终状态**: built
