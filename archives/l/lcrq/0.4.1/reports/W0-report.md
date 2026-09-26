# lcrq 0.4.1 W0 报告（依赖发布检查 + 静态分析 + 真机构建）

**日期**: 2026-09-20
**分支**: feat/lcrq-0.4.1（worktree D:\harmonyos\worktrees\lcrq）
**结论**: 前置适配就绪；作为 librecast 0.11.2 硬链接依赖先行适配

## W0 依赖发布检查

- lcrq 自身：纯 C 无外部依赖 → 无依赖检查项
- ohpcd 制品仓 `lcrq/*`：0 条（本适配即填补此空缺）
- 下游依赖方：librecast 0.11.2（硬链接依赖，独立 PR 声明依赖本包）

## 依赖图

```text
lcrq/0.4.1
`-- (无依赖，纯 C)
下游: librecast/0.11.2 --(硬链接依赖)--> lcrq/0.4.1
```

## 源码

- URL: https://codeberg.org/librecast/lcrq/archive/v0.4.1.tar.gz（官方仓库 tag 归档）
- sha256: f342fbcd1b4617cd14149d428cb6b596aa4cf57b1dbc2f954320dce2acd42e1f

## 静态分析结论

- autotools；非 VPATH 感知 → in-tree 构建；仅共享库产物
- config.guess 2022-05-25 无 HarmonyOS 识别 → 0001/0002 补丁（repo 脚本生成）
- 顶层 install 带 doc/man 页（裸 install）→ 0003 裁剪
- src/Makefile.in 3 处 `ln -sf` → 0004 改 cp -f
- aarch64 NEON 实现由上游按 CPU 分派，无需干预
- 测试：20 用例纯算法（0000-* RaptorQ / 0001-* q 队列），断言 ≈146，无网络依赖

## 真机构建记录

- 设备：HarmonyOS PC aarch64（HongMeng 1.12.0，LAN 10.62.178.77）
- profile：ci/conan/profiles/ohos-aarch64（compiler_executables=/data/service/hnp/bin/clang*）
- 方式：conan create（-j1）
- 结果：待构建后回填
