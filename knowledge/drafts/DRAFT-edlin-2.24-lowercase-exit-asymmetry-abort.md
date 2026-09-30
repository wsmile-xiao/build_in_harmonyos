# DRAFT: 命令 switch 大小写归一化与分支内原始判断不一致 → "功能成功却 Signal 6 abort"

> 草稿条目 `DRAFT-edlin-2.24-lowercase-exit-asymmetry-abort`（.kv 配对见同目录同名 .kv）

## 症状（极具迷惑性的三层洋葱）

管道驱动交互式工具时，**功能断言全部通过、副作用全部正确，但退出码 134
（Signal 6 / core dumped）**。日志形态：

```
PASS: T1 output file created
PASS: T1 line 1 content saved      ← 文件真的写对了
Signal 6 (core dumped)
FAIL: T1 exit code is 0 after e
```

## 根因（edlin 2.24 实测，上游 bug）

上游命令分发把命令字母归一化后再匹配 switch，但**分支内部重新检查原始字符**：

```c
switch (tolower((unsigned char)(*ip))) {     /* 'E' 归一为 'e'，大写可进入分支 */
case 'e': case 'w':
    exiting = (*ip == 'e') && quitting ();   /* ← 检查的是原始大写 'E'，恒 false！ */
    ... write_file (...);                    /* 文件照写 → 功能断言全过 */
```

连锁后果：大写 `E` 保存文件但 `exiting` 恒 0 → 主循环继续 → stdin 耗尽 →
`read_line` 返回 NULL → 上游防御代码 `if (s == 0) abort();` → **Signal 6**。
小写命令则完全正常——大小写行为不对称。

## 三步定位法（本轮实测有效的顺序）

1. **找 abort() 点**：grep 上游 `abort()`/`assert()`，确认是"输入耗尽后的防御退出"
   还是内存错误（本例是前者，errno/ferror 全 0，可排除堆损坏）；
2. **对比正交用例**：构造"同类命令、不同字母/大小写"的对照（Q+Y 正常、E+Y abort）
   → 差异立即锁定在**分支内部对该命令字符的二次判断**；
3. **确认确认提示语义**： quitting() 类函数会再读一行（`Really quit (Y/n)?`），
   大写 E 下该提示根本没出现（短路求值跳过）——提示缺位即短路铁证。

## 方案

- **零补丁优先**：测试/消费者改用小写命令（switch 语义等价，原始判断为真）；
  上游行为（大写不退出）如实记录在 notes/manifest，不代上游"修 bug"；
- 若工具必须支持大写（用户习惯），才考虑 source patch 把分支内判断改为
  `tolower((unsigned char)(*ip)) == 'e'`——补丁说明里必须附上本条根因。

## 验证（edlin 2.24 真机）

小写 `e\nY\n` 序列：exit 0、文件内容正确；8/8 断言通过，shadow CI 全绿。
对照大写 `E\nY\n`：文件内容正确但 exit 134（100% 复现，与 cwd/stdin 形态无关）。

## 适用边界

- 只适用于"switch/分发层做了大小写归一、分支内又用原始字符判断"的代码模式
  （grep 特征：同文件同时出现 `tolower` 与 `== 'x'` 的字符比较）；
- errno≠0 或 ferror(stdin)≠0 的 abort 先查内存/堆损坏（musl double free 等），
  不要套用本条；
- 与 DRAFT-8960（stdin 不关闭导致阻塞超时）区分：本条是**耗尽后 abort**，
  那条是**永不耗尽阻塞**。
