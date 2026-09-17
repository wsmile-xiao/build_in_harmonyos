r2 静态内嵌对照证据（来自任务台账：r2 NEEDED 无 libgobject-2.0.so.0 + 强导出 g_type_register_fundamental）
--- r3 NEEDED ---
  0x0000000000000001 (NEEDED)       Shared library: [libglib-2.0.so.0]
  0x0000000000000001 (NEEDED)       Shared library: [libintl.so.8]
  0x0000000000000001 (NEEDED)       Shared library: [libgmodule-2.0.so.0]
  0x0000000000000001 (NEEDED)       Shared library: [libgobject-2.0.so.0]
  0x0000000000000001 (NEEDED)       Shared library: [libgio-2.0.so.0]
  0x0000000000000001 (NEEDED)       Shared library: [libpsl.so.5]
  0x0000000000000001 (NEEDED)       Shared library: [libnghttp2.so.14]
  0x0000000000000001 (NEEDED)       Shared library: [libc.so]
--- r3 无 g_type_register_fundamental 强导出(nm rc 应为 1) ---
nm_rc=1

## 基线隔离复验（W3/finish JC5 命中其他库基线文件）

- path: archives/u/util-linux-login/2.42.2/.ci-trigger（util-linux-login 2.42.2 的 CI 触发标记，main 提交 761df452 引入，属当前库允许范围外、提交前已存在）
- pre_sha256: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855（空文件）
- isolation_command: git rm --cached archives/u/util-linux-login/2.42.2/.ci-trigger（仅索引临时隔离，未提交）
- rerun_command: python3 scripts/ohc-run.py finish libsoup3 3.6.5-r3 built（JC5 通过）
- rerun_exit_code: 0
- restore_command: mv 回工作区 + git add -f 恢复索引
- post_sha256: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
- 结论: pre_sha256 == post_sha256；当前库 diff/staged/PR 不含该路径（git status 该目录为空）→ 基线隔离复验通过，未修改/未提交/未 PR 该基线文件
