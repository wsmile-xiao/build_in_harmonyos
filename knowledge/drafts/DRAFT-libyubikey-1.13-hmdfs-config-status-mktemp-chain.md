# DRAFT-libyubikey-1.13-hmdfs-config-status-mktemp-chain

> Status: Draft | Updated: 2026-09-27 | Source: libyubikey 1.13 真机 shadow CI r1（job libyubikey-1.13-20260927）

## 摘要

OHOS 真机上 autotools 包修完「configure 脚本无法直接执行」（E232：`sh ./configure`
解释器调用）后，**紧接着的第二个失败点**是 config.status 的临时目录创建：

```
./config.status[960]: can't create ./confXXXXXX/subs1.awk: Permission denied
config.status: error: could not setup config files machinery
```

该错误签名目前在知识库（graph + drafts）中没有条目；4ti2、abnfgen 等配方已在
build() 内联修复但从未沉淀。任何走 E232 修复路径的 autotools 包都会在下一步撞上它。

## 两级失败链（libyubikey 1.13 实测，2026-09-27）

1. 第一级：`/system/bin/sh: .../configure: Permission denied`（Error 126）。
   HMDFS 对当前会话新建的**脚本**一律拒绝 execve；解释器调用可执行。
   E232 的 `sh ./configure` 方案解决本级。
2. 第二级：configure 能跑到生成 config.status，但 config.status 用
   `(umask 077 && mktemp -d "./confXXXXXX")` 建私有临时目录，在 HMDFS setgid
   目录下产物为不可写（drwx--S--- / 组权限不足），写 subs1.awk 被拒。

## 设备状态补充（E490/E232 的边界，2026-09-27 实测）

- 对新建脚本 `chmod 777` 实际落盘 `rwxr-x---`，owner 显示为 20001006（非当前
  会话 uid/gid），**other 位被剥离——chmod 补救执行位无效**。E490 的
  chmod +x 方案在当前 HMDFS 状态下不能恢复脚本可执行。
- **编译出的 ELF 二进制可以直接执行**（无 `Permission denied`，无需手工
  sign-elf；工具链链接时自动处理）。make check 跑测试二进制、test_package
  跑消费者二进制均不受 execve 限制影响。
- 结论：脚本一律解释器调用（`sh x` / `bash x`），不要指望 chmod。

## 修复

configure **运行前**把 mktemp 分支替换为普通 mkdir（configure 会把该段原样
嵌入 config.status 模板，事后补丁 config.status 来不及——configure 生成后
立即执行它）：

```python
old = 'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null` &&\n  test -d "$tmp"'
new = 'tmp=./conf$$-$RANDOM && mkdir "$tmp"'
# load()/replace()/save() 到 configure，找不到模式时 warn（上游文本可能变了）
```

落地：archives/l/libyubikey/1.13/conanfile.py `_patch_configure_mktemp()`；
同款先例：abnfgen/0.21、4ti2/1.6.10（配方内联，未入知识库）。

配套：`TMPDIR` 需要 writable（设备 /tmp 只读），配方内
`os.environ.setdefault("TMPDIR", os.path.expanduser("~/tmp"))`。

## 验证

- 真机探针：补丁后 `sh ./configure` → `make -j1` → `make check`（TOTAL=1
  PASS=1）→ `make install DESTDIR` 全通过。
- shadow CI r4（run codex-1.13-libyubikey-1.13-20260927-conan-20260927-150715-23005）
  L0/L1/L2/L5 pass、exit 0。

## 相关条目

- E232：configure 解释器调用（本条是其修复链的下一环）。
- E490：chmod 恢复执行位——本条实测证明其对脚本已失效，仅历史参考。
- DRAFT-6487：CONFIG_SHELL 用 hnp bash 触发 getcwd 风暴——所以本方案
  `CONFIG_SHELL=/bin/sh` 而非 hnp bash。
- DRAFT-10767：config.guess 探测失败的另一条路线（显式三元组）；本案例
  2023 版 config.guess + TMPDIR=~/tmp 下探测可直接通过。
