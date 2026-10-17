# DRAFT: rindex 是 OHOS libc 移除的遗留符号（irqbalance 1.9.4）

- **来源**：irqbalance 1.9.4 首轮适配（feat/irqbalance-1.9.4）
- **错误特征**：链接期 `undefined symbol: rindex`，clang 同时提示 `did you mean: index`。
- **根因**：OHOS / HarmonyOS PC（aarch64-linux-ohos）libc 不再导出 BSD 遗留函数
  `rindex`/`index`，仅保留标准 C `strrchr`/`strchr`；遗留 autotools 源码直接调用
  `rindex(path, '/')` 即触发。
- **修复**：`cputree.c:304` 将 `rindex(path, '/')` 改为 `strrchr(path, '/')`
  （返回 `char*`、语义等价），最小补丁 `patches/0002-cputree.c.patch`。
- **验证**：conan create 干净构建链接通过；`irqbalance --version` 输出
  `irqbalance version 1.9.4`；test_package 真实执行通过。
- **适用边界**：任何在 OHOS 上构建且使用 `rindex`/`index` 的 C/C++ 项目；
  含 `strchr` 反向语义，不适用需要区分大小写或搜索多个字符的场景。
- **反例**：若仅编译未链接（如只产 .o），不会暴露；动态库场景同受影响。

## 查重结论（七轴）

| 轴 | 结论 | 依据 |
|---|---|---|
| exact_duplicate | 未命中 | 正式条目与草稿中无独立覆盖 rindex→strrchr 的条目 |
| causal_duplicate | 未命中 | 无同因果链条条目 |
| trigger_overlap | 部分重叠 | DRAFT-centerim 四连坑含 rindex 一条，但其根因是 gettext intl/version 遮蔽与老 C++ 混淆，非独立 libc 遗留符号主题 |
| solution_overlap | 部分重叠 | 同用 source-patch，但中心主题不同 |
| combination_novelty | 新增 | irqbalance 为纯 C autotools 守护进程，无 gettext/老 C++ 维度 |
| boundary_novelty | 新增 | 适用范围（纯 C、OHOS libc 遗留符号）独立 |
| test_migration_novelty | 新增 | 上游 tests/runoneshot.sh 1/1 通过，无迁移测试差异 |

- `similar_to`：E007（config.guess HarmonyOS）、E136（configure umask/TMPDIR）为同库
  其他适配问题，主题不同；centerim 草稿为部分重叠。
- 判定：`new_draft`（路径 B 知识库扩展候选）。