# install 期未完整替换目标文件 → 包内产物截断、丢 `.codesign`、exec 报 EPERM

> Draft: `DRAFT-ohos-install-truncates-large-binaries-codesign-loss`
> 配对同 stem 的 `.kv`：`DRAFT-ohos-install-truncates-large-binaries-codesign-loss.kv`
> 来源：swtpm 0.10.1 适配（`archives/s/swtpm/0.10.1`，2026-09-20）
> 严重度：medium（构建全程 EXIT=0，但交付物不可执行——**静默失败**，危害大）

## 差异化定位（避免与既有条目重复）

| 既有条目 | 讲的是什么 | 与本文的差别 |
|----------|-----------|--------------|
| **DRAFT-ohos-elf-skip-strip-codesign**（nymphcast）/ **E077** | 主动执行 `strip` 会破坏 `.codesign`，修法是 **OHOS 下跳过 strip** | 那类前提是「有人调了 strip」。本例**没有任何 strip 步骤**（日志中 `strip` 仅出现在 configure 探测行），签名段是随 install 的截断一起丢失的；修法也不是「跳过 strip」，而是**从构建树回填产物** |
| **DRAFT-parallel-install-install-sh-eexist-race**（libjpeg6b） | `make install -j` 下 `install-sh` EEXIST 竞争，修法 `-j1` | 属**并行竞争**问题；本例配方本就用 `make -j1` 串行，与并行无关 |
| **E574**（libosip `install-sh` 批量丢失）/ **DRAFT-8958**（clthreads stage install 遮蔽） | install 脚本在某些情形下漏装/遮蔽文件 | 那是**文件缺失或被遮蔽**；本例是**文件在场但内容被截断**（体积从 7203328 缩到 1235968），且产物仍在 `bin/` 下可见——判据与修法都不同 |

**一句话差异**：既有条目都在讨论「strip 破坏签名」或「install 竞争/漏装」；
本文讨论的是「install **成功退出（EXIT=0）**但产物被截断、签名段随之丢失」——
一个**不报错的静默失败**，必须靠「执行产物」而非「检查文件存在」才能发现。

## 现象

swtpm 0.10.1 适配时，`conan create` 端到端 **EXIT=0**、`Package '...' created`，
但交付的核心可执行文件无法运行：

```
$ <pkg>/bin/swtpm --version
timeout: failed to run command '<pkg>/bin/swtpm': Permission denied
```

逐项对照（`llvm-readelf -S` 看段表）：

| 产物 | 构建树 | 包内 | `.codesign` | 可执行 |
|------|--------|------|-------------|--------|
| `swtpm` | 7203328 | **1235968** | 构建树 **1** → 包内 **0** | ❌ EPERM |
| `swtpm_setup` | 6072832 | **1028096** | — | ❌ EPERM |
| `swtpm_localca` | 2193920 | **268800** | — | ❌ EPERM |
| `swtpm_ioctl` | 43392 | 43392 | 1 | ✅ |
| `swtpm_bios` | 31104 | 31104 | 1 | ✅ |

构建日志中唯一的异常线索：

```
ginstall: error deallocating '<pkg>/bin/swtpm': Permission denied
ginstall: error deallocating '<pkg>/bin/swtpm_localca': Permission denied
ginstall: error deallocating '<pkg>/bin/swtpm_setup': Permission denied
```

三个报错恰好对应三个**大体积**产物；两个小体积工具未受影响。

## 根因（只写可复现的部分）

- **可复现的事实**：install 阶段对上述三个目标文件未能完整替换，留下体积被截断的
  副本；截断副本同时**不含 `.codesign` 段**（OHOS 链接期由 lld 写入）。
- **后果**：OHOS 内核对缺少签名的 ELF 拒绝执行 → `EPERM` / `operation not permitted`。
- **未定位的部分**：受影响的三个产物恰好都是动态链接 libtpms/glib 等外部库的
  大体积二进制，但**不能因此断定**是「体积」还是「依赖外部库」所致。
  在受控可写目录中单独调用 `ginstall -c` 覆盖同名文件是**成功**的
  （含「目标已存在」与「软链接占位」两种形态），故本机机理尚未复现。

