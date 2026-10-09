# config.status 在 HMDFS 上写不进"自己刚建的临时目录"：本地全绿、CI 间歇失败

> Draft: `DRAFT-REFLEX-20241231-HMDFS-TMPDIR-CONFIG-STATUS-EACCES`
> Stem: `reflex-20241231-hmdfs-tmpdir-config-status-eacces` — pairs with the same-stem `.kv`

## 基本信息

- **ID**: DRAFT-REFLEX-20241231-HMDFS-TMPDIR-CONFIG-STATUS-EACCES
- **严重度**: 2
- **类别**: filesystem|hmdfs|autotools|ci-only-failure
- **触发工具**: configure|config.status|conan|make
- **阶段**: configuration

## 错误特征

本地 `conan create` 全绿，GitCode CI 在 autotools 包的**配置末尾**失败（构建 #65023 / worker CI-015）：

```
configure: creating ./config.status
./config.status: line 244: /storage/Users/currentUser/.cache/tmp/cslDeidH/subs.sed: Permission denied
./config.status: line 365: /storage/Users/currentUser/.cache/tmp/cslDeidH/subs.frag: Permission denied
config.status: creating install-man
./config.status: line 553: /storage/Users/currentUser/.cache/tmp/cslDeidH/out: Permission denied
rm: /storage/Users/currentUser/.cache/tmp/cslDeidH/stdin: Permission denied
cp: bad '/storage/Users/currentUser/.cache/tmp/cslDeidH/out': Permission denied
./config.status: line 656: /storage/Users/currentUser/.cache/tmp/cslDeidH/in: Permission denied
./config.status: line 690: /storage/Users/currentUser/.cache/tmp/cslDeidH/undefs.sed: Permission denied
grep: install-man: No such file or directory
```

注意：**configure 的全部探测都通过了**，只有 `config.status` 段炸；且 `TMPDIR` 指向的是
`$HOME/.cache/tmp`（HMDFS 用户卷），不是 worker 自己导出的 `/data` 路径。

## 机理

autoconf 生成到 `config.status` 正文里的临时目录段落：

```sh
# Create a (secure) tmp directory for tmp files.
: "${TMPDIR=/tmp}"
{
  tmp=`(umask 077 && mktemp -d -q "$TMPDIR/csXXXXXX") 2>/dev/null` &&
  test -n "$tmp" && test -d "$tmp"
}  ||
{
  tmp=$TMPDIR/cs$$-$RANDOM
  (umask 077 && mkdir "$tmp")
} ||
```

紧接着就是第一处写入：

```sh
sed 's/,@/@@/; ...' >"$tmp"/subs.sed <<\CEOF
```

HMDFS 上"刚建好的目录"其属主/权限元数据不会立刻对调用者生效（同族问题还有
`config.status` 读自己毫秒前写的 `subs1.awk` → `could not setup config files machinery`），
于是第一次重定向就 EACCES，之后每个临时文件同理。

三个迷惑点：

1. `configure` 通过、`config.status` 失败 ⇒ 看起来像构建中途随机崩；
2. 失败路径在 `$TMPDIR` 下，而 `$TMPDIR` 是被上层环境覆盖成 HMDFS 的（实测
   `$HOME/.cache/tmp`），worker 自身导出的是 `/data/storage/el2/base/cache`；
3. 本地机器的 `TMPDIR` 恰好在 `/data` ⇒ 本地全绿，完全复现不了。

**性质：间歇竞态，不是确定性必现**（这一条容易误判，务必先分清）：

- 同一 PR 的 #65046（worker CI-003）在**修复前的同一份代码**上**通过**（评论明确标注
  构建包为 `archives/r/reflex/20241231`、各步骤 ✅）⇒ 同一份代码可失败也可通过；
- 该 PR 首轮的 #65021 失败于 `git-clone`（`cannot exec 'git-remote-https'`），属 worker
  基础设施问题，**根本没跑到 `config.status`** —— 不能把它计入"同点复现"。

所以正确表述是：**时序相关的间歇竞态**（HMDFS 新目录权限元数据的生效延迟）。
推论：**重试有可能偶然通过，但根因真实存在，必须从根因消除，不能靠重试**。

