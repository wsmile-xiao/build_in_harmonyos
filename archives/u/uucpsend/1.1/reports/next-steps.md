# uucpsend 1.1 — 下一步命令

工作区：`D:\harmonyos\worktrees\uucpsend`
分支：`feat/uucpsend-1.1`（自 `origin/main` = `67fbdde039` 创建）
包路径：`archives/u/uucpsend/1.1`

## 0.1 工作区注意事项（重要）

本 worktree **启用了 sparse-checkout**，且 `archives/l/libXext`、`archives/l/libxext`
下的条目被 `git update-index --skip-worktree` 标记。原因：

> 仓库 index 里同时存在 `archives/l/libXext/` 与 `archives/l/libxext/`
> （两个不同软件条目），Windows 文件系统大小写不敏感，无法同时落地。
> 一旦对这两个路径做完整 checkout，后写的一方会覆盖另一方，`git status`
> 会永久显示 2 个文件 modified，并使 `git add -A` 误报删除。

因此：

- **不要**执行 `git sparse-checkout disable` 或全量 `git checkout .`
- 提交本库时用显式路径：`git add archives/u/uucpsend`
- 有效 sparse 模式：

  ```
  ci templates docs scripts archives/u/uucpsend/1.1 archives/u/uucp archives/i/inn2
  ```

## 0.2 提交状态

已 commit，**尚未 push**。提交内容仅为：

```
archives/u/uucpsend/
```

不含 `build_in_harmonyos` 基础设施（SKILL.md / references/ / templates/ /
scripts/ / ci/ / index.tsv / SUMMARY.md），不含其他库目录。

## 0.3 已完成（2026-10-02 真机实跑，见 device-build.md）

- ✅ G2 `conan create` 通过 —— recipe revision `6c16e7ec…`，package id `6b129b06…`
- ✅ L1 `test_package` **15/15 通过**
- ✅ L4 ELF 加固通过 —— PIE + RELRO + NX，`NEEDED` 仅 `libc.so`，`BIND_NOW`
- ✅ L5 产物通过 —— `bin/uucpsend` 43456 B，sha256 `70ff4a24…`，设备上实际执行成功

**仍需执行：W3 shadow CI（L0/L2/L3 闸门）。**

真机关键环境事实（下次直接用，别再踩）：

- `ci/conan/profiles/ohos-aarch64` 里 `/data/service/hnp/bin/clang` 在该设备
  **不存在**；真实工具链是 `/storage/Users/currentUser/usr/local/bin/clang`
- `git` 在 `/data/service/hnp/bin/git`，不在非交互 shell 的 PATH 里
- `TMPDIR` 必须显式设置（`/tmp` 只读）
- **在本设备上 source 过 `conanbuild.sh` 后运行 `make` 会 SIGSEGV**；
  本配方已改为不依赖该脚本（`env=None` + 显式 `CC=`），无需再排查

## 1. 真机前置（首次启动，按避坑指南 §11 顺序）

```powershell
ssh ohos 'echo "home=$HOME"; uname -a; id; pwd'
```

```sh
command -v sh; command -v git; command -v conan
command -v clang; command -v clang++
command -v make; command -v install; command -v mkdir
python3 --version 2>/dev/null || true
```

临时目录探针（避坑指南 §11.3）：

```sh
mkdir -p "$HOME/tmp-probe"
TMPDIR="$HOME/tmp-probe" sh -c 'tmp=$(mktemp); echo ok > "$tmp"; cat "$tmp"; rm -f "$tmp"'
```

隔离 Conan 配置（避坑指南 §10——新 `CONAN_HOME` 必须带项目定制
`settings.yml`，否则报 `Invalid setting 'OHOS'`）：

```sh
conan profile show -pr:h ci/conan/profiles/ohos-aarch64
conan profile show -pr:b ci/conan/profiles/ohos-aarch64
conan list '*'
```

## 2. W0 依赖复核（真机侧重跑一次）

`uucpsend` 无链接期依赖，但运行期需要下列程序。`uucp/1.07` 在本机侧
**未发布**，真机上再确认一次：

```sh
conan list "inn2/2.7.4:*" -r=ohpcd
conan list "uucp/*"       -r=ohpcd
```

预期：`inn2/2.7.4` 命中二进制包；`uucp` 报
`There are no matching recipe references` 或
`error:system acceleration policy not enabled.`。

**结论不影响本 PR**：这两个包都不是 `uucpsend` 的链接期依赖，只有真机部署
需要它们。若后续要真正投递新闻批，需先为 `uucp/1.07` 单独开一轮发布
（其配方已在 main，commit `5b8165f5ad`，`status: built`）。

