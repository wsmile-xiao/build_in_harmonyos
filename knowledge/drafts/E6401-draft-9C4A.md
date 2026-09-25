# E6401 — OpenBSD calendar 依赖外部 cpp 展开 #include，无预处理器环境（OHOS）打不开任何日历文件

## 错误特征
```
calendar: /usr/bin/cpp: No such file or directory
```
（或：`calendar -f <file>` 无任何输出、退出码 0，因为 opencal() 返回 NULL 后 cal() 静默返回）

## 触发条件
- 构建系统: 手写 Makefile（outils 0.14）
- 阶段: runtime（calendar 运行期）
- 平台: HarmonyOS PC（musl，无 /usr/bin/cpp）

## 根因分析
OpenBSD calendar 的 `opencal()`（io.c）在 vfork 子进程中
`execl(_PATH_CPP, "cpp", "-traditional", "-undef", "-U__GNUC__", "-P", "-I.", "-w", _PATH_INCLUDE, NULL)`，
把日历文件的 `#include <calendar.xxx>` 展开工作委托给外部 C 预处理器。
HarmonyOS 不提供任何 `cpp`（既无 /usr/bin/cpp，也不在 PATH 中），
exec 失败 → 子进程 `_exit(1)` → 父进程读到空管道 → calendar 不输出任何事件。

## 解决方案

### 推荐方案
当 `/usr/bin/cpp` 不存在（stat 失败）时，使用**内置 #include 展开**：
- 新增 `preprocess.c`：递归展开 `#include <name>` / `#include "name"`，
  搜索路径为 `.` 加 `_PATH_INCLUDE`（"-I/usr/share/calendar" 解析后的目录），
  递归深度上限 32，缺失 include 仅 `warnx` 告警不中断；
- `opencal()` 中 pipe+fork：子进程把展开结果流式写入管道，父进程 `fdopen` 读端；
- `cal()` 的输入从 `stdin` 改为全局 `calin` 流（cpp 路径下 calin=stdin，行为不变）。

### 禁止做法
- ❌ 依赖 open_memstream/fmemopen 在 OHOS 上做内存流（实测 open_memstream 不累积输出、
  fmemopen 读取 SIGILL；见 E302）
- ❌ 用 tmpfile() 做中转（OHOS /tmp 只读，errno=EACCES(13)；见 E002/E272）
- ❌ 简单把 `_PATH_CPP` 改成 "cpp" + execvp（设备仍无 cpp，等于没修）

## 验证
```bash
# 无 cpp 环境（OHOS 设备）
printf '#include <calinc>\n' > main; printf '01/01\tIncluded Event\n' > calinc
calendar -f main -t 20260101        # 应输出 Included Event
# 缺失 include 不中断
printf '#include <nosuch>\n09/21\tStill Here\n' > miss
calendar -f miss                    # 告警 + 输出 Still Here
```

## 关联条目
- 相关: E002（/tmp 只读）、E272（tmpfile EACCES）、E302（open_memstream 空输出）
