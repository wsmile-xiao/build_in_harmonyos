# E543 — RLIMIT_AS 单位混用（MB 当字节）导致子进程 execvp 恒失败 ENOMEM

## 错误特征
资源限制类工具在启用 CPU 时间限制（如 runlim `-t`）后，每次运行都报告：
```
[runlim] status:		execvp failed
[runlim] result:		1
```
即子进程刚 fork 出来就无法 exec；而墙钟限制（`-r`）与默认路径正常。
最小复现：`setrlimit(RLIMIT_AS, 31914)` 后 `execv("/bin/echo")` → `errno=12 Out of memory`。

## 触发条件
- 构建系统: 任意（问题在运行时；源码中 `setrlimit(RLIMIT_AS, ...)` 的调用方）
- 阶段: runtime（子进程 exec 阶段）
- 平台: Linux/OHOS 通用（与平台无关）

## 根因分析
`setrlimit(RLIMIT_AS)` 的内核单位是**字节**，而代码中的 `space_limit` 以 **MB** 计量
（usage 文本、采样比较 `mb > space_limit`、默认值 `get_physical_mb()` 均为 MB）。
MB 数值被原样传入 → 地址空间上限被压到 ~31 KB → `execvp` 装载解释器/动态库时
`ENOMEM` 失败。仅当代码路径进入 `setrlimit(RLIMIT_AS)` 时触发（runlim 中为
`time_limit < real_time_limit`，即 `-t` 或 `-t -s` 组合），因此表现为「只有 -t 失败」。

## 解决方案

### 推荐方案
将 MB 值换算为字节并强转 64 位防溢出：
```c
l.rlim_cur = l.rlim_max = ((rlim_t) space_limit << 20);
```
（runlim 1.10 实例：补丁 `0001-runlim.c.patch`，设备实测 rc=1 → rc=2 "out of time"）

### 禁止做法
- ❌ 不要删除/跳过 `setrlimit(RLIMIT_AS)` 调用（丢失限制语义，治标不治本）
- ❌ 不要用 `space_limit` 直接比较字节数（采样比较单位是 MB，需保持语义一致）

## 验证
```bash
setrlimit(RLIMIT_AS, 31914) 后 execv("/bin/echo") → errno=12 ENOMEM（复现）
setrlimit(RLIMIT_AS, ((rlim_t) 31914 << 20)) 后 execv("/bin/echo") → 成功（修复）
runlim -t 1 sh -c 'i=0; while [ $i -lt 100000000 ]; do i=$((i+1)); done' → rc=2 "out of time"（修复后）
```

## 关联条目
- 相关: 无（新错误模式）
