# dazz_db 1.0（官方 tag V1.0）适配笔记

## 编译环境

- 构建系统: makefile（上游手写 Makefile，无 configure）
- 编译日期: 2026-09-22
- 编译器: clang 15.0.4（`/data/service/hnp/bin/clang`，aarch64-linux-ohos）
- 状态: built（conan create 全绿，test_package 41/41）
- 源码: `thegenemyers/DAZZ_DB` 官方 tag `V1.0` = commit
  `40bb7e4b2041cdfd3c50b22201301b8df06342fa`（2015-06-15 "Interactive version"），
  官方 archive URL `https://github.com/thegenemyers/DAZZ_DB/archive/refs/tags/V1.0.tar.gz`
  下载产物 sha256 `ae7a71b71925dd5a1fd4026ca7462a70cb8ade9d3afd5cdeef0f1bd11b9c9105`
  （URL 重定向至 codeload 实测一致，解包顶层目录 `DAZZ_DB-1.0/`，22 个文件）。

> 版本关系：本仓库 main 上已有的 `archives/d/dazzdb/1.0-git20250217.a3eefd4` 是
> 2025-02-17 的 master 快照（21 个工具、含 zlib 链接依赖、含 arrow2DB/DB2ONE 等），
> 与本任务 1.0（官方 tag V1.0，13 个 ALL 工具、无 zlib、无 arrow/ONE 工具）是不同版本，
> 不构成重复 PR。任务 lib 为 `dazz_db`，归档目录采用任务正文 lib 字段命名。

## 编译步骤

上游 Makefile 16 条规则（13 个 ALL 工具 + 3 个 DBupgrade 迁移工具）各自
`gcc $(CFLAGS) -o <tool> <srcs> -lm`。配方不直接调用 make 默认规则，而是在
`generate()` 里生成 conanbuild 环境（CC 取 `tools.build:compiler_executables`
的 `c`，CFLAGS 复述上游默认值），`build()` 再执行：

```bash
make -j1        # 工作目录 = source_folder，env = conanbuild
```

产物为 13 个可执行文件（ALL 工具集），`package()` 逐一点名 install 到 `bin/`，
缺任何一个即失败。V1.0 全部 16 条规则只链 `-lm`，不引用 zlib（无
arrow2DB/DB2arrow，也没有任何 zlib API 调用），因此**无第三方 Conan 依赖**
（W0 预检通过）。

## 遇到的问题与解决方案

| # | 问题（第一条真实错误） | 根因 | 解决方案 |
|---|------------------------|------|----------|
| 1 | `make: gcc: No such file or directory`（16 条规则全部硬编码 gcc，exit 127） | 设备与 CI worker 只有 clang | 0001：每条规则改为 `$(CC) $(CPPFLAGS) $(CFLAGS) -o $@ <该目标原有的源文件列表> $(LDFLAGS) $(LDLIBS)`——源文件列表逐条保留而不是用 `$^`，并新增 `CC ?= gcc`、`CFLAGS ?=`、`LDLIBS = -lm` |
| 2 | `ld.lld: error: undefined symbol: rindex`（DB.c 4 处 + DBshow.c 1 处，另提示 did you mean: index） | OHOS libc 导出 `index` 但不导出 BSD 遗留别名 `rindex`（E570 同源） | 0002：5 处 `rindex(` 统一改写为 POSIX `strrchr(` |
| 3 | `DBshow -q/-Q <db>` 报 `Cannot open ./.GQ/GQ.db`（exit 1） | 上游 V1.0 `Load_QVs` 在 HIDE_FILES（PATHSEP="/."）下把可见 stub 路径拼成 `./.<root>/<root>.db`；2025-02 快照已修复 | 0003：按上游 2025 修复形态，`root = strrchr(db->path,'/')` 后判断 `root[1]=='.'` 再 `Catenate(db->path,"/",root+2,".db")`，否则 `Catenate(db->path,"","",".db")` |

0003 的实测形态：DB2quiva 往返、quiva2DB 导入均正常（不经过 Load_QVs 的 stub
打开路径），只有 DBshow -q/-Q（经 Load_QVs）触发；修复后 DBshow -q 与 -Q 均
exit 0 且输出真实 quiva 内容。修复形态与上游 a3eefd4（2025-02-17）快照逐行一致。

## 依赖版本

无第三方依赖。V1.0 的 16 条规则全部只链 `-lm`（libm 由 OHOS libc 提供），
与 2025 快照（arrow2DB/DB2arrow 链 `-lz`）不同。