## 3. 单包构建 + 消费测试（G2 + L1）

```sh
cd <repo>/archives/u/uucpsend/1.1
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 \
               -pr:b=ci/conan/profiles/ohos-aarch64 \
               --build=missing
```

预期日志关键行：

```
uucpsend/1.1: resolved toolchain: CC=/data/service/hnp/bin/clang AR=llvm-ar RANLIB=llvm-ranlib
uucpsend/1.1: Apply patch (portability): Make the hand-written Makefile ...
uucpsend/1.1: Apply patch (portability): Replace the BSD/legacy-POSIX index() alias ...
uucpsend/1.1: RUN: make all -j1 CFLAGS=-O2 -g -Wall -fPIE -fstack-protector-strong -std=gnu89 LDFLAGS=-pie -Wl,-z,relro,-z,now
uucpsend/1.1: built .../uucpsend (NNNN bytes)
uucpsend/1.1: RUN: make install DESTDIR=.../stage STRIP=
uucpsend/1.1: Testing package
assertions passed: 17
assertions failed: 0
RESULT: PASS
```

**若 `test_package` 断言失败**：`reports/local-verification.md` §4 记录了每条
断言的期望值来源（对 `parse_ctlfile()` / `extract_site()` / `trimm_sites()`
的逐行转写）。先对照该表判断是 fixture 问题还是程序行为差异，不要把断言
改宽松来凑过。

## 4. 产物校验（L4 / L5）

```sh
PKG=$(conan cache path uucpsend/1.1:<package_id>)
ls -l "$PKG/bin" "$PKG/share/man/man8" "$PKG/share/man/man5" \
      "$PKG/share/uucpsend" "$PKG/share/doc/uucpsend" "$PKG/licenses"

# L4：PIE / NX / RELRO
llvm-readobj -h "$PKG/bin/uucpsend" | grep -E 'Type|Machine'
llvm-readobj -l "$PKG/bin/uucpsend" | grep -E 'GNU_STACK|GNU_RELRO'
llvm-readobj --dynamic-table "$PKG/bin/uucpsend" | grep -E 'NEEDED|BIND_NOW'
```

预期：`Type: DYN (Position-Independent Executable)`、`GNU_STACK` 无 `E`（NX）、
存在 `GNU_RELRO`、`NEEDED` 只有 `libc.so`。

## 5. shadow CI 单包验证（W3）

```sh
CI_PACKAGES="archives/u/uucpsend/1.1" zsh ci/conan/build_and_test.sh
```

或：

```sh
/path/to/run-ohos-shadow-ci.sh archives/u/uucpsend/1.1
```

提交前确认：

- build 日志只发现目标包，`Build Summary` 为 `Total: 1`
- L0 pass（含 L0e `test_package/MANIFEST.yml` 存在；本包已提供）
- L1 pass（`test_package` 17 条断言）
- L2：命令行工具应为 `pass`（`uucpsend` 无 `--version`，冒烟步骤按 CI 定义处理）
- L4：本包有补丁，补丁文本已自查不含 `strcpy|sprintf|gets|strcat`，
  预期 `pass: patches clean`
- L5：`bin/uucpsend` 真实存在
- `ci-metadata.json` 与日志一致

## 6. 排队字段（避坑指南 §5）

```
库名：uucpsend
分支：feat/uucpsend-1.1
包路径：archives/u/uucpsend/1.1
预计耗时：< 5 分钟（620 行 C + 75 行 C，单文件级构建）
资源类型：CPU（极轻）
是否重任务：否
可接受运行时间段：白天任意时段；不与 Arrow / hdf5-mpi / qtquick3d 争抢
```

## 7. 已知限制（须写入 PR 描述）

1. **批处理路径不可端到端验证**：`loopthrough()` 依赖 INN spool 与 UUCP
   传输（`ctlinnd`、`batcher`、`uux`），独立包上无法真实投递。这是上游设计
   使然，不是配方缺陷；已作为运行期前置条件记录，未虚报为已测。
2. **`paths.h` 绝对路径未改**：`/var/spool/news`、`/usr/lib/news/bin`、
   `/usr/bin/uux` 等保持上游原样。改成可配置属功能变更，超出适配范围。
3. **`uucp/1.07` 未发布到制品仓**，若需真实部署须先解决。
4. **上游零测试资产**：无 `check`/`test` 目标、无测试目录，配方不虚构通过率。
