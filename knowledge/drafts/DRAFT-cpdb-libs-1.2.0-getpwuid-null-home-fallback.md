# DRAFT-cpdb-libs-1.2.0-getpwuid-null-home-fallback — get_absolute_path 对 getpwuid() NULL 未判空解引用导致 Signal 11

- 触发事件：cpdb-libs 1.2.0 适配，conan create 消费端测试 Signal 11 崩溃
- 路径：Path B（知识库扩展）
- 编号：DRAFT-cpdb-libs-1.2.0-getpwuid-null-home-fallback

## 现象

`conan create` 走到 test_package 阶段时，消费者测试进程直接崩：

```
cpdb-libs/1.2.0 (test package): RUN: ./test_cpdb_libs_ohos
Signal 11 (core dumped)
ConanException: Error 139 while executing
```

测试代码尚未涉及 D-Bus/打印后端，只做了 ABI/boolean/string/Settings/
前端对象创建等简单断言；gdb 不可用（ptrace 被拒）。

## 根因

`get_new_FrontendObj()` 内部调用 `read_settings_from_disk()` →
`get_absolute_path("~/.CPD-print-settings")`。`get_absolute_path()` 对
`~` 前缀分支：

```c
struct passwd *passwdEnt = getpwuid(getuid());
char *home = passwdEnt->pw_dir;   /* 未判空 */
```

在 OHOS 沙箱（HMDFS UID 映射、/etc/passwd 无对应条目）中 `getpwuid()`
返回 NULL（最小复现：`uid=20020083 pw=0`），解引用 `NULL->pw_dir` 即
Signal 11。

## 修复

```c
struct passwd *passwdEnt = getpwuid(getuid());
char *home = passwdEnt ? passwdEnt->pw_dir : NULL;
if (home == NULL)
    home = getenv("HOME");
if (home == NULL)
    return NULL;
```

`getenv("HOME")` 在 OHOS 沙箱可用且与 pw_dir 语义等价；仍无 HOME 时按
原契约返回 NULL。

## 验证

- `conan create`（`-pr:h`/`-pr:b=ohos-aarch64`）全流程通过；
- 消费者测试 `test_cpdb_libs_ohos` 12/12 PASS（`No previous settings
  found.` 后正常打印 PASS，即 `~/.CPD-print-settings` 读取路径已安全）；
- W3 `build_and_test.sh` RC=0。

日志：`archives/c/cpdb-libs/1.2.0/reports/conan-create.log`。

## 适用边界

- 适用：任何在 OHOS/无 passwd 条目环境运行、路径/身份逻辑直接使用
  `getpwuid`/`getpwnam` 且未判空的三方库；
- 快速诊断：目标环境 `getpwuid(getuid()) == NULL` 即命中；
- 反例/注意：只判空不 fallback 会导致功能缺失（设置读写失败），应优先
  fallback `$HOME`；
- 关联同域草稿：DRAFT-empty-login-identity（rcs 的 getlogin_r 空成功）——
  同根因（OHOS 无 passwd 条目）不同错误面（空身份串 vs NULL 崩溃）。

## 关联

- 相似：E081（musl 缺失 secure_getenv 时的路径语义）；本条目为
  getpwuid NULL 解引用崩溃 + $HOME fallback 的具体可复现模式。