## 验证结果

```bash
# 配方与门禁（命令唯一权威副本见 manifest.yaml 的 validation 段）
python3 scripts/ohc-run.py conan-verify dazz_db 1.0 --project-dir <repo>

# 适配侧用例（test_package 以 env=conanrun 调用同一脚本）
sh test_package/test.sh <package_folder>/bin <work-dir>
# -> adaptation cases: PASS=41 FAIL=0 TOTAL=41 SKIP=0 / RESULT: OK
```

上游测试为 0 用例（非跳过、非部分执行），零入口证据与取数命令见
`test_package/MANIFEST.yml` 的 `upstream_tests` 段与版本级 `manifest.yaml` 的
`test_results.upstream.evidence`。适配侧 41 项断言覆盖全部 13 个 ALL 产物，
统计单位为断言（`test.sh` 的 ok/no 计数）。

测试覆盖要点（V1.0 工具集与 2025 快照差异已体现在断言设计）：
- awk 确定性合成 5000 bp 参考基因组（V1.0 无 rangen）→ fasta2DAM/DAM2fasta 往返逐字节一致；
- simulator 0.005 -c20. -r42 合成 19 条读段（V1.0 无 -U 选项，输出小写）→
  fasta2DB/DB2fasta 往返逐字节一致（DB2fasta 不带 -U，保持小写原样）；
- DBstats -n/直方图、DBshow/-w40；
- DBsplit -s1 + DBdust + Catrack 汇聚 dust 轨 + DBstats -mdust/DBshow -mdust
  （小数据量下 dust.data 可为 0 字节，断言只要求文件存在）；
- quiva2DB/DB2quiva 质量值流往返逐字节一致 + DBshow -q/-Q（0003 修复后通过）；
- DBrm 生命周期完整移除。

## 注意事项

- 上游把 `simulator` 这类通用名直接安装为可执行文件，本包安装到 Conan 包内独立
  `bin/`，不落系统目录。
- V1.0 的 3 个 DBupgrade.*/DUSTupgrade.* 是历史格式一次性迁移工具（不在 ALL），
  上游默认 `make` 不构建，本包不打包（与上游默认产物集一致）。
- V1.0 无 LICENSE 独立文件：上游把 BSD-3-Clause 许可文本写在 README 顶部版权块，
  `package()` 复制 README 到 `licenses/` 作为许可记录。
- V1.0 的 DBsplit 在已有分区时交互询问 `[Y/N]`，脚本化使用时 `printf 'Y\n' | ...`；
  首次分区（cutoff<0）不询问。
- 知识 E002（TMPDIR 方案）不适用本版本：V1.0 源码无 /tmp 硬编码（无 ONElib.c），
  不需要 0003-onelib 类补丁（那是 2025 快照的 ONElib 问题）。

## 基线隔离复验记录（W3/finish 命中其他库既有文件）

W3 本地 CI 模拟（build_and_test.sh）的 JC 杂项文件检查在**无分支提交、diff 为空**
时回退 full 模式（`git ls-files` 全仓 83977 个文件），命中 3 个**提交前已存在于
main、属于其他库**的运行时状态空文件（不属于本库、不由本任务引入、不得修改/提交）：

| path | pre_sha256（隔离前） | isolation_command | post_sha256（恢复后） |
|------|----------------------|-------------------|----------------------|
| archives/c/cloog/0.21.1/.build-closed | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 | git rm --cached <path>（工作树不动） | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 |
| archives/c/cloog/0.21.1/.staging-verified | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 | git rm --cached <path> | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 |
| archives/k/kics/2.1.20/.staging-verified | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 | git rm --cached <path> | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 |

- rerun_command: `python3 scripts/ohc-run.py finish dazz_db 1.0 built`（隔离期间复跑）
- rerun_exit_code: 0（隔离期间 W3 通过，后续 step8/10 缺项为归档收尾项，非构建失败）
- restore_command: `git reset --quiet HEAD <path>`（恢复 index 条目）
- 恢复后核对：3 个文件内容 SHA-256 前后一致（空文件），index 恢复为
  `100644 e69de29bb2d1d6434b8b29ae775ad8c2e48c5391`（= HEAD 原状）
- 当前库 diff/staged/PR 均不包含上述路径（本库只新增 archives/d/dazz_db/）

隔离复验通过：W3 的 JC 失败确为其他库既有基线噪声，非本库相关失败；按规则继续
当前库审计与交付。
---

**编译结束**: 2026-09-22 22:45
**最终状态**: built