**判据（比"同点复现"更可靠）**：

1. `configure` 通过而只有 `config.status` 段失败 —— 这个"分段特征"本身就很独特；
2. 失败路径在 `$TMPDIR` 下、且该路径落在 HMDFS 用户卷（`/storage/...`）；
3. 逐条核对失败构建的**失败步骤**：`conan-build-test` 才有意义，`git-clone`/`cleanup`
   一类失败属基础设施，与配方无关。

## 修复

**recipe 侧（环境）**：`configure` 之前把 `TMPDIR`/`TMP`/`TEMP` 钉到经探针验证的可写根。

探针必须是"**建目录 → 立刻往该目录里写文件 → 回读**"，普通的 `isdir()`/可写判断抓不到这个
bug（父目录是好的，坏的是刚建的子目录）：

```python
@staticmethod
def _usable_tmpdir(candidate):
    try:
        os.makedirs(candidate, exist_ok=True)
        old = os.umask(0o077)
        try:
            probe_dir = tempfile.mkdtemp(dir=candidate)
        finally:
            os.umask(old)
    except OSError:
        return False
    try:
        probe = os.path.join(probe_dir, "probe")
        with open(probe, "w") as fh:
            fh.write("ok")
        os.chmod(probe_dir, 0o700)
        with open(probe) as fh:
            return fh.read() == "ok"
    except OSError:
        return False
    finally:
        shutil.rmtree(probe_dir, ignore_errors=True)
```

候选顺序优先**非 HMDFS** 的 `/data` 缓存（`/data/storage/el2/base/cache`），其后
`$HOME/tmp`、构建目录下的 `hmbs-tmp`、最后才是继承来的 `$TMPDIR`；全部不过时**保留原值并告警**，
不要抛错（否则会把本来能过的构建弄挂）。

**configure 侧（补丁）**：去掉 `umask 077` 依赖，并在临时目录创建后显式
`chmod 700 "$tmp" 2>/dev/null || true`。`mktemp -d` 本来就会申请 `0700`，补丁只是让该权限位
在元数据滞后的文件系统上**确定生效**，安全语义不变。这行会随 heredoc 一并流入生成的
`config.status`，因此一次补丁同时覆盖 configure 与 config.status 两段。

**消费端测试脚本**同样要探针化：生成物、`.o` 与链接出来的消费者程序都放在那个临时目录里。

## 验收

```bash
# 补丁进入生成的 config.status
grep -n 'chmod 700' config.status            # -> chmod 700 "$tmp" 2>/dev/null || true
grep -n -A3 'mktemp -d -q' config.status     # -> 不再有 umask 077

# recipe 探针生效（构建日志）
grep -n 'Using usable TMPDIR=' <conan-create.log>
# -> reflex/20241231@ohpcd/stable: Using usable TMPDIR=/data/storage/el2/base/cache

# 全量回归仍绿
make check && make check COMPRESSION=-Ce     # "Check successful, using COMPRESSION=..."
```

## 关联

- 同族：`config.status` 读自己刚写的 `subs1.awk`/`subs.awk`（`could not setup config files machinery`）。
- 同族：HMDFS execve/新文件信任延迟、`init-build` 硬链接基线等"本地过 ≠ 没问题"的宿主特性。
- 旁证（非本包、仅供交叉参考）：CI 看板上另有一个 `perl-crypt-openssl-bignum/0.09-r13`
  构建失败于 `.../conan2/p/b/perl-.../p/lib/auto/Crypt/OpenSSL/Bignum/Bignum.so: Permission denied`
  —— 同样是 **`/storage` 用户卷上的文件权限元数据不可靠**（该例表现为 ELF 加载期）。属相邻现象，
  不能作为本包的定案证据，但说明该 CI 宿主的用户卷权限语义值得单独警惕。
- 误导源：CI 评论里的构建号（如 `#65046`）与 `https://ohpcd.atomgit.com/ci?id=<n>` 页面的
  构建号**不是同一命名空间**（本例该 id 指向的是 6 天前另一个包的构建）。判断某次 PR 构建结果
  时，应以 **PR 评论正文**（含"构建包"与步骤表）为准，不要用该网页反查。
