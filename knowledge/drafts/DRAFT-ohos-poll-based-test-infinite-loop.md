# DRAFT — 受限平台上「轮询直到出现」型测试会**挂死**而非失败：上游超时判定写在循环体内导致真无限循环

> 触发事件：psutil 7.2.2 HarmonyOS PC 适配（PR #11263，2026-09-19 真机实测）
> 这是本次适配**最昂贵的一个坑**：一个用例把整套测试从「33 秒」拖成「外推 7 小时」，
> 并让我误判为"套件天生慢"，据此做出错误的架构决策（改用并行）。

## 现象

上游套件跑到 `tests/test_linux.py::TestProcess::test_open_files_mode` 时**永不结束**：

- 串行：进程 `elapsed` 持续增长而 **CPU 时间几乎不涨**（实测主进程 `cpu_ticks` 在两个
  15 秒采样窗口间差值为 **0**）——典型的"忙等但无进展"，不是计算慢。
- 并行（xdist）：表现为**某一个 worker 卡住**，其余 worker 因分不到活而空转，最终整体超时。

```text
# 串行 40 分钟仅完成 65/704 项（其余时间卡在该用例）
# 实测主进程 CPU 时间：38 分钟 elapsed 而 cpu_ticks 增量≈0
```

## 根因（实测定位）

上游该用例的源码（`tests/test_linux.py:1863`）把**超时判定写在了循环体内**：

```python
def get_test_file(fname):
    p = psutil.Process()
    giveup_at = time.time() + GLOBAL_TIMEOUT      # GLOBAL_TIMEOUT = 5
    while True:
        for file in p.open_files():               # ← OHOS 上该集合**恒为空**
            if file.path == os.path.abspath(fname):
                return file
            elif time.time() > giveup_at:         # ← 超时判定在 for 内部
                break
    raise RuntimeError("timeout looking for test file")
```

外层 `while True` 里**只有** `for` 语句。当 `p.open_files()` 恒返回空列表时：

1. `for` 循环体一次都不执行 → 其中那条 `elif time.time() > giveup_at: break` **永不求值**；
2. 外层 `while True` 没有任何其它退出条件 → **真正的无限循环**；
3. 末尾的 `raise RuntimeError("timeout...")` 也永远到不了。

**上游自身的逻辑缺陷**（超时保护写在循环体内而非外层条件），在 Linux 上因
`open_files()` 正常返回而被掩盖；一旦某平台让该集合恒为空，缺陷立即暴露为挂死。

**为什么 OHOS 上恒为空**（实测）：OHOS 无 `/proc/self/fdinfo` ——
`Process.open_files()` 依赖它读取每个 fd 的打开模式，文件不存在时实现返回空列表：

```text
$ ls /proc/self/fdinfo
FileNotFoundError: [Errno 2] No such file or directory: '/proc/self/fdinfo'
$ python3 -c "import psutil,os; p=psutil.Process();
              print('num_fds=',p.num_fds(),'open_files=',len(p.open_files()))"
num_fds= 13 open_files= 0        # ← fd 数正常、打开文件集合却为空
```

## 适用面（判断方法）

任何**上游测试/工具**同时具备以下两个特征时，在受限平台上会挂死而非失败：

1. 使用「**轮询直到某条件成立**」结构（`call_until` / `waits_for` / `while True` +
   `for` + `if ...: break` / 轮询重试循环）；
2. 其**退出条件/超时保护写在循环体内部**，而非外层循环条件里。

一旦**被轮询的数据源在该平台上恒为空或恒不满足**，该循环就没有退出路径。

**特征识别命令**（跑套件时判断是"慢"还是"挂死"）——**不要靠 elapsed 判断**：

```sh
# elapsed 大 + CPU 时间不涨 = 挂死；CPU 时间持续增长 = 真在计算
for i in 1 2 3; do
  awk '{print "cpu_ticks=" $14+$15}' /proc/$(pgrep -f "[p]ytest" | head -1)/stat
  sleep 15
done
```

> 教训：本次我此前用「40 分钟完成 65 项」**线性外推**出"约 7 小时"，并据此改用
> 并行 —— **外推结论完全错误**。真实原因是个体用例挂死，修掉后全套只需 **59 秒**。
> 受限平台上**禁止用完成速率外推总耗时**，必须先按上面的 CPU 时间法区分"慢/挂死"。

## 推荐方案

1. **先隔离**：按上面的 CPU 时间法确认是否为挂死；再用逐个用例/逐文件的方式
   二分定位到具体用例（`--deselect` / `--ignore` 缩小范围）。
2. **命令行精确排除**该用例（而非列入"允许失败清单"——挂死的用例**根本不会产生
   失败记录**，列入清单毫无作用，且会让整个 run 超时）：

   ```text
   --deselect "tests/test_linux.py::TestProcess::test_open_files_mode"
   ```

3. **如实归因**：在 manifest / notes / PR 描述中写明"该用例在 OHOS 上因 <数据源>
   恒空触发上游超时判定位置缺陷导致无限循环，故排除"，并给出上游 file:line。
4. 若该用例覆盖的功能重要，**另写自身进程的等价消费者测试**（`test_package`）
   来补足覆盖，而不是把它 skip 掉后不闻不问。

## 禁止做法

- ❌ **不要**为挂死用例打上游补丁改逻辑（偏离上游、增加维护面；用 `--deselect`
  能达成同样效果且补丁面为零）。
- ❌ **不要**把它列入 `ALLOWED_TEST_FAILURES`：挂死用例不产生失败记录，列了也没用，
  反而掩盖"整套 run 超时"的真实原因。
- ❌ **不要**靠 `elapsed` 判断进度并线性外推（本次实测教训，见上）。
- ❌ **不要**因为"看着慢"就改成并行：挂死在并行下只表现为某 worker 卡住，更难定位，
  且 xdist 会连带吞掉失败清单（见 DRAFT-xdist-internalerror-swallows-summary）。

## 验证证据

- **主证据**：psutil 7.2.2（PR #11263）真机实测
  - 未排除时：串行 40 分钟仅完成 65/704 项，主进程 CPU 时间增量≈0
  - 排除该用例后：`collected 700 items` → **158 failed, 280 passed, 279 skipped,
    1 deselected, 1 error in 59.55s**（全套 59 秒）
- **根因证据**：上游 `tests/test_linux.py:1863-1873` 源码（超时判定在 for 循环体内
  + `while True` 无其它退出条件）；OHOS `open_files()` 恒空（`num_fds()=13` 而同刻
  `open_files()=0`）；`/proc/self/fdinfo` 不存在。
- **环境**：HarmonyOS PC / aarch64 / clang 15.0.4 / CPython 3.12。

## 查重结论

- 对 `无限循环` 检索：命中 **E069**（aclocal `--force` 触发 autotools 循环依赖）与
  **E079**（反复重试创建硬链接的循环报错）——两者均为**构建期工具行为**，与
  "测试轮询因数据源恒空而挂死"无关，未覆盖本条。
- 对 `infinite loop`（英文）检索：0 命中。
- 对 `open_files` / `fdinfo` 检索：命中 `E429-draft-76B1`（lsof 的 fdinfo `flags:`
  **方向位**缺失，pipe/pty 端点配对测试恒 FAIL）——那是"fdinfo **存在**但字段值
  语义不同"，本条是"数据源**恒空**导致轮询不退出"，根因与后果均不同。
- 盲区声明：以上基于本地已合并知识（本地 main + 本分支），无法保证外部无人提交过
  同主题草稿。
