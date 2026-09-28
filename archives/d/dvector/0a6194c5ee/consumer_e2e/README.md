# dvector HarmonyOS 特有消费者端到端用例（consumer_e2e）

R02 修复规则 12「鸿蒙特有测试」：随 PR #13002 交付的独立、可失败、端到端消费者用例。

## 与本 PR 中 test_package 的关系（范围分离）

| 项 | test_package/test.c（Conan L1 配方自检） | consumer_e2e/consumer_e2e.c（鸿蒙特有端到端用例） |
|---|---|---|
| 角色 | 配方完整性断言级自检（16 断言） | 完整消费者端到端用例（真实渲染管线流程） |
| 触发 | `conan create` 时由 Conan 执行 | 目标 OH 设备上独立构建并运行 |
| 校验 | 函数级断言 | 管线级解析解对照 + 可见性统计交叉验证 |
| 可失败 | 是（断言失败非零） | 是（任何校验失败非零退出） |

## 构建（OHOS aarch64 本机）

```bash
clang -std=c99 -O2 -I<dvector 头文件目录> consumer_e2e.c -lm -o consumer_e2e
```

## 运行

```bash
./consumer_e2e
# 期望尾部输出: === 结果: ALL PASS (0 failures) === ，退出码 0
# 任何校验失败: 输出 FAILED 并返回非零退出码（可失败）
```

## 用例覆盖（端到端管线）

1. LookAt 视图矩阵解析校验（原点 → 相机前方 z=-5）
2. 透视投影 + 透视除法（视场中心 → NDC (0,0)）
3. 四元数旋转 vs 矩阵旋转一致性
4. 8 顶点 View→Projection→裁剪空间可见性 + frst 视锥剔除交叉统计
5. 相机前方点视锥可见性端到端对照
