# lgrind 3.67 适配笔记

## 编译环境
- 构建系统: makefile（无 configure；顶层 Makefile 依赖 TeX 生成 .sty/.dvi，OHOS 无 TeX，仅构建 source/ 下的 C 二进制）
- 编译日期: 2026-09-27
- 编译器: clang 15.0.4（OHOS 本机 aarch64，musl）
- 状态: built

## 编译步骤

```bash
# 顶层 Makefile 的 lgrind 目标即等价于：
cd source
make -j2 DEFSFILE=/usr/local/share/lgrind/lgrindef VERSION=3.67 CC=clang
# retest 测试工具单独构建（见问题 #2/#3）
clang -O2 -I. -c retest.c -o retest.o && clang -O2 -o retest retest.o regexp.o
# staging（source/Makefile 的 install 使用 install -s，改用手工 staging）
cp lgrind $TEST_PREFIX/bin/
cp ../lgrindef $TEST_PREFIX/share/lgrind/   # 运行时语言定义库，经 lgrind -d <file> 指定
cp lgrind.1  $TEST_PREFIX/man/man1/
cp lgrindef.5 $TEST_PREFIX/man/man5/
```

运行时契约：二进制默认读编译期 `DEFSFILE` 路径；OHOS 消费场景必须随包分发 `lgrindef`
数据文件并以 `lgrind -d <包内 lgrindef>` 调用（T4b 已验证缺失时的诊断行为）。
TeX 侧产物（lgrind.sty/lgrind.dvi）不在 OHOS 适配范围（CI 无 TeX 工具链）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | lgutil.c:280 `error: non-void function 'parsevartab' should return a value` | 上游 K&R 时代 `return;` 落在 `varsubst *` 函数，旧 gcc 宽容为警告，clang 15 报错 | `return;` → `return NULL;`（lgutil.c，语义为失败返回空表） |
| 2 | retest 链接失败 duplicate symbol `_escaped`（retest.o vs regexp.o） | retest.c 声明 `char *_escaped`，regexp.c:354 定义 `boolean _escaped`（类型冲突 + 重复定义）；-fcommon 合并不同类型 common 符号又触发 lld `R_AARCH64_LDST64_ABS_LO12_NC` 对齐错误 | retest.c 改为 `extern boolean _escaped;` 并包含 regexp.h |
| 3 | retest 链接失败 duplicate symbol `_start`（与 Scrt1.o 冲突） | OHOS SDK 链接器以 `_start` 为 ELF 入口符号；retest.c 的 `_start` 是私有全局变量且 regexp.c 并不引用 | 重命名 `retest_start` |
| 4 | retest 运行时 SIGSEGV（expmatch 空指针调用） | regexp.c v1.3 引入函数指针 `re_strncmp`（仅 lgrind.c:849 初始化），retest.c 未初始化即调用 | retest.c 增加 `init_retest_matching()`：`re_strncmp = l_onecase ? lc_strncmp : strncmp;` |

## 源码修改（探索阶段，补丁由 refresh-patch --auto 固化）

- `source/lgutil.c`：`parsevartab` 失败路径 `return;` → `return NULL;`
- `source/retest.c`（上游测试工具，不影响产品二进制）：include regexp.h/string.h；`_escaped` 改 extern boolean；`_start` 改名 `retest_start`；expmatch 调用补第 3 参 `&retest_start`（上游 3 参调用与 4 参原型不符）；初始化 `re_strncmp`

## 依赖版本

无 conan 依赖（preflight_check.sh 验证：无依赖声明，制品仓检查通过）。
构建工具链：clang 15.0.4、GNU Make 4.4.1（OHOS 本机）。

## 上游测试申报（R51 三步法）

**清点**：上游无 tests/ 目录、无 make check / ctest / pytest / CI 配置（1999 年 CTAN 包）。
可执行测试入口共 2 处：`source/retest.c`（regexp 交互测试器）与 `example/` 黄金样例链
（egcprog.c/egmasm.asm → lgrind -i 生成 .lg，结构断言）。`-d!` 自改写二进制模式跳过
（对可执行文件原地补丁，OHOS HMDFS 不可逆风险，非消费路径）。

**实测**（runner: /data/storage/el2/base/cache/logs/run-lgrind-upstream-tests.sh，
报告: upstream-test-report.txt，retest 日志: retest-final.txt）：

| 组 | 用例 | 结果 |
|----|------|------|
| T1 retest | T1a 字面量 abc/abx；T1c 组+交替 a(b|c)d；T1d 交替 (a\|b)c；T1e 字面量 a* | 4/4 通过 |
| T2 example | T2a egcprog.c 生成 exit=0；T2b \File 头；T2c \Proc{main}；T2d 逐行覆盖(LB=34>=src=27)；T2e -lmasm | 5/5 通过 |
| T3 v2lg | T3a verbatim→%[] 转换 | 1/1 通过 |
| T4 鸿蒙新增消费者用例 | T4a staging 布局 -d 解析完整文档包络；T4b 缺 defs 诊断；T4c -lc++ 语言分发 | 3/3 通过 |

**汇总：13 通过 / 0 失败 / 1 跳过（-d!，理由如上）。**
test_package 不能替代上游测试：T1-T3 即上游入口实测；T4 为本次适配新增的鸿蒙消费者可行性用例，
test_package 将复用 T4a 形态（staged lgrind -d <res>/lgrindef 处理样例 C 文件）。

## 验证结果

```bash
$TEST_PREFIX/bin/lgrind -d $TEST_PREFIX/share/lgrind/lgrindef smoke.c
# 输出完整 \documentclass...\begin{lgrind}...\Proc{main}...\end{lgrind} 文档，exit=0
# file: ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1)
```

## 注意事项

- 源 URL：https://mirrors.ctan.org/support/lgrind.zip（CTAN 官方，version 3.67，sha256 见 conandata.yml）
- 包为命令行工具（R38）：归档需含 commands.json（name=lgrind, type=tool）
- lgrindef 数据文件必须随包分发（cpp_info.resdirs），消费方以 `-d` 传入
- lgrind.c 另有 2 条无害告警（dangling-else / pointer-compare），上游固有，不改
---

**编译结束**: 2026-09-27 15:29
**最终状态**: built
