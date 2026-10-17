## pullseq 1.0.2 OHOS aarch64 适配笔记（GLM-72，2026-09-21）

### 适配要点（配方 build() 内联，未走 patches/）
- E386 家族：`env -u CONFIG_SHELL SHELL=/bin/sh` 路由 shell，命令内联 `sh configure`；
  autoreconf 后 umask 077→022；`--build=aarch64-unknown-linux-gnu`（双 OHOS 会误判）。
- `-fcommon`：clang 15 `-fcommon` 语义下 QUALITY_SCORE 重复符号（vfork/QUALITY 全局）。
- 依赖 include/lib 手工注入 CPPFLAGS/LDFLAGS（conan 2.29 `tc.generate(env=)` 是整体替换）。
- package() 从 `self.build_folder/src` 取打包二进制（第 6 轮 create 实证）。

### 0001 补丁（本窗新增）：file_read.c char→int（aarch64 EOF 可移植性）
- 机制：aarch64 clang 的 plain char **无符号**，`file_read.c:23 char ch;` 接收
  `getc()` 的 EOF(-1) 变 255，`while ((ch = getc(fp)) != EOF)` 永不退出 →
  getl() 读循环无界 realloc（实测 34 字节 FASTA 输入吃到 6.4GB RSS，
  被本机 memguard 按 §14.1⑤ 授权止损；上游 signed-char 平台（x86 glibc）从不复现）。
- 同根因回溯：解释 GLM-67 时代 smoke 10.26GB 事件（当时误判为"输入过大"）。
- 修复：`char ch;` → `int ch;`（patches/0001-file-read-int-ch-eof.patch，唯一getc站点）。
- 修复后 conan-verify 全绿，消费者冒烟 `MEMCAP peak=197MB / budget=2500MB`（memcap-run.py 实测）。

### 上游测试清点（N_static=0）
- src/test_linked_list.c 为独立 main() 手工程序，未注册进 src/Makefile.am
  （bin_PROGRAMS 仅 pullseq、seqdiff），无 check target、无 test/ 目录——
  上游 1.0.2 不提供自动化测试，如实申报 N_static=0（详见 test_package/MANIFEST.yml）。

### test_package 实测（消费者测试补位）
- smoke.sh：两记录 FASTA 夹具，2 场景/6 断言——
  ①`-n names.txt` 按名提取（seq2 在、seq1 不泄漏）；②`-g SEQ1` 大小写不敏感正则提取。
- conan-verify G2 内真实执行：PASS（2026-09-21，peak RSS 197MB）。
- max_rss_mb: 2500（预算口径，实测峰值 197MB）。

### 下载源
- conandata.yml 官方 URL：https://github.com/bcthomas/pullseq/archive/refs/tags/1.0.2.tar.gz
  （ghfast 代理仅为本机 E017 下载注入，PR 内不留镜像形态；dlcache sidecar 双 URL 登记）

---

**编译结束**: 2026-09-21 23:05
**最终状态**: built
