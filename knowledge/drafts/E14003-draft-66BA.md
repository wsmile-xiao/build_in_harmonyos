# E14003 — OHOS 没有 `/var`：FHS 硬编码的锁文件路径导致启动即失败

## 错误特征

```
LinPac version 0.28 (...) by KI6ZHD

Cannot create the lockfile /var/lock/LinPac.20020101 : No such file or directory
（exit 1，程序根本没起来）
```

## 触发条件

- 阶段: 运行期（编译、安装、conan create 全部正常）
- 程序在启动时于 `/var/...` 下创建锁文件 / pid 文件 / unix socket

## 根因分析

OpenHarmony 根文件系统**没有 `/var` 目录**：

```bash
$ ls -d /var          → No such file or directory
$ ls -d /var/lock     → No such file or directory
$ touch /var/lock/x   → No such file or directory
$ ls -ld /tmp         → drwxr-xr-x root root（存在但不可写）
```

沿用 FHS 固定路径的老程序（终端类、守护进程、系统服务）在启动阶段 `open(O_CREAT)`
失败即 `exit(1)`。这类问题**编译期完全看不出来**，只有把产物真正跑起来才会暴露，
所以 test_package 必须执行真实二进制（R34）。

## 解决方案

### 推荐方案：候选目录列表 + 首个可写者

```c
static void lock_file_name(char *buf, size_t len)
{
  const char *dirs[] = { getenv("LINPAC_LOCKDIR"), "/var/lock",
                         getenv("XDG_RUNTIME_DIR"), getenv("TMPDIR") };
  const char *dir = NULL;

  for (unsigned i = 0; i < sizeof(dirs)/sizeof(dirs[0]) && dir == NULL; i++)
    if (dirs[i] != NULL && dirs[i][0] != '\0' && access(dirs[i], W_OK) == 0
        && snprintf(buf, len, "%s/LinPac.%i", dirs[i], (int)getuid()) < (int)len)
      dir = dirs[i];

  if (dir == NULL) /* nothing usable - keep the historical path */
    snprintf(buf, len, "/var/lock/LinPac.%i", (int)getuid());
}
```

两个实施要点（都是实测踩出来的）：

1. **必须校验完整路径长度**：`snprintf` 返回 `>= len` 即发生截断，要跳过该候选。
   实测上游的全局缓冲是 `char keyfile[64]`，遇到较长的 `$TMPDIR` 会把
   `<dir>/LinPac.<uid>` 截断成 **`LinPa`**——锁文件“创建成功”但名字错误，
   单实例保护静默失效，比报错更难查。
2. **同步扩大调用方缓冲**（本例 `char keyfile[64]` → `256`），否则长路径候选会被
   长度校验拒绝，最终回落到不可写的 `/var/lock`。

### 回退方案

启动脚本/包运行环境里把 `$TMPDIR`、`$XDG_RUNTIME_DIR` 指到可写目录。对把路径写死的
老程序仍须改代码，故只作补充手段。

### 禁止做法

- ❌ 打包/安装期 `mkdir -p /var/lock`：根文件系统只读或无权限，伪造系统目录也不属于
  库适配范围。

## 验证

```bash
ls -d /var; ls -d /var/lock                       # 均应报 No such file or directory
HOME=$WORK/home TMPDIR=$WORK/tmp <bin> </dev/null # 锁文件应落在 $WORK/tmp/LinPac.<uid>
LINPAC_LOCKDIR=$WORK/d <bin> </dev/null           # 显式覆盖应生效
```

linpac 0.28 的 `test_package/test.sh` 把上述两条断言固化成了鸿蒙特有回归用例。

## 关联条目

- 相关: 无（`/var` 缺失属 OpenHarmony 文件系统布局层面，与 `__MUSL__`/uapi 头裁剪类问题不同）
