# E665：HMDFS 文件系统语义缺口与 OHOS 无 passwd UID 的移植修法（草稿）

- **来源**：s-nail 14.9.25 适配（Berkeley mail 家族 MUA），上游测试套件
  607 用例从 15 FAIL 收敛到 5 FAIL 的三轮真机排障
- **日期**：2026-09-22
- **证据**：`archives/s/s-nail/14.9.25/notes.md`、
  `archives/s/s-nail/14.9.25/patches/000{1,2,3}-*.patch`、
  `archives/s/s-nail/14.9.25/reports/`

四条相互独立的设备事实，任何一条都能让"本地能跑的 C 程序"在
OHOS/HMDFS 上成簇失败。修法均为最小作用域补丁，已在 s-nail 三个补丁中落地。

## 1. umask×属主映射：0700 目录对创建进程自身不可访问

HMDFS 把新建目录的**属主映射为共享身份**（`ls` 显示 20001006），而进程
euid 是应用域号（20020085）。s-nail 默认内部变量 `*umask*=0077`，
`mkdir(0777)` 的目录落盘 `drwx--S---`(2700)：组位被剥掉后，进程对刚建的
"自己的"目录按 other 类判定 → 目录内一切创建/写操作 `EACCES`。

对照实验（同一父目录、同一调用方式）：

| 创建时 umask | 请求 mode | 落盘模式 | 目录内 mkdir/写 |
|---|---|---|---|
| 0077 | 0777 | `drwx--S---`(2700) | **EACCES** |
| 0022 | 0700 | `drwxr-s--x`(2751) | 正常 |

**修法**（`patches/0002-path-mkdir-umask.patch`）：mkdir 调用点作用域化
放宽 umask——保存旧值 → `umask(0022)` → mkdir → 恢复。目录内文件的创建
仍受进程原 umask 约束，不放大文件可见性，不属于削弱文件权限语义。

## 2. 硬链接缺失：link(2) 恒失败

Maildir 投递（`tmp/→new/`）与状态迁移（`new/→cur/`）的经典实现是
`link()+unlink()`；HMDFS 上 `link()` 恒失败（`cp -al` 同样命中且会**静默
退化为整树复制**）。由于源/目标必在同一 Maildir 内，`rename(2)` 提供等价
的原子语义。**修法**（`patches/0003-maildir-link-rename-fallback.patch`）：
两处 link 失败时回退 rename。上游测试的对应症状是断言成簇失败
（实测 maildir 组 10 项 FAIL）。

## 3. 属主独占权限位丢失：owner-only 检查必拒

`chmod 0600` 实际落盘 `0660`（组位无法移除）。任何"文件必须 owner-only
否则拒绝使用"的安全检查在 HMDFS 上恒触发：s-nail 拒绝加载 `.netrc`
（`Not a regular file, or accessible by non-user`，实测 netrc 组 2 项 FAIL）。
**处置**：不改弱上游安全检查，按环境限制如实申报。

## 4. 应用域 UID 无 passwd 条目：getpwuid 为 NULL 即 panic

`getuid()`=20020085 而 `/etc/passwd` 无对应行，`getpwuid()` 返回 NULL。
s-nail 的处理是 `n_panic("Cannot associate a name with uid …")`——启动即
SIGABRT，上游测试套件 372 项成簇失败（多数断言根本没跑完）。
**修法**（`patches/0001-main-uid-fallback.patch`）：getpwuid 失败时从
`$LOGNAME`→`$USER`→`"unknown"` 与 `$HOME`→`"/"` 合成 passwd 身份继续。

## 排障方法（可直接复用）

- 目录类问题先做**落盘模式对照**：`ls -ld` 看实际落盘位，再查创建点的
  umask；不要按"磁盘权限配置错误"排查。
- 链接类问题先跑 `link()` 探针；`cp -al` 的"成功"是假象（整树复制）。
- 上游测试成簇失败时先看**首个错误行**（一次 panic 会级联出几百个假差异：
  s-nail 首轮 372 tests/349 FAIL → 修复后 607 tests，测试根本没跑完的
  用例不会计入计数）。

## 验证

```sh
# 探针（在设备可写目录下执行，完整命令与输出见 patches 同级 notes.md）
# 1) umask 效应：umask 0077 后 mkdir(0777) → ls -ld 显示 2700
# 2) 硬链接：link(a,b) 恒 -1
# 3) 权限位：chmod 0600 后 stat 显示 660
# 4) passwd：getpwuid(getuid()) 返回 NULL
```
