# DRAFT — netcdf-c 4.9.3 ddispatch 硬编码 /tmp 在 OHOS erofs 只读下 DAP cookie jar 失败

## 基本信息
- **ID**: DRAFT-netcdf-c-4.9.3-ddispatch-tmpdir-env
- **类别**: platform | filesystem | tmpdir | erofs | DAP
- **来源任务**: netcdf-c-4.9.3-r01-pc1-22（知识库扩展）
- **状态**: DRAFT — 待主编审核提升为正式 E 条目

## 错误特征
```
Assertion failed: ocpanic(("state->auth->curlflags.cookiejar != NULL")) (ocinternal.c: oc_set_curlproperties: 585)
Signal 6 (core dumped)
FAIL t_dap3a / test_cvt3 / test_vara / tst_ncdap3.sh
```

## 根因分析
libdispatch/ddispatch.c 在非 Windows 分支把 `tempdir` 硬编码为 `/tmp`，
且不读取 TMPDIR/TMP 环境变量（`#else tempdir = "/tmp";`）。OHOS 上 `/tmp` 是
erofs 只读挂载（`/dev/block/dm-0 on /tmp type erofs (ro)`），DAP client
（oc2/ocinternal.c:585）为 cookie jar 创建临时文件失败 → `curlflags.cookiejar`
保持 NULL → OCASSERT，4 个 DAP3 测试全部 Signal 6。
设备上可写候选挂载点穷举：HMDFS（chmod 700 不保留、实测 drwxrws--x 2771）、
/dev/shm（不可写）、/data/local/tmp（权限拒绝），因此纯"设置 TMPDIR 环境变量"
（E002 方案）对**库内部硬编码 /tmp 且不读环境变量**的代码无效。

## 推荐方案
**方法**: patch-source-tmpdir-env-read

**说明**: 在库源码中让非 Windows 分支先读取 TMPDIR/TMP 再回退 /tmp，即
`tempdir = getenv("TMPDIR") || getenv("TMP") || "/tmp"`；同时运行环境 export
TMPDIR=<可写目录>。纯可移植性修复，不改测试逻辑。

**验证/命令**:
```
mount | grep ' /tmp '                    # erofs (ro) 实证
export TMPDIR=<任务可写目录>
make -C ncdap_test check -j1             # 修复前 4 FAIL(Signal 6) → 修复后 4 PASS
```

## 关键词
tempdir, /tmp, erofs, read-only, TMPDIR, cookiejar, OCASSERT, ocinternal.c, ddispatch,
curlflags, cookie jar, HMDFS, DAP

## 适用边界
- 适用：非 Windows 分支硬编码 /tmp 且不读 TMPDIR/TMP 的 C 库，在 /tmp 只读平台
  （OHOS erofs）上需要临时文件/缓存文件（cookie jar、下载暂存等）
- 反例：库已读 TMPDIR、或平台 /tmp 可写 → 无需补丁；纯设置环境变量（E002）仅当
  库本身尊重 TMPDIR 时有效

## 关系字段
- similar_to: E002（/tmp 只读+TMPDIR 通用建议）；DRAFT-E547 / DRAFT-E571
  （libcheck 临时目录优先级，同族但触发库不同）
- caused_by: OHOS /tmp erofs 只读 + ddispatch 硬编码 /tmp 不读环境变量
- prerequisite_of: 依赖 DAP client 的库在 /tmp 只读平台上的运行可用性
- conflicts_with: 无

---
*由 netcdf-c 4.9.3 适配任务生成（2026-09-16）*