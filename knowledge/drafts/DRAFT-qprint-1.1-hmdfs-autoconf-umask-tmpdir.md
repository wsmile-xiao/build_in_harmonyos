**DRAFT-qprint-1.1-hmdfs-autoconf-umask-tmpdir — 旧版 autoconf 的 umask 077 临时目录在 HMDFS 上被压成 drwx--S---，config.status 写入即拒；umask 022 一行修复**

触发：qprint 1.1.dfsg.2（旧版 autoconf 2.59 一代）在真机 conan create 中 configure 最后一步失败。根因：`(umask 077 && mktemp -d "./confXXXXXX")` 在 HMDFS 上产出组位仅 setgid 的目录，后续对 `subs1.awk` 的重定向前置检查即被拒。修复：configure 一行补丁（umask 022）+ 老 Makefile installdirs 补丁。修复后 conan create 全绿（编码/解码往返 + 已知值消费者测试）。

**身份与当前结论**

| 字段 | 内容 |
|---|---|
| 草稿 ID | `DRAFT-qprint-1.1-hmdfs-autoconf-umask-tmpdir` |
| 配套结构化文件 | `knowledge/drafts/DRAFT-qprint-1.1-hmdfs-autoconf-umask-tmpdir.kv` |
| 当前状态 | 已有验证证据待审 |
| 建议去向 | 新增模式（HMDFS 文件系统语义 × 旧版 autotools） |
| 包及配方版本 | qprint / 1.1.dfsg.2 |
| 上游版本与源码 | Debian orig tarball；sha256 5bfb038c05453db8f356dd01e06e2dd5629519faa26c9ab190d67a3e71de6f02 |
| 最后更新 | 2026-09-20 |

**1. 触发与签名**：真机 conan create 日志 `./config.status:602: permission denied: ./confFAGLbI/subs1.awk` + `config.status: error: could not setup config files machinery`；签名验证：失败样本命中（两轮日志），修复后样本不命中。

**2. 根因与排除**：设备对照实验——`umask 077; mktemp -d ./confXXXXXX` → `ls -ld` 得 `drwx--S---`，`echo hi > $D/f` → Permission denied；同目录 `umask 022` 建目录（2751 型）→ 写入成功。排除：磁盘满（同目录可写）、竞态（两次复现一致）、SELinux 类（无此报错形态）。HMDFS 忽略常规 umask/chmod 语义（与 E524 的 chmod-ignored 家族同根），组权限位被压缩为 setgid-only 是关键形态。

**3. 最小修复**：①`patches/0001-configure-hmdfs-tmpdir-umask.patch`：configure 中 `umask 077` → `umask 022`（单用户构建树内临时目录，无安全损失）；②`patches/0002-Makefile-in-installdirs.patch`：老 Makefile 把 `$(BINDIR)` 列为 install-bin 前置目标且无创建规则 → 新增 `installdirs: mkdir -p $(BINDIR) $(MAN1DIR)`。

**4. 验证矩阵**：EVID-01 失败基线（两轮 conan create，错误原文如上）；EVID-02 umask 对照实验（设备实测）；EVID-03 修复后 conan create 退出码 0，消费者测试输出 `roundtrip: OK / known-value: OK / test_qprint: OK`（编码→解码逐字节一致 + `=` → `=3D` 已知值）。

**5. 测试统计**：上游 0（清点：源码包仅 qprint.c/getopt/configure/Makefile.in，无 tests/、无 make check）；消费者 2/2；实验断言 2/2（失败基线 + umask 对照）。

**6. 边界**：已验证 HMDFS + 旧版 autoconf（相对路径临时目录）；未验证 NFS/ext4 等常规 fs（umask 077 在其上本就合法）；新版 autoconf（2.69+ 用 TMPDIR 与管道替换）不触发。

**7. 自检**：- [x] ID/文件/doc_file 一致、KV 单行；- [x] 证据链完整（target-executed）；- [ ] PR 编号回填。剩余：影子 CI → 提交 → PR。
