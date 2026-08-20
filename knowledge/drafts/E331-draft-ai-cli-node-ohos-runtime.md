# E331 - Node.js CLI 在 HarmonyOS 上的 JITless/WASM 能力边界与跨 UID 制品验证

> Contributor: xuguowei | Status: DRAFT | Created: 2026-08-20
> 关联库：ai-cli 0.4.2 | 关联 PR：#5837 | 关联 Issue：#2284

## 复用范围

本草稿适用于“Node.js 22+ CLI、预构建 JavaScript bundle、可选或必需 WASM
资源、Conan 二进制包、HarmonyOS 跨 UID package cache”组合。它不把
`--jitless` 单点做法申报为新知识：已有 `uglifycss` 适配记录使用过该参数，
本草稿新增的是能力矩阵和制品消费者验证边界。

## 现象与证据

在 OHOS armv8 真机 Node.js v24.13.0 上，普通 JIT 路径在业务 JavaScript
执行前稳定退出：

```text
Check failed: 12 == (*__errno_location())
Signal 5
```

`--v8-pool-size=1`、`--max-opt=0`、`--no-sparkplug`、`--no-maglev`、
`--no-turbofan` 和 `--single-threaded` 均不能消除该失败；只有
`--jitless` 完成 `--version` 和 `--help`。但同一设备执行：

```sh
node --jitless -e 'console.log(typeof WebAssembly)'
```

输出 `undefined`。当发布物包含 OpenH264 WASM 时，文本入口通过不能推导出
多媒体或编解码路径可用。

Shadow CI 还观察到 Conan package cache 以不同 UID 物化 launcher：缓存文件为
`0750`、属主 UID `20001006`，SSH 测试 UID 为 `20020083`。直接执行返回
exit 126；这不是配方中 `chmod 0755` 能单独解决的条件。

## 诊断流程

1. 固定上游提交和运行时版本，在最小入口先复现普通 JIT 的失败；记录退出码、
   stderr 和“业务 JS 尚未输出”的边界。
2. 逐步收窄 V8 参数，但不把任意单个参数当成根因；只有在相同输入下稳定
   通过的 `--jitless` 才进入目标平台 fallback。
3. 在 fallback 下单独探测 `typeof WebAssembly`，并按能力拆分声明：文本 CLI
   可以通过，WASM 依赖功能仍需单独验证或标记限制。
4. 对 package cache 取样记录 mode、owner UID、测试 UID；正向测试必须从
   Conan package folder 执行真实 launcher，不能改为源码入口。
5. OHOS 使用 `/system/bin/sh` 只是绕过缓存跨 UID 的直接执行条件，Linux 保留
   正常直接执行；同时移走 package `bin/`、`lib/`、`include/` 做破坏性负向测试，
   确认测试没有落到源码树或系统同名命令。

## 推荐实现边界

```text
Linux:  node <bundle> ...
OHOS:   node --jitless <bundle> ...
OHOS consumer: /system/bin/sh <package-folder>/test.sh
```

配方只在 OHOS 条件分支设置 `--jitless`，不把限制传播到 Linux。若命令需要
WASM，而当前运行时没有 WebAssembly，应报告能力缺口，而不是把文本 smoke
测试结果表述为完整功能通过。

## ai-cli 实例验证

上游 `v0.4.2` 源码提交 `2a72d32793e21839439e96adc8429453f17500f1` 使用 Bun
1.3.9 和锁文件执行 `bun test`：15 个文件，`135 pass, 0 fail`。第一次隔离
运行只因测试子进程找不到 `bun` 而失败；将同一个 Bun 目录加入 PATH 后，未修改
上游测试源码即全部通过。

OHOS 单包 Shadow CI r5：L0、KC、JC、L1、L4、L5、破坏性负向测试通过，构建
1/1；实际 package launcher 的离线消费者断言 7/7。L2 直接执行缓存 launcher
因跨 UID 权限非阻塞跳过，L1 通过目标 shell 执行同一 package folder 的真实
launcher。

## 禁止误用

- 不能因 `--jitless --help` 通过就宣称 WebAssembly/OpenH264 可用。
- 不能把初始 Bun PATH 配置失败统计为上游用例失败，也不能把修复 PATH 后的
  主机结果冒充 OHOS 运行时测试。
- 不能只用 `chmod +x` 解释跨 UID package cache 的直接执行问题。
- 不能让 test_package 直接引用源码、构建目录或系统安装的同名 `ai` 命令。
- 不能把报告中未证实的 V8/内核底层根因写成确定结论。

## 评审状态

这是与 ai-cli PR #5837 直接相关的 `draft: true` 草稿，用于响应路径 B
知识库扩展审查。是否提升为正式知识条目、最终编号和积分由知识库维护者及
评审委员会决定。
