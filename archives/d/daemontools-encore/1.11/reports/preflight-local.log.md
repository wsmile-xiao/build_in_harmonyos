# preflight-local.log — 逐字留档（原文件不随 PR 入库）

- 原始文件: `archives/d/daemontools-encore/1.11/reports/preflight-local.log`（本机工作区，未入库）
- 字节数: 1596
- 行数: 16
- sha256: `b9664a3c3c3bd1944bb6f717dbcec9b0036df1b275543ddb1ccf6b3753e2ca15`
- 说明: 本地 preflight 等价执行（新包包级 PF9 例外留痕）
- 生成命令: `python3 scripts/ohc/preflight.py . upstream/main HEAD`
- 逐字性: fenced 内容与原文件逐字节一致（含行尾空格与末尾空行）；头部字节数/行数/sha256 均对原文件计算

以下为原文件逐字内容（```text 代码块）：

```text
### local preflight equivalent run for this PR (new-package PF9 exception)
$ python3 scripts/ohc/preflight.py . upstream/main HEAD
[31m✗ PF9 分支/路径闸: 变更路径缺版本目录层（须 archives/<字母>/<包>/<版本>/<文件>）——CI 将报 No packages to build（490 例）: archives/d/daemontools-encore/README.md, archives/d/daemontools-encore/commands.json, archives/d/daemontools-encore/manifest.yaml[0m
rc=1 (PF9 only)

PF1 单包闸 : pass — changed paths only under archives/d/daemontools-encore/ plus knowledge/drafts/
PF2 制品闸 : pass — 'git diff --numstat upstream/main...HEAD | awk '$1=="-"||$2=="-"'' is empty (no binaries/archives)
PF3 测试闸 : pass — test_package/conanfile.py test() calls self.run(sys.executable test_daemontools.py ...) which executes the packaged binaries
PF4 依赖闸 : pass — conanfile.py has no requires()/tool_requires(); W3 L0i registry check passed
PF5 平台宏 : pass — patches/0001-MAN-optional-setuser.patch adds no __OHOS__ macro
PF6 前缀闸 : pass — no SYS_PREFIX//usr/local injection
PF7 源URL闸: pass — conandata.yml source is the official https URL (untroubled.org)
PF8 配方闸 : pass — settings os/arch/compiler/build_type present; package dir/version slugs lowercase
PF9 分支闸 : FAIL (expected, new package) — package-level README.md/manifest.yaml/commands.json live at
              archives/d/daemontools-encore/<file> (4 segments) as ARCHIVE-SPEC v3.0 requires, while PF9 demands
              archives/<letter>/<package>/<version>/<file> (5 segments); documented conflict, see PR body
```
