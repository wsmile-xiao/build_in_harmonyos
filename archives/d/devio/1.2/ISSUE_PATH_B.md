# 路径 B 知识库扩展申请：消费者测试的判定链路不应经文件系统中间文件（OHOS 上 `/tmp` 只读）

## 申请信息

- **申请类型**：路径 B（知识库扩展，10 分候选）
- **关联任务**：#7093 devio 1.2
- **关联 PR**：`!9180`（`feat/devio-1.2`，配方 PR，CI build #43387 / #43615 校验通过）
- **知识草稿**：`knowledge/drafts/devio-1.2-consumer-test-no-tmpfile-popen-capture.kv` / `.md`
- **草稿 ID**：`DRAFT-DEVIO-CONSUMER-TEST-NO-TMPFILE-POPEN-CAPTURE`
- **提交方式**：草稿与配方归档**同一原子 PR 分支**（`feat/devio-1.2`）提交
- **申请日期**：2026-09-10

## 一、为什么这是"可跨仓库复用的知识"

本仓库所有 `test_package` 都要过 CI 的 L1「测试执行验证」。而**把运行输出落盘再
grep** 是消费者测试里最常见的写法之一，它在 OHOS 上会**凭空失败**——失败与被测
程序毫无关系，且失败信息（`grep: … No such file or directory`）会把排查方向误导到
"程序没跑起来"。本条把判据原则讲清（**判据不应引入与被测对象无关的隐变量**），
并给出可直接复制的内存直读模板，已在本批次 **4 个包**上复用验证。

## 二、症状与最小复现

```
ogrep: /tmp/devio_test.out: No such file or directory
otest devio 1.2: FAIL (exit 2, expected 0 from grep)
oERROR: devio/1.2 (test package): Error in test() method, line 41
o	ConanException: Error 1 while executing
o[fail] devio/1.2 — conan create failed
```

同一 PR 内其余判定（存在性 / 可执行位）全部 PASS —— 说明被测二进制正常。

```c
/* ❌ 把输出落盘再 grep（隐含假设 /tmp 可写） */
snprintf(cmd, sizeof(cmd),
    "%s 2>&1 | head -20 > /tmp/devio_test.out; "
    "grep -q 'Usage\\|read\\|write' /tmp/devio_test.out", argv[1]);
```

OHOS 实测（**消费级 HarmonyOS PC 本机 + CI runner 行为一致**）：

```
$ echo probe > /tmp/ohpcd_probe
sh: can't create /tmp/ohpcd_probe: Read-only file system
```

自检一行：`echo x > /tmp/probe || echo READONLY`

## 三、根因

测试判据把「文件系统 `/tmp` 可写」当成隐含前提，而该前提**与验证目标（被测程序能否
运行）无关**。OHOS 将 `/tmp` 设为只读后，这个无关变量直接变成失败源。
**同一根因实测命中两个包**：devio 1.2（`/tmp/devio_test.out`）与 devmem2 0.2
（`sh: can't create /tmp/devmem2_test.out: Read-only file system`）。

## 四、方案（可复用模板，已落地 4 个包）

```c
static int safe_run(const char *path, char *out, size_t outlen, int *code, int *killed) {
    snprintf(cmd, sizeof(cmd), "\"%s\" < /dev/null 2>&1", path);
    FILE *fp = popen(cmd, "r");                 /* 内存管道，全程不落盘 */
    ...
    *killed = !WIFEXITED(rc);
    if (*killed) return -3;
    if (*code == 126 || *code == 127 || *code == 255) return -4;   /* 跑不起来 */
    return 0;
}
```

判定顺序：① 排除跑不起来（`rc==-1` / 信号终止 / 126-127-255）；② 语义断言（含**从源码
抄出的**确定字面）；③ 工具预期非 0 时不断言 0。
必须落盘时改用 `$TMPDIR` 或 `self.build_folder` 下自建目录并**显式校验可写**，
**绝不写死 `/tmp`**。

**参考实现**：`archives/d/devio/1.2/…/test_devio.c`、`archives/d/devmem2/0.2/…/test_devmem2.c`、
`archives/c/crashme/2.8.5/…/test_crashme.c`、`archives/d/daa2iso/0.1.7e/…/test_daa2iso.c`。

## 五、验证证据

| 项 | 证据 |
|---|---|
| 失败 | devio !9180 build **#43387 之前**：`grep: /tmp/devio_test.out: No such file or directory` → `test()` ConanException |
| 修复 | 改为 popen 直读后 build **#43387 ✅**；devmem2 同法 **#43399 ✅** |
| 复用 | crashme **#43591 ✅**、daa2iso **#43588 ✅** 均按此模板书写 |
| 真机佐证 | HAD-W32（消费级 HarmonyOS PC）实测 `/tmp` 只读，与 CI runner 一致 |

## 六、查重声明

- **E325**（先解析可用 shell）：解决"**用哪个 shell**"；本条解决"**判据要不要经文件系统**"。
  同一测试里可能同时出现，但判据、失败信息、处置动作不同，**不合并**。
- **E223**（secure tmp 联合验证 owner/mode/MAC）：讲**产品侧临时目录安全属性**；
  本条是**测试判据的设计原则**，层次不同，**不合并**。
- 正式库以 `popen` 检索命中 E226 / E260，语境分别为"读取方式""启动器安全语义"，
  均非本条主题。

## 七、请评审确认

1. 是否认可本条目为**路径 B（贡献创新，10 分候选）**评审对象？
2. 是否建议把「判据不得经过文件系统中间文件（改用管道直读）」写入
   `docs/TEST_QUALITY_SPEC.md` 与 `templates/test_package/`？
3. 建议 CI 在 L1 失败信息里前置一句提示（"若日志含 Read-only file system，
   请检查测试是否写死 /tmp"），以便后续贡献者快速定位——是否可作为本条的落地项？
