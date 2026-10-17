# 消费者测试必须显式排除 126/127/255 与信号终止，否则把"加载失败"误判为通过

> Draft: `DRAFT-CRASHME-CONSUMER-TEST-EXITCODE-126-127-255-GUARD`
> Stem: `crashme-2.8.5-consumer-test-exitcode-126-127-255-guard` — 与同 stem 的 `.kv` 成对
> 实例：crashme 2.8.5（任务 #6894，配方 PR !9361）；首次由 AI 检视在 detachtty 11.0.0 上指出

## 基本信息

- **ID**: DRAFT-CRASHME-CONSUMER-TEST-EXITCODE-126-127-255-GUARD
- **严重度**: 2
- **类别**: ci-gate, test-quality, ohos-exec
- **触发工具**: ci（L1 测试执行验证）+ 人工/AI 检视
- **阶段**: testing

## 问题特征

消费者测试写成"跑完即通过"的弱判定：

```python
# ❌ detachtty 11.0.0 的初版 test：非 0 即通过
rc = system(cmd)
if (WEXITSTATUS(rc) == 0) { FAIL("expected non-zero"); }
else { OK("both binaries exec'd"); }
```

在 OHOS 上"程序根本没跑起来"的三种典型退出码会被这条判定**当成通过**：

| 退出码 | 含义（OHOS 实测） |
|---|---|
| **126** | 无执行权限 / exec 被拒（实测消费级 HarmonyOS PC 的 SELinux 域限制，`/data/local/tmp` 下自定义二进制即返回 126） |
| **127** | 找不到解释器或文件（shebang 缺失、动态依赖缺失走到 shell 兜底） |
| **255** | 动态加载器失败（`Error while loading …`） |

另有**被信号杀死**的情形：`WIFEXITED(rc)` 为假，此时 `WEXITSTATUS` 取值无意义，
同样不能参与判定。

反向陷阱同样存在：**被测工具本身可能故意非 0 退出**（crashme 的崩溃注入、mlddc 的
usage 错误路径 exit 10、devio/devmem2/daa2iso 无参数时的 usage 分支），所以"断言退出码
必须为 0"也不可靠。

## 一行自检法

把测试里的被测路径临时换成 `/nonexistent`（或一个无执行位的文件）：

- 测试**仍 PASS** → 判定无效，未排除 126/127/255；
- 测试 FAIL 且详情里打印出 `rc=127` / `rc=126` → 判定有效。

## 根因分析

CI 的 **L1 门禁 = "测试执行验证"**，其价值完全来自 `test()` 里断言的有效性。弱判定会让
L1 表面全绿而实际零验证：CI 认为"二进制可执行 + 动态链接正确"，事实上连
`execve` 都没成功。这是**测试质量缺陷**，不是平台缺陷——但它恰好会在 OHOS 上被
三类"跑不起来"的码掩盖，因此需要在测试模板层统一加守卫。

## 最终方案（可复用模板）

统一用 `popen` 直读（顺带避免落盘 `/tmp` —— OHOS 的 `/tmp` 只读，写中间文件会直接
制造失败）：

```c
static int safe_run(const char *path, char *out, size_t outlen, int *code, int *killed) {
    char cmd[1200];
    snprintf(cmd, sizeof(cmd), "\"%s\" < /dev/null 2>&1", path);
    FILE *fp = popen(cmd, "r");                       /* 不落盘 */
    if (!fp) { *code = -1; *killed = 0; return -1; }
    size_t n = fread(out, 1, outlen - 1, fp);
    out[n] = '\0';
    int rc = pclose(fp);
    if (rc == -1) { *code = -1; *killed = 0; return -2; }
    *killed = !WIFEXITED(rc);                          /* 被信号杀死 */
    *code = *killed ? -1 : WEXITSTATUS(rc);
    if (*killed) return -3;
    if (*code == 126 || *code == 127 || *code == 255) return -4;   /* 跑不起来 */
    return 0;
}
```

判定顺序固定为三步：

1. **排除跑不起来**：`rc == -1` / `!WIFEXITED` / `code ∈ {126,127,255}` → FAIL，并把原始码写进断言详情；
2. **语义断言**：输出含该工具**确定的**字符串——从**源码里抄出真实字面**
   （如 `daa2iso.c` 的 `"Usage: %s <input.DAA/GBI> <output.ISO>"`），不要泛泛断言"输出不为空"；
3. **工具预期非 0 时**：断言"未落在 126/127/255 且未被信号杀死"，而不是断言 `code == 0`；
   工具**故意崩溃**时（crashme），刻意不执行其崩溃路径，只做静态校验 + 辅助工具的安全调用
   （上游 makefile 的 `ptest1` 目标本身就是直接 `./pddet`）。

参考实现：
- `archives/c/crashme/2.8.5/test_package/test_crashme.c`（`safe_run()` + ELF 静态校验 8 条断言）
- `archives/d/devio/1.2/test_package/test_devio.c`（popen 直读 4 条断言）
- `archives/d/devmem2/0.2/test_package/test_devmem2.c`（同上 5 条断言）
- `archives/d/daa2iso/0.1.7e/test_package/test_daa2iso.c`（同上 + usage 字面断言）

## 边界与查重

- **E400**（Node.js CLI on HarmonyOS: JITless/WASM 能力边界）：其 error_signature 里出现
  `exit 126`，但语境是**被测运行时本身的 exec 被拒**（产品缺陷面）；本条是**测试断言的
  判定缺陷面**（测试设计质量），对象（被测程序 vs 测试代码）、阶段、处置全不同，**不合并**。
- **E260**（fixed interpreter launcher must execute validated fd）：也出现 `126|127`，
  但讲的是启动器安全语义，与本条无关。
- **E325 / E223**（OHOS 上 `/tmp` 只读、需先解析可用 shell）：本条**复用**其结论（popen
  直读不落盘），但新增的是**退出码三态判定**这一独立知识点，不属复用。
- 正式库以 `255` 检索无相关条目，`126/127` 的既有命中均非"测试断言判定"语境。

## 关联

- 首次由 AI 检视在 PR **!9171**（detachtty 11.0.0）指出（P2：非 0 即通过会把
  缺失/不可执行/加载失败误判为 OK）
- 修复并落地为模板：PR **!9361**（crashme 2.8.5）、**!9180**（devio 1.2）、
  **!9172**（devmem2 0.2）、**!9360**（daa2iso 0.1.7e）
- 本 Issue 与 PR 双向关联；草稿经主编审核后由 promote 流程转入正式知识库。
