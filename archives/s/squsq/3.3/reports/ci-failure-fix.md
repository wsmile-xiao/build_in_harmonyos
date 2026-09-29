# 远端 CI 失败定位与修复 — squsq 3.3（PR #12396）

> **原始日志说明（review-memory 规则 19）**：`*.log` 属仓库审查规则 19 定义的 **PR 禁止文件**，故本目录下的 `.log` 原件**不随 PR 提交**（保留在工作区本地）；本报告引用的日志名指本地原件，其**关键原始输出已内联于本报告**，结论可被独立复核。

- 触发：PR #12396 的 PR 校验流水线
- 失败构建：**#59456**（worker CI-017）、**#59543**（worker CI-013），均为 `conan-build-test ❌`，`elapsedTime≈257s`，最终 `program finished with exit code 1`
- CI 侧自动分类：`环境问题 / 构建超时 — 可能是交互式测试卡住`（**分类方向正确，但"超时预算"不成立**：257s 远小于构建预算，实为用例内 `subprocess` 超时）
- 本地（真机 W3 / `conan create`）在此之前**全绿**，故属"仅远端复现"的环境差异问题

## 1. 首个真实错误（CI 原始输出）

```
osqusq/3.3: RUN: "/data/service/hnp/bin/clang" -O2 -Wall -Wno-error=return-type -Wno-error=int-conversion -o ".../build-release/sq" "sq.c" "tr1.c" "tr2.c" "sqio.c"
osqusq/3.3: RUN: "/data/service/hnp/bin/clang" ... -o ".../build-release/usq" "usq.c" "utr.c"
o======== Testing the package: Executing test ========
osqusq/3.3 (test package): RUN: "python3" ".../test_package/test_squsq.py" ".../p/bin" --log ".../squsq-cases.log"
o
o[ERROR] (upstream) sq_prints_version_banner: TimeoutExpired: Command '[.../p/bin/sq']' timed out after 120 seconds
o[ERROR] (upstream) usq_prints_version_banner: TimeoutExpired: Command '[.../p/bin/usq']' timed out after 120 seconds
o[PASS] (upstream) sq_squeezes_file_to_SQ_extension
o...（其余 24 例全 PASS）
oTOTAL 27  PASSED 25  FAILED 2  SKIPPED 0
oERROR: squsq/3.3 (test package): Error in test() method, line 32
o	ConanException: Error 1 while executing
o... hprogram finished with exit code 1
```

（完整 CI 日志：<https://ohpcd.atomgit.com/ci?id=59543>；构建流水线里同时出现的 `[fail] [Errno 2] No such file or directory: 'curl'` 属 CI worker 未安装 curl 导致的"预下载跳过"告警，已 `[WARN] ... will rely on conan's download`，不影响构建。）

## 2. 根因

`sq` / `usq` 的 `main()` 在**无命令行参数**时进入交互式提示循环：

```c
/* sq.c:102-120 */
if(argc < 2) {
    printf("Enter file names, one line at a time, or type <RETURN> to quit.");
    do { printf("\n*");
         for(i = 0; i < 16; ++i) {
             if((c = getchar()) == EOF) c = '\n';   /* fake empty (exit) command */
             ...
         }
    } while(inparg[0] != '\0');
}
```

用例运行器此前调用 `subprocess.run(..., capture_output=True)` 但**没有指定 `stdin`** → 子进程继承父进程的 stdin：

| 环境 | 父进程 stdin | 行为 |
|---|---|---|
| 本机 / W3 | 立即 EOF | `getchar()` 返回 EOF → `c='\n'` → 干净退出，用例 PASS |
| CI worker（buildbot 管道） | **永不 EOF** | `getchar()` 永久阻塞 → 用例 120s 超时后抛 `TimeoutExpired` |

**复现（本机，故意构造永不 EOF 的 stdin）**：

```python
r, w = os.pipe()                     # 读端给子进程，写端保持打开
p = subprocess.Popen([bin+name], stdin=r, stdout=PIPE)
time.sleep(5); assert p.poll() is None     # 5s 后仍在运行 → 挂死复现
os.close(w)                                # 关闭写端 → EOF
p.communicate(timeout=5)                   # 立即 rc=0 退出
```

实测：`sq: 5s 后仍运行=True`、`usq: 5s 后仍运行=True`（复现成功）；关闭写端后两者 `rc=0` 且输出含 `Enter file names`。

## 3. 修复（只改 test_package，不改被测程序、不改配方构建逻辑）

`test_package/test_squsq.py` 的 `Context.run()` 统一补 `stdin=subprocess.DEVNULL`：

```python
kwargs.setdefault("stdin", subprocess.DEVNULL)
```

`DEVNULL` 读取即 EOF，等价于用户在提示符下直接按 `<RETURN>` —— 正是上游文档规定的非交互退出路径；同时把这一行为写入断言（2 例 banner 用例新增"必须打印交互提示"与"遇 EOF 立即 rc=0 退出"），避免回归。

## 4. 重新验证

| 验证 | 结果 |
|---|---|
| 永不 EOF 的 stdin 下跑完整用例集（模拟 CI worker） | `TOTAL 27  PASSED 27  FAILED 0  SKIPPED 0`，**耗时 0.9s**（修复前必挂） |
| `conan create`（干净构建 + 12 秒内 test_package） | `TOTAL 27  PASSED 27  FAILED 0 SKIPPED 0` |
| `ohc-run.py finish squsq 3.3 built` → W3 本地 CI 模拟 | ✅ 通过（`.ci-result.json` `exit_code=0`，`integrity_hash` 与 `log_sha256` 均复算一致） |
| `ohc-run.py conan-verify squsq 3.3` | G0–G4 + L2/L4/L5 全 PASS |

## 5. 修复后的动作

`git push origin feat/squsq-3.3`（新增修复提交，未改写历史）→ 在 PR 内评论 `/rebuild` 重新触发 PR 校验流水线。
