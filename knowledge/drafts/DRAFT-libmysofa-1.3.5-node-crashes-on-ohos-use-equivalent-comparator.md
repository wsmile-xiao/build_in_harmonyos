# Draft: libmysofa 上游 node 比对测试在 OHOS 崩溃——原入口以 --jitless 恢复

> Source event: `libmysofa/1.3.5` OHOS 测试阶段，R01 2026-09-07 / R02 修订 2026-09-08。
> Draft only. Do not promote to `knowledge/graph/` without reviewer assignment.

## Problem

libmysofa 上游 41 项 ctest 中 16 项 compare.sh/compareIgnoreNew.sh 在普通 node
下全部 Failed，失败点是：

```text
Fatal error in , line 0
Check failed: 12 == (*__errno_location())
Signal 5 (core dumped)
```

即使 `node -e 'console.log("ok")'` 也崩溃——是 node/V8 在 OHOS armv8 镜像上
启动即挂（与 E400 同根因），而非 libmysofa 输出错误。

## R02 修订：恢复原始入口（首选）

实测（2026-09-08）：

```bash
node -e 'console.log(1)'        # 崩溃（Signal 5, errno 断言）
node --jitless -e 'console.log(1)'   # 正常输出 n2（E400 恢复条件可用）
NODE_OPTIONS=--jitless ctest -R '^(H20_44K|MIT_KEMAR|dtf_nh2|hrtf_c_nh898|CIPIC|FHK|LISTEN|Pulse|Tester|TU-Berlin|example_dummy|TestSOFA48).*$' --output-on-failure
# → 16/16 Passed, CTEST_EXIT=0（原始 ctest 注册入口，compare.sh/compareIgnoreNew.sh
#   原样调用 node json-diff.js，不改脚本、不改库），日志 SHA-256
#   487281faf05275a7a43ff8dfca43fcce64d5a544d1cfce8292e95a15cd1d117a
```

因此 16 项以**原始上游入口**原生通过；python 等价比对器（tests/pyjsoncmp.py）
保留为 R01 补充证据，不计入原始通过。

## Recommended handling

1. 不要为迁就崩溃的比对器改动库代码。
2. 首选：`NODE_OPTIONS=--jitless` 恢复 node 运行时后以原始 ctest 入口重跑
   （E400 已验证该模式可运行 node 脚本）。
3. 仅当 plain 与 --jitless 均无可用 node 时，才用 python 等价比对器
   （复刻 compare.sh/compareIgnoreNew.sh 语义：容差 0.05、ignore-new 模式），
   逐项记录 EQUAL 作为补充证据，并如实标注非原始通过；同时记录受影响入口的
   原始命令/退出码/首错/归属/恢复条件。

## Applicability

- 适用：上游测试依赖 node 比对的任何库在 OHOS 适配时；可跨库复用的模式是
  "E400 恢复条件 --jitless → 原始入口原生重跑 → 逐项 Passed 证据"。
- 反例/边界：OHOS 上连 --jitless 都无法运行的 node 构建时，才降级为等价比对器
  补充证据；等价比对器只替代比对步骤，不能替代被测工具本身的功能验证。
- 关系: similar_to E400（同根因 node/OHOS 崩溃；E400 聚焦 CLI 打包，本条目
  聚焦测试基建的原始入口恢复）；caused_by E400 根因。
