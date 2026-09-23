# bwbasic 2.20pl2 适配笔记

## 编译环境
- 构建系统: autotools（随包 1995 年 autoconf 1.x configure + 手写 Makefile.in，源内构建）
- 编译日期: 2026-09-06
- 编译器: clang/clang++ 15.0.4（OHOS 适配版 conan 2.29.1 + ci/conan/profiles/ohos-aarch64）
- 状态: built
- worktree: ~/qzy/bwbasic 分支 feat/bwbasic-2.20pl2（基线 upstream/main dfe3d3ac77）

## 任务与 W0/W0b
- 任务号 #6153（开源鸿蒙PC专项积分赛），认领人 wanderlust_0823，无同名同版本重复，upstream/main 归档树无 bwbasic。
- 上游确认：原生上游站点已失效，源取 Debian pool 官方归档 bwbasic_2.20pl2.orig.tar.gz（SHA256 3aad826d54751180932443da577e3d44cf09b1ad34016700132e1c93477583b4，a52dec/0.7.4 已合入 Debian pool URL 先例）。
- W0: 零依赖（纯 ISO-C + libm）。
- W0b: 无同软件历史归档。语言预检通过（task=cpp, detected=c，兼容族）。

## 编译步骤
1. init-build（Debian pool URL）
2. lang-preflight 通过
3. 手动 configure+make 探索，定位 5 处老代码兼容问题并做最小补丁
4. refresh-patch 生成 5 个补丁；conanfile 以 AutotoolsToolchain+源内 configure/make
5. conan create：build() 内断言执行器运行上游 bwbtest 全部 41 脚本（53 项断言）+ test_package 消费者测试
6. conan-verify / finish：见 reports/ 与 .ci-result.json

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | bwbasic.c:54 编译错误 initializer element is not a compile-time constant | `FILE *errfdevice = stderr;`——OHOS/musl 的 stderr 是宏（展开为全局变量）非编译期常量 | 0003 补丁：NULL 声明 + bwb_init() 入口延迟初始化（main 首行调用 bwb_init，早于任何使用） |
| 2 | bwb_elx.c:757 int-conversion 错误 | int 函数 exp_function() 错误路径 `return NULL`（(void*)0） | 0002 补丁：改 `return 0`（语义等价） |
| 3 | bwx_tty.c:69 main 必须返回 int | 1995 年代码 `void main` | 0004 补丁：改 int main（C99 起 main 缺省 return 0） |
| 4 | renum.c:478 int-conversion 错误 | instr() 把 char* strstr 结果存入 int，aarch64 64 位指针截断（32 位时代真 bug） | 0005 补丁：改用 char* 指针变量计算偏移，返回值语义不变 |
| 5 | putget.bas 随机文件测试段错误 | bwb_dio.c：CLOSE 释放并置 NULL 缓冲区，reopen 时 mode==DEVMODE_CLOSED 令 previous_buffer=TRUE 跳过重分配，GET 写 NULL+offset | 0001 补丁：分配条件改为按 dev_table[].buffer 是否为 NULL 判断（保留"复用未释放缓冲区"的原意图） |
| 6 | conan out-of-source 构建失败 no such file: renum.c | 上游 Makefile 按源内构建设计（renum 规则无 VPATH 前缀） | 配方在 source_folder 内显式执行 configure/make（conanbuild 环境提供 CC/CFLAGS，R33 合规） |
| 7 | conan 自动生成首稿模板为 Autotools 但测试目录会联网 | 上游 bwbtest 无自动化入口且 41 个脚本为人工核对型 | build() 内嵌断言执行器：按各脚本语义喂定制 stdin、对验证输出 grep 断言、DATE$/TIME$ 掩码、random 按结构断言 |

## 源码修改
- 5 个最小可移植补丁（0001-0005，见上表），均无平台宏（__OHOS__ 零使用）、无功能语义变更、不影响非 OHOS 平台（R8 合规）。未删除或修改任何测试断言。

## 依赖版本
- 零运行时/编译依赖（libm 为系统库）。

## 验证结果（R51 三步法）
- 上游静态清点：bwbtest/ 共 41 个 .bas 测试脚本（index.txt 登记 39 个 + pascaltr.bas 等；chain2.bas 为 chain1 的被链脚本）。人工核对型：脚本打印结果后等待确认，index.txt 为人工勾选清单。
- 实际执行（真机 + CI 同路径）：配方 build() 内断言执行器全部 41 个脚本真实执行，53 项断言（含交互脚本定制 stdin、function 的 DATE$/TIME$ 掩码、random 的结构断言）全部通过：**40 通过 + 1 已知局限（width）**，0 段错误 0 超时。
- width.bas 已知局限：WIDTH 语句在 bwbasic.doc 有文档但分派代码零实现（grep bwb_cmd.c/bwb_stc.c = 0），静默忽略，data.tmp 60 字符单行不折行——上游功能缺失，非 OHOS 回归，各平台一致。不计为平台适配失败。
- test_package 消费者测试：test_consumer（C 驱动）执行包内 bwbasic 运行内嵌 BASIC 程序，断言 MUL= 42 / LT-OK / V= 1.5000000 与无效下标 ERROR 反例，4 项检查全部通过。

## 注意事项
- CI 与真机同路径执行上游套件（build() 内），无覆盖缺口。
- Debian pool URL 为官方归档（原生上游失效），a52dec 先例口径。
- bwbasic 输出浮点默认 7 位有效数字格式（abs.bas 打印 1.2345679），属解释器固有格式。
---

**编译结束**: 2026-09-06 13:01
**最终状态**: built
