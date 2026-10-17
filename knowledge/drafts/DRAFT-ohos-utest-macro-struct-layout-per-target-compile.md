# DRAFT-ohos-utest-macro-struct-layout-per-target-compile：test-only 编译宏（-DUTEST）给共用结构体加 mock 字段——镜像上游按 target 全量编译

> Contributor: xiao921924 | Status: Draft | Updated: 2026-09-03
> Source: burp 3.3.0 HarmonyOS PC 适配（-DUTEST 下 asfd 追加 mock 字段，共享 libburp 方案评估后否决）

## 现象

部分库的测试模式靠编译宏切换（burp：`-DUTEST`）：宏开启时**共用结构体
被改写**（burp 的 `asfd` 追加 mock 的 send/recv 指针），`main()` 被
`#ifndef UTEST` 保护。conanfile 若图省事把主源文件抽成共享库
`libburp`（一次编译、主程序与 runner 复用），会产生**无编译报错**的
ODR 隐患：

```
(a) 库与 runner 宏定义不一致 → 同一结构体两处布局不同
    → 跨 .so 边界读写 = 静默内存错乱（mojibake/崩溃）
(b) main 保护宏不一致 → 两个 main（链接错误）或零个 main
```

上游 autotools 的设计里**根本没有共享库**：每个 target 各自全量编译
所需 `.c`，宏按 target 设置。

## 与现有知识的关系

- 现有索引无 test-only 编译宏 / 结构体布局 ODR 类条目（已对照
  knowledge/graph/index.tsv 全量查重）。
- 与 E472（test_package ELF 签名）无关。
- 本条是 build-system 新类别：C/C++ 库移植中"共享库优化"的适用
  边界判定。

## 方案

1. 从 `Makefile.am` 读出每个 target 的**真实源集合与 CFLAGS 差异**
   （burp：`burp_SOURCES` = main_SOURCES；`runner_SOURCES` =
   main_SOURCES ∪ utest，runner 带 `-DUTEST`）。
2. 结构体/宏改写点全量 grep 清单化：
   `grep -nE 'defined\(UTEST\)|UTEST' src/*.c src/*.h`
3. 镜像上游按 target 全量编译，**不要自创共享库**：
   - 主 target（`burp`）：主源集合编译，不带 `-DUTEST`；
   - test target（`runner`）：主源集合 ∪ utest 源编译，带 `-DUTEST`；
   - 源文件跨 target 重复出现是**预期行为**（各自编译，与上游 make
     一致），勿"优化"成共享目标；
   - 若 runner 复用含 `main()` 的文件（burp 的 prog.c），先确认
     `main()` 包在 `#ifndef UTEST` 后——runner 带 -DUTEST 编译时该
     main 自动消失，不冲突（burp 实测成立）。
4. 验证：两 target 均编译通过；runner 跑通上游套件；用 sizeof 打印
   或断言核对关键结构体大小在 target 内一致；主 target 行为不被
   test 宏污染。

## 验证证据

- burp 3.3.0：否决共享 `libburp` 方案（asfd 在 -DUTEST 下布局变化，
  库与 runner 宏不一致即 ODR 隐患），改用 per-target 全量编译
  （111 源 → burp，177 源 → runner），`prog.c` 的 main 确认包在
  `#ifndef UTEST` 后，runner 复用 main_SOURCES 无 main 冲突；
  上游 check 套件 233 例正常执行（226 通过 / 7 环境性失败）。
- 适用软件：所有"测试模式靠编译宏切换 + 共用结构体被宏改写"的
  C/C++ 库（UTEST/TESTING/MOCK 类宏）。