> 之所以强调「未定位」：把机理写成确定的「HMDFS 上 ginstall 无法覆盖文件」会
> 误导后来者——按此假设去排查会找不到问题。**修法不依赖机理**，这也是本文的落脚点。

## 修法（推荐）：不信任 install 产物，从构建树回填

```python
def _restore_binaries(self):
    import glob as _glob
    bindir = os.path.join(self.package_folder, "bin")
    os.makedirs(bindir, exist_ok=True)
    for src_dir in sorted(_glob.glob(os.path.join(self.build_folder, "src", "*"))):
        name = os.path.basename(src_dir)
        candidate = os.path.join(src_dir, name)
        if not os.path.isfile(candidate):
            continue
        dst = os.path.join(bindir, name)
        if os.path.exists(dst):
            os.remove(dst)          # 必须先删：install 留下的是截断副本
        shutil.copyfile(candidate, dst)
        os.chmod(dst, 0o755)

def package(self):
    autotools = Autotools(self)
    autotools.install()
    self._restore_binaries()        # install 产物不可信，一律回填
```

**删除步骤是必要的**：直接 `shutil.copyfile` 覆盖同名文件未必能修正内容
（目标上仍是 install 留下的截断副本），先 `os.remove` 再拷贝可稳定还原
产物体积与 `.codesign` 段。

## 兜底修法：install 到干净目录再整目录拷入

若产物众多、逐个回填不便，可 `make install DESTDIR=<全新空目录>`，
再把该目录整体拷进 `package_folder`。受控实验已验证：**安装到干净目录时**
产物体积与签名字段均正常（7203328 bytes、含 `.codesign`、可执行）。

## 禁止做法

**不要用 `strip` 处理这类产物**。OHOS 上 strip 会移除/破坏链接期写入的
`.codesign` 段，使 ELF 无法执行（见 `DRAFT-ohos-elf-skip-strip-codesign`、`E077`）。
本例的截断副本同样是「签名段消失 → EPERM」的后果，用 strip 只会**加重**问题。

## 验证

```bash
# 1) install 阶段是否报了替换失败
grep -n "error deallocating" build.log

# 2) 构建树 vs 包内：体积与签名字段对照
stat -c "%s %n" build-release/src/swtpm/swtpm <pkg>/bin/swtpm
llvm-readelf -S <pkg>/bin/swtpm | grep -c codesign     # 修复后期望 1

# 3) 最终判据：真的能执行（这是唯一能发现静默失败的检查）
<pkg>/bin/swtpm --version                              # 期望输出版本号
```

实测（swtpm 0.10.1，OHOS aarch64）：

- 修复前：`bin/swtpm` 1235968 bytes、`.codesign` 计数 0、`--version` 报 EPERM
- 修复后：`bin/swtpm` 7203328 bytes、`.codesign` 计数 1、`--version` 输出
  `TPM emulator version 0.10.1`（rc=0），全部 5 个产物的 `.codesign` 计数均为 1
- 端到端：`conan create` EXIT=0，`test_package` **RESULT: PASS (7 checks, 0 failures)**

## 教训（供同类包参考）

1. **「构建 EXIT=0」不等于「交付物可用」**：本例全程无失败退出，
   唯一的线索是 install 日志里的一行 `Permission denied`。
2. **test_package 必须真的执行产物**（R34 反空壳）：只断言「文件存在」
   会让本问题 100% 漏网。本例 `test_package` 实际运行
   `swtpm --version` / `socket --help` / 拉起 TCP daemon 并连接控制通道。
3. **修法优先选不依赖机理的方案**：在机理未定位时，「一律从可信来源回填」
   比「猜测失败条件再绕开」更稳妥。

## 相关条目

- `DRAFT-ohos-elf-skip-strip-codesign`、`E077` — strip 破坏 `.codesign`（本文禁止的修法）
- `DRAFT-parallel-install-install-sh-eexist-race` — install 并行竞争（不同根因）
- `E574`、`DRAFT-8958-clthreads-makefile-stage-install-shadow` — install 漏装/遮蔽（不同表现）
- `DRAFT-ohos-autoreconf-config-guess-not-patchable-at-source` — 同一 PR 的另一个发现
