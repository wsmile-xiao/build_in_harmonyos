# DRAFT-ohos-autoconf-confstat-umask-077-perm：OHOS HMDFS 上 autoconf 老版本 config.status 的 confstat 临时目录（umask 077）写入 Permission denied→patch configure 的 umask 077→000

> Contributor: boa-0.94.14rc21 适配 | Status: Draft | Updated: 2026-08-24
> Source: archives/b/boa/0.94.14rc21（本地 conan create 实测）

## 现象

autoconf 2.59 生成的 config.status 在 OHOS 上运行到生成
Makefile/src/Makefile/src/config.h 阶段全部失败：

```
./config.status: line 442: ./confstatInHGJG/subs.sed: Permission denied
./config.status: line 716: ./confstatInHGJG/out: Permission denied
rm: ./confstatInHGJG/stdin: Permission denied
mv: bad './confstatInHGJG/out': Permission denied
config.status: creating src/config.h
./config.status: line 789: ./confstatInHGJG/in: Permission denied
```

configure 以 exit 1 结束，构建无法继续。

原因：config.status 创建临时目录用
`tmp=\`(umask 077 && mktemp -d -q "./confstatXXXXXX") 2>/dev/null\``，
umask 077 产物为 0700（实测 mktemp -d 创建为 `drwx--S---`）。OHOS
HMDFS 上该 0700 目录对构建进程不可写（owner 语义/权限模型与 Linux
不同），向其中写 subs.sed/subs.frag/out/in 全部 Permission denied。

## 主从根因

- **主根因**：OHOS HMDFS 权限模型差异——umask 077 创建的 0700 临时目录
  对进程不可写（平台限制，归轴 1 平台能力边界）。实测对照：同目录普通
  `mkdir`（2771 drwxrws--x）可写；`umask 000 && mktemp -d`（2771）可写；
  唯 `umask 077 && mktemp -d`（0700/drwx--S---）不可写。
- **附加 note（非主根因，同批老 configure 常伴生）**：
  - config.guess 为 2004 年老版本，不识别 HarmonyOS/aarch64——configure
    报 `cannot guess build type`——需显式 `--build=aarch64-unknown-linux-gnu`
    （ncurses/groonga 同款教训）。
  - OHOS 沙箱禁 mkfifo（`Operation not permitted`）——make -jN 的
    jobserver 需要 mkfifo——需显式 `make -j1`（nawk 同款教训）。

## 与现有知识的关系

- 现有 DRAFT-hmdfs-* 系列覆盖 HMDFS 的脚本执行/owner 检查限制，不覆盖
  autoconf confstat 临时目录写入——本主题无覆盖。
- 现有 E074（make -j FIFO jobserver）覆盖 mkfifo 禁用，与本主题的
  confstat 权限是同一批老构建系统的伴生问题——本文聚焦 confstat 部分。
- 跨库可复用：任何 autoconf 2.5x 时代生成的 configure（config.status
  用 `umask 077 && mktemp -d -q "./confstatXXXXXX"` 机制）在 OHOS 上
  都会命中——2000-2005 年间的 autotools 项目（boa/早期 Web 服务器等）。

## 方案

patch configure 脚本的 confstat 临时目录创建逻辑，umask 077→000（配方
build() 内文本替换，不改上游测试用例）：

```python
# 配方 build() 内（boa conanfile.py 实测有效）：
cfg = os.path.join(self.source_folder, "configure")
with open(cfg, "r", encoding="latin-1") as f:
    s = f.read()
s = s.replace(
    '(umask 077 && mktemp -d -q "./confstatXXXXXX")',
    '(umask 000 && mktemp -d -q "./confstatXXXXXX")')
s = s.replace("(umask 077 && mkdir $tmp)", "(umask 000 && mkdir $tmp)")
with open(cfg, "w", encoding="latin-1") as f:
    f.write(s)
```

patch 后 config.status 生成的临时目录为 2771（drwxrws--x），实测可写，
configure 完整跑通生成 Makefile/src/config.h。

## 验证

- 本地 conan create（boa/0.94.14rc21）通过：configure + make -j1 全过，
  Package created + test_package（boa -x usage）PASSED。
- patch 前后对照：patch 前 configure 报 confstat Permission denied 中断
  （exit 1）；patch 后 config.status 全部文件生成成功。
