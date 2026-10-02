# E433 — strncmp 前缀比较的 n 超过字面量长度导致恒不匹配

> 草稿条目，来源：`rtl-wmbus/1.1.0` 适配 HarmonyOS PC（OHOS aarch64）。
> 状态：draft，待主编审核后 promote 为正式知识条目。

## 错误特征

```text
strncmp 前缀判断恒返回非 0（期望匹配 /lib/ld-linux- 却失配）
```

实际遇到的报错：

```text
strncmp(interp, "/lib/ld-linux-", 15) 对 "/lib/ld-linux-aarch64.so.1" 恒返回非 0
```

## 触发条件

- 分类：`c`
- 阶段：`testing`
- 工具：`test`
- 适用范围：C 代码中对路径/字符串做前缀判断时手写 strncmp 第三参数长度的场景

## 根因分析

字面量 "/lib/ld-linux-" 长度为 14，第 15 个字符即 '\0'；strncmp 会在该处停止比较，而目标串 /lib/ld-linux-aarch64.so.1 第 15 个字符是 'a'，因此永远不等。字符级前缀判断极易写错 n。

## 解决方案

### 推荐方案

做路径/前缀判断优先用 strncmp(ip, prefix, strlen(prefix))；需要包含关系时用 strstr 并单独校验目录部分。

**方案说明**：前缀比较的 n 用 strlen(prefix) 计算，不手数字面量长度。

```bash
strncmp(interp, "/lib/", 5) == 0 && strstr(interp, "ld-linux-aarch64.so.1")
```

### 禁止做法

- ❌ 不要手数字面量长度传给 strncmp——数错即恒失配，且失败现象与“路径不对”难以区分。
  - 原因：字面量隐含结尾 NUL，与 n 冲突时比较必然在 NUL 处终止。
  - 后果：断言恒失败，误判为被测产物链接了错误 libc，排查方向被带偏。

### 回退方案

改用 strstr + 前缀校验，或用带长度的结构（如把期望路径存为数组并用 sizeof-1 计算长度）。

## 验证

```bash
改为 14 或改用 strstr 组合后该断言通过；由 rtl-wmbus/1.1.0 ohos_special_test 实测。
```

## 关联条目

- 相关软件包：`rtl-wmbus/1.1.0`
- 完整踩坑记录：`archives/r/rtl-wmbus/1.1.0/notes.md` 第 7 节
