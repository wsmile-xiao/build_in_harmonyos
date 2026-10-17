# codonw 1.4.4 适配笔记

## 编译环境
- 构建系统: makefile（上游手写 Makefile，无 configure/install 目标）
- 编译日期: 2026-09-08
- 编译器: clang（profile tools.build:compiler_executables 提供，命令行 CC= 传入）
- 状态: built

## 编译步骤

```bash
make -C <source> all CC="/data/service/hnp/bin/clang" LN="cp -f"
```

- `all` = codonw 主程序 + links（17 个 argv0 分析别名）
- 上游 Makefile 硬编码 `CC=cc`（OHOS 设备无 cc），经 make 命令行变量覆盖
- 无 install 目标，package() 手工搬运 codonw + 17 个别名副本到 bin/

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `ln -f codonw rscu` 报 "cannot create hard link ... Operation not permitted" | HMDFS 禁止硬链接（知识库 E079） | make 命令行 `LN="cp -f"` 覆盖（GNU make 命令行变量优先于文件内赋值）；argv0 分发对副本同样生效 |
| 2 | conan apply_conandata_patches 失败 "can't backup original file to Makefile.orig" | 源码包自带 Makefile.orig，与 patch 的备份文件名冲突 | 放弃补丁路线，改用 make 变量覆盖（问题 1 同解） |
| 3 | test() 中 tidy 别名报 "This command line parameter was not recognised" | argv0 别名只接受 [inputfile] [outputfile] 两参 | 消费者测试去掉第三个 bulk 文件参数 |

## 源码修改

无补丁（无源码修改）。平台适配通过 make 命令行变量 `LN="cp -f"` 完成，见 conanfile.py build()。

## 依赖版本

无外部依赖（仅 libc/libm）。

## 上游测试清点（R51）

- 上游无自动化测试套件：Makefile 目标仅有 all/codonw/links/clean/cleanall/realclean，
  无 check/test 目标，源码树无 tests/ 目录；上游静态用例数 N_static = 0。
- 消费者测试（test_package）：以真实基因输入（testgene.dat，70 个密码子的合成 CDS）运行
  打包后的 codonw（`-gc -enc` 指数分析，断言标题与数值输出）和 tidy（argv0 别名格式转换，
  断言输出内容），conan test() 全部通过（1/1 passed）。
- 补充实测（探索构建，设备 OHOS 原生）：`codonw input.dat out -nomenu -silent -human -rscu -gc -enc`
  对上游自带 40 基因输入 input.dat 完整分析成功，输出 Nc/GC 表（样例见下）：

```text
title           	Nc	GC
YCG9_Probable…	54.09	0.394
YCG8…          	52.46	0.446
```

## 注意事项

- codonW.hlp（交互帮助文件）不参与 CLI 分析，仅菜单 h 帮助使用且按 CWD 相对路径查找，
  未打包；已知限制，不影响命令行功能。
- argv0 别名以独立副本（cp -f）而非硬链接交付，行为与上游 links 目标等价。
- 输出文件截断标题至 25 字符为上游行为。

## 编译结束

- 最终状态: built（conan-verify 全过、W3 本地 CI 通过、W4 审计 P0=0 P1=0）
- 结束标记: 2026-09-09，commit 1cc4570b746744590c2c059276063aa7359b08dc

- 2026-09-09 提交元数据刷新（触发分支同步）
