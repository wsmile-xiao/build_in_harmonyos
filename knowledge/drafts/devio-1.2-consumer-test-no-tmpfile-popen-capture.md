# 消费者测试的判定链路不应经文件系统中间文件（OHOS 上 `/tmp` 只读）

> Draft: `DRAFT-DEVIO-CONSUMER-TEST-NO-TMPFILE-POPEN-CAPTURE`
> Stem: `devio-1.2-consumer-test-no-tmpfile-popen-capture` — 与同 stem 的 `.kv` 成对
> 实例：devio 1.2（PR !9180）、devmem2 0.2（PR !9172）

## 基本信息

- **ID**: DRAFT-DEVIO-CONSUMER-TEST-NO-TMPFILE-POPEN-CAPTURE
- **严重度**: 2
- **类别**: ci-gate, test-design, filesystem
- **触发工具**: ci（L1 测试执行验证）
- **阶段**: testing

## 错误特征

```
ogrep: /tmp/devio_test.out: No such file or directory
otest devio 1.2: FAIL (exit 2, expected 0 from grep)
oERROR: devio/1.2 (test package): Error in test() method, line 41
o	ConanException: Error 1 while executing
o[fail] devio/1.2 — conan create failed
```

而同一时刻被测二进制完全正常——同一个 PR 里其余"存在性 / 可执行位"判定全部 PASS。

## 可复现问题

两种常见写法都会踩：

```c
/* ❌ C 版：先把输出落盘再 grep */
snprintf(cmd, sizeof(cmd),
    "%s 2>&1 | head -20 > /tmp/devio_test.out; "
    "grep -q 'Usage\\|read\\|write' /tmp/devio_test.out", argv[1]);
int rc = system(cmd);
```

```c
/* ❌ 隐含前提：/tmp 可写 */
system("sh run_tests.sh > /tmp/out 2>&1");
```

在 OHOS 上 `/tmp` 是**只读文件系统**——实测消费级 HarmonyOS PC（HAD-W32）与 CI
runner 行为一致：

```
$ echo probe > /tmp/ohpcd_probe
sh: can't create /tmp/ohpcd_probe: Read-only file system
```

于是重定向静默失败 → `grep` 因文件不存在返回 2 → `test()` 抛 `ConanException` →
CI 的 L1 门禁 fail，但**问题不在被测程序**。

自检（一行）：

```bash
echo x > /tmp/probe || echo READONLY      # 打印 READONLY 即说明判据不可靠
```

## 根因分析

测试判据隐含假设了「文件系统 `/tmp` 可写」，而该假设**与验证目标（被测程序能否运行）
无关**。OHOS 把 `/tmp` 设为只读后，这个无关变量直接变成失败源。更隐蔽的是失败信息
（`grep: … No such file or directory`）**看起来像"程序没产出输出"**，会把排查方向
误导到"程序没跑起来 / 链接有问题"，浪费整轮 CI。

实测同一根因命中**两个包**：devio 1.2（`/tmp/devio_test.out`）与 devmem2 0.2
（`/tmp/devmem2_test.out`，报错字符串 `sh: can't create /tmp/devmem2_test.out: Read-only file system`）。

## 方案：内存管道直读（popen）

```c
static int safe_run(const char *path, char *out, size_t outlen, int *code, int *killed) {
    char cmd[1200];
    snprintf(cmd, sizeof(cmd), "\"%s\" < /dev/null 2>&1", path);
    FILE *fp = popen(cmd, "r");                 /* 内存管道，全程不落盘 */
    if (!fp) { *code = -1; *killed = 0; return -1; }
    /* ★ 必须循环读到 EOF 再 pclose：单次 fread 后立即 pclose，输出超过缓冲时
     * 子进程会因写端被关而收到 SIGPIPE（假通过）或阻塞在写端（死锁挂起）。 */
    size_t n = 0, got;
    while (n < outlen - 1 && (got = fread(out + n, 1, outlen - 1 - n, fp)) > 0) {
        n += got;
    }
    out[n] = '\0';
    int rc = pclose(fp);
    if (rc == -1) { *code = -1; *killed = 0; return -2; }
    *killed = !WIFEXITED(rc);
    *code = (*killed || rc == -1) ? -1 : WEXITSTATUS(rc);
    if (*killed) return -3;
    /* ★ popen 经 /bin/sh 中转：shell 把子进程的信号死亡转成 128+signum
     * （SIGSEGV→139、SIGABRT→134）后**正常退出**，WIFEXITED 恒为真。
     * 因此必须判 >=128，而不是只列 {126,127,255} —— 后者漏掉最常见的段错误。 */
    if (*code == 126 || *code == 127 || *code >= 128) return -4;
    return 0;
}
```

判定顺序固定三步：

1. **排除跑不起来**：`rc==-1` / `!WIFEXITED` / `code ∈ {126,127}` / `code >= 128` → FAIL，
   并把原始码写进断言详情（否则失败信息又会误导排查）；
2. **语义断言**：输出含**从源码抄出的**确定字面（devio 的 usage 关键字、
   daa2iso 的 `Usage: %s <input.DAA/GBI> <output.ISO>`），不要泛泛断言"输出不为空"；
3. **被测工具预期非 0 时**不断言 0。

> 判据实现请用显式 `expect(cond, ...)` 计数汇总，**不要用 `assert()`**：
> `NDEBUG`（Release 构建）下 `assert` 会被整体编译掉，断言静默消失、
> 测试变成永远通过的空壳。

若上游确实必须落盘（工具本身产出文件）：把目录取为 `$TMPDIR` 或
`self.build_folder` 下自建子目录，并**显式校验目录可写**；**绝不写死 `/tmp`**。

参考实现：
- `archives/d/devio/1.2/test_package/test_devio.c`（4 条断言）
- `archives/d/devmem2/0.2/test_package/test_devmem2.c`（5 条断言）
- `archives/c/crashme/2.8.5/test_package/test_crashme.c`（8 条断言，含 `safe_run()`）
- `archives/d/daa2iso/0.1.7e/test_package/test_daa2iso.c`（5 条断言 + 源码字面断言）

## 边界与查重

- **E325**（Conan test_package 在 OHOS 上应先解析可用 shell 再跑脚本）：E325 解决的是
  **"用哪个 shell 执行"**（`sh`/`bash` 缺失导致脚本压根跑不起）；本条解决的是
  **"判据要不要经过文件系统"**（即便 shell 正确，落盘到只读 `/tmp` 仍失败）。
  两者在同一个测试里可能同时出现，但**判据、失败信息、处置动作均不同**，**不合并**。
- **E223**（secure tmp 需联合验证 owner、mode、MAC 与真实写入闭环）：E223 讲的是
  **产品侧临时目录的安全属性校验**；本条是**测试判据的设计原则**（判据不应引入无关变量），
  对象与层次不同，**不合并**。
- 正式库以 `popen` 检索命中 E226（HarmonyOS `os.popen` 文本解码）与 E260（解释器启动器），
  两处语境均为"读取方式/安全语义"，**均非本条主题**。

## 关联

- 实例 PR：**!9180**（devio 1.2）、**!9172**（devmem2 0.2）
- 同批修复并复用该判据模板：**!9361**（crashme 2.8.5）、**!9360**（daa2iso 0.1.7e）
- 真机佐证：消费级 HarmonyOS PC（HAD-W32）实测 `/tmp` 只读，与 CI runner 一致
- 本 Issue 与 PR 双向关联；草稿经主编审核后由 promote 流程转入正式知识库。
