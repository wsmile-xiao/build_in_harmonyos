# 路径 B 知识库扩展申请：消费者测试必须显式排除 126/127/255 与信号终止，否则把"加载失败"误判为通过

## 申请信息

- **申请类型**：路径 B（知识库扩展，10 分候选）
- **关联任务**：#6894 crashme 2.8.5
- **关联 PR**：`!9361`（`feat/crashme-2.8.5`，配方 PR，CI build #43591 校验通过）
- **知识草稿**：`knowledge/drafts/crashme-2.8.5-consumer-test-exitcode-126-127-255-guard.kv` / `.md`
- **草稿 ID**：`DRAFT-CRASHME-CONSUMER-TEST-EXITCODE-126-127-255-GUARD`
- **问题首次提出方**：配方 PR `!9171`（detachtty 11.0.0）的 AI 代码检视（P2）
- **提交方式**：草稿与配方归档**同一原子 PR 分支**（`feat/crashme-2.8.5`）提交
- **申请日期**：2026-09-10

## 一、为什么这是"可跨仓库复用的知识"

CI 的 **L1 门禁 = "测试执行验证"**，它的全部价值来自 `test()` 中断言的有效性。
而"跑完即通过"这类弱判定会让 L1 **表面全绿、实际零验证**：CI 认为"二进制可执行 +
动态链接正确"，事实上连 `execve` 都没成功。这一陷阱在 OHOS 上尤其隐蔽，因为
"跑不起来"恰好表现为三个**看似正常**的退出码（126/127/255），而不是崩溃。
本条给出**一行自检法**（把被测路径换成 `/nonexistent`，若测试仍绿则判定无效）与
**可直接复制的判定模板**，适用于本仓库所有 `test_package`。

## 二、问题与自检

```c
/* ❌ 弱判定：非 0 即通过（detachtty 11.0.0 初版） */
rc = system(cmd);
if (WEXITSTATUS(rc) == 0) FAIL("expected non-zero"); else OK("exec'd");
```

OHOS 上"根本没跑起来"的三类码会被这条判定当成通过：

| 退出码 | 含义（实测） |
|---|---|
| **126** | 无执行权限 / exec 被拒（消费级 HarmonyOS PC 的 SELinux 域限制，实测 `/data/local/tmp` 下自定义二进制即返回 126） |
| **127** | 找不到解释器或文件（shebang 缺失、依赖缺失走 shell 兜底） |
| **255** | 动态加载器失败（`Error while loading …`） |

另有**被信号杀死**（`WIFEXITED` 为假，`WEXITSTATUS` 无意义）同样不能参与判定。

**一行自检**：把测试里的被测路径换成 `/nonexistent` ——

- 测试仍 PASS → 判定无效；
- 测试 FAIL 且详情打印 `rc=127` → 判定有效。

反向陷阱：被测工具**可能故意非 0 退出**（crashme 的崩溃注入、mlddc usage 路径 exit 10、
devio/devmem2/daa2iso 无参数时的 usage 分支），所以"断言退出码必须为 0"同样不可靠。

## 三、根因

测试断言把"进程结束了"等同于"进程成功加载并运行"。OHOS 的内核/加载器对
"exec 被拒 / 解释器缺失 / 动态库加载失败"分别返回 126/127/255，这些码**非 0 且非崩溃**，
恰好落进弱判定的"通过"分支。属**测试设计质量缺陷**，需在模板层统一加守卫。

## 四、可复用方案（已落地为模板）

```c
static int safe_run(const char *path, char *out, size_t outlen, int *code, int *killed) {
    char cmd[1200];
    snprintf(cmd, sizeof(cmd), "\"%s\" < /dev/null 2>&1", path);
    FILE *fp = popen(cmd, "r");                       /* 不落盘：OHOS 的 /tmp 只读 */
    if (!fp) { *code = -1; *killed = 0; return -1; }
    size_t n = fread(out, 1, outlen - 1, fp);
    out[n] = '\0';
    int rc = pclose(fp);
    if (rc == -1) { *code = -1; *killed = 0; return -2; }
    *killed = !WIFEXITED(rc);
    *code = *killed ? -1 : WEXITSTATUS(rc);
    if (*killed) return -3;
    if (*code == 126 || *code == 127 || *code == 255) return -4;
    return 0;
}
```

判定顺序：① 排除跑不起来（`rc==-1` / `!WIFEXITED` / `126|127|255`）→ FAIL 并打印原始码；
② 语义断言输出含**从源码抄出的**确定字面（如 daa2iso 的
`Usage: %s <input.DAA/GBI> <output.ISO>`）；③ 工具预期非 0 时不断言 0；工具**故意崩溃**时
不执行崩溃路径，只做静态校验 + 辅助工具安全调用（上游 makefile 的 `ptest1` 即 `./pddet`）。

**参考实现**（本 PR 及同批 PR 均按此模板）：
- `archives/c/crashme/2.8.5/test_package/test_crashme.c`
- `archives/d/devio/1.2/test_package/test_devio.c`
- `archives/d/devmem2/0.2/test_package/test_devmem2.c`
- `archives/d/daa2iso/0.1.7e/test_package/test_daa2iso.c`

## 五、验证证据

| 项 | 证据 |
|---|---|
| 问题提出 | PR !9171（detachtty）AI 检视：P2「非 0 即通过会把缺失/不可执行/加载失败（127/126/255）全部误判为 OK」 |
| 修复落地 | PR !9171 build **#43404 ✅**；模板复制到 !9361 / !9180 / !9172 / !9360，CI 全绿（#43591 / #43387 / #43399 / #43588） |
| 真机佐证 | 消费级 HarmonyOS PC（HAD-W32）实测自定义二进制 exec 被拒 = **rc 126**，正是弱判定会放行的码 |

## 六、查重声明

- **E400**（Node.js CLI on HarmonyOS）：error_signature 含 `exit 126`，但语境是**被测运行时
  自身的 exec 被拒**（产品缺陷面）；本条是**测试断言的判定缺陷面**（测试设计质量），
  对象、阶段、处置全不同，**不合并**。
- **E260**（fixed interpreter launcher must execute validated fd）：同现 `126|127`，讲启动器
  安全语义，与本条无关。
- **E325 / E223**（OHOS `/tmp` 只读、需先解析可用 shell）：本条**复用**其结论（popen 直读不落盘），
  新增的独立知识点是**退出码三态判定**。
- 正式库以 `255` 检索无相关条目；`126/127` 的既有命中均非"测试断言判定"语境。

## 七、请评审确认

1. 是否认可本条目为**路径 B（贡献创新，10 分候选）**评审对象？
2. 是否建议把该判定模板写入 `templates/test_package/`（C 版）与
   `docs/TEST_QUALITY_SPEC.md`，作为消费者测试的强制项？
3. 是否认可"被测工具故意非 0 / 故意崩溃时，断言改为『未落在 126-127-255 且未被信号
   杀死』+ 静态校验"这一处置？
