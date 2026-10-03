# DRAFT-7C3E：HarmonyOS 无应用 uid 的 passwd 条目 ⇒ 工具静默退化为空操作（metastore 1.1.2）

- **触发实例**：metastore 1.1.2 适配（2026-10-02，积分赛任务，Agent 7C3E）
- **错误签名**：`getpwuid failed for .*: uid [0-9]+ not found` / `getgrgid failed for .*: gid [0-9]+ not found`
- **类别**：ohos / libc / runtime / posix / testing
- **严重度**：1（工具在本平台上完全不工作，且本地不可见）

## 症状（CI build #66657 真机实测）

```
getpwuid failed for ./tree: uid 20001006 not found
...
consumer assertions: 29 run, 6 PASS, 23 FAIL, 0 SKIP
RESULT: FAILED
```

`--save` 存出空 metafile、`--compare` 无输出、`--dump` mode 列为 0 字节、`--apply` 不还原任何东西。

## 根因

HarmonyOS 的 `/etc/passwd`、`/etc/group` **不为应用 uid 建条目**（CI worker 上 uid/gid 20001006 均无条目），
`getpwuid(3)` / `getgrgid(3)` 合法返回 NULL。metastore 1.1.2 的 `mentry_create()`
（`src/metaentry.c:205-213`）把它当**致命错误**：

```c
pbuf = xgetpwuid(sbuf.st_uid);
if (!pbuf) {
    msg(MSG_ERROR, "getpwuid failed for %s: uid %i not found\n", ...);
    return NULL;          /* ← 整条 metaentry 作废 */
}
```

调用方 `mentries_recurse()` 只在 `!mentry` 时静默 `return` ⇒ **该子树整个被跳过**。
于是平台级**静默降级**：不崩溃、不报错退出，只是对每个文件都什么都不做。唯一症状是每路径一行 error 日志。

apply 路径还有对称问题：它用 `xgetpwnam(stored->owner)` / `xgetgrnam()` 反查，
即便存储端修好，写进去的名字在稀疏 DB 上也解析不回来。

## 为什么本地全绿

本地以 root 跑，uid 0 在 `/etc/passwd` 里有条目，`xgetpwuid()` 正常返回 —— **12/12 断言通过**。
**判定条件是「跑测试的用户在不在 passwd DB 里」，而不是代码对不对。**
同一个 commit：本地 `conan create` 12/12，真机 CI 6/23。

> 这是「设备与 CI 语义差异」里最难在本地自查的一类。
> 对比同源的 `DRAFT-10175-rmlint-getpwuid-null-no-passwd-db-segfault`：
> 那次是**解引用 NULL 直接 SIGSEGV**（症状明显、本地易复现），
> 这次是**上游主动 return NULL 导致静默空操作**（症状隐蔽、本地不可见）。同一平台事实，两种截然不同的暴露方式。

## 修复

补丁 `0002-numeric-uid-fallback-when-passwd-db-has-no-entry.patch`：

- 查不到名字时，把**十进制数字**当作 owner/group 名写进 metafile；
- apply 路径反过来接受这个十进制形式：整串都是数字就直接 `strtoul` 当 id，否则走名字查询；
- metafile 格式不变（owner/group 仍是 CSTRING，只是内容可能是数字），
  A 机存的 metafile 仍能在 B 机 apply；
- 判据是「数据库里有没有这个 id」，**与平台无关、无 `__OHOS__` 宏**（PF5/R8 干净），
  passwd DB 完整的主机行为**逐字节不变**。这与 `tar(1)` 的 `--numeric-owner` 是同一思路。

## 本地等价复现（不需要真机）

```bash
setpriv --reuid=20001006 --regid=20001006 --clear-groups <被测工具> --save --file m.bin ./tree
```

本机同样没有 20001006 这个 uid，所以这与真机条件等价。配套两个坑：

1. 工作目录必须在该 uid 可达的路径 —— `/root` 是 0700，uid 20001006 进不去；
   先把被测脚本与二进制复制到 `/var/tmp` 并 `chmod a+rX`。
2. 回归要**同时跑两个身份**：稀疏 DB 身份（证明修复生效）+ 有条目身份（如 root，证明无回归）。

实测：

| 补丁 | 身份 | 结果 |
|---|---|---|
| 仅 0001 | uid 20001006（无条目） | 6 PASS / **25 FAIL**，exit=1 —— 精确复现真机 |
| 0001 + 0002 | uid 20001006（无条目） | **12/12 PASS**，exit=0 |
| 0001 + 0002 | root（有条目） | 12/12 PASS，无回归 |

直接验证机制：metafile 内该文件的 owner/group 字段为 `20001006`，
而同目录下有 passwd 条目的目录仍记为 `root`；`--apply` 把 0777 复原为 0644。

## 适用边界

- 适用于任何在 OHOS 上调用 `getpwuid`/`getgrgid`/`getpwnam`/`getgrnam` 的包：
  用户名显示、属主/权限备份类工具、tar/快照类、quota 工具、"bad uid" 告警。
- 若无法改动上游，至少把「查不到名字」从致命降级为**可观测的警告并继续处理其余元数据维度**
  （mode/mtime/xattr 与属主无关），让工具在稀疏 DB 上仍能完成主要工作，
  并在文档与测试里显式声明属主维度在该平台不可用。
- **绝不**用 dummy 名字或硬编码 `nobody` 伪造属主 —— 那会让 compare/apply 静默写错属主。
- **绝不能**把测试 skip 掉：那是把真机红灯藏起来。空操作同样返回 0，
  所以元数据类工具**只断言退出码必然被骗过**，必须断言落盘产物。

## 关联

- 配方补丁：`archives/m/metastore/1.1.2/patches/0002-numeric-uid-fallback-when-passwd-db-has-no-entry.patch`
- 配方：`archives/m/metastore/1.1.2/conanfile.py`（R33：CC 从 Conan conf 读，不裸用 `${CC}`）
- 消费者测试：`archives/m/metastore/1.1.2/test_package/test_metastore.sh`（9 组 / 12 条断言）
- 适配账本：`archives/m/metastore/1.1.2/notes.md` §2b
- 兄弟知识：`DRAFT-10175-rmlint-getpwuid-null-no-passwd-db-segfault`（同一平台事实，崩溃型表现）
- 兄弟草稿：`DRAFT-7C3E-...-strmode-only-libbsd-import-and-sh-symbol-probe-lies`（本包另一处适配）
