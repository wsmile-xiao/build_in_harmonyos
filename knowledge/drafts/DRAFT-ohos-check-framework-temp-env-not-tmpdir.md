# DRAFT-ohos-check-framework-temp-env-not-tmpdir：只读 /tmp 下 check 框架 runner 启动即中止——check 0.15.2 优先读 TEMP 而非 TMPDIR

> Contributor: xiao921924 | Status: Draft | Updated: 2026-09-03
> Source: burp 3.3.0 HarmonyOS PC 适配（check 0.15.2 在 OHOS 只读 /tmp 下启动即中止）

## 现象

OHOS 宿主 `/tmp` 是只读 erofs 挂载。check 框架（checkmark 0.15.2）的
上游测试程序在 OHOS 上启动即中止：

```
Unable to create temp file
```

按通用"只读 /tmp"经验（E002/E363）`export TMPDIR=<可写目录>` **无效**
——runner 依然中止，233 个用例 0 执行。

## 与现有知识的关系

- E002/E363 是通用 /tmp 只读 + **TMPDIR** 方案，适用于读 TMPDIR 的
  程序（多数 POSIX 工具）。
- check 框架是例外：其 `open_tmp_file()` 解析顺序为
  `$TEMP` → `P_tmpdir`（编译期 `/tmp`），**不读 TMPDIR**。
  现有索引无 check 框架特例条目。

## 方案

1. 先 grep 目标版本 check 源码确认临时目录解析顺序（不同版本可能
   不同，勿照搬）：
   `grep -n 'TEMP\|TMPDIR\|P_tmpdir' <check-src>/check_tmp.h`
   check 0.15.2 中 `TEMP` 在 `P_tmpdir` 之前被检查，`TMPDIR` 不在
   解析链里。
2. 运行 check 测试前 `export TEMP=<可写目录>`；可写目录建议用包构建
   目录内子目录（如 `$PWD/.tmp`），避免依赖 HOME。
3. **保留 TMPDIR 注入**：同一测试进程树里可能有其他读 TMPDIR 的
   子进程（shells、子命令），两个变量同时 export 才能全覆盖。
4. 验证：runner 完整执行（用例数 >0），临时文件确认落在 TEMP 目录
   而非 /tmp。

## 验证证据

- burp 3.3.0：`TEMP=$PWD/.tmp ./runner` 后 233 个用例完整执行
  （226 通过 / 7 环境性失败）；仅 `TMPDIR` 时 runner 启动即中止
  （0 执行）。修复后 7 个失败全部可取证归因（非 temp 问题）。
- 适用软件：所有用 check 框架做上游测试且运行环境 /tmp 只读的库
  （OHOS 宿主常态）。
