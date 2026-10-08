# 脚本型 CLI（无库 API、无构建系统、只有一个 C 助手）：别让整段测试被架构守卫跳过
> Draft: `DRAFT-SCRIPT-CLI-TAR-ARCHIVE-TEST-WITHOUT-TARGET-EXEC`
> Stem: `script-cli-tar-archive-test-without-target-exec` — pairs with the same-stem `.kv`

## 基本信息

- **ID**: DRAFT-SCRIPT-CLI-TAR-ARCHIVE-TEST-WITHOUT-TARGET-EXEC
- **严重性**: 1
- **类别**: testing|build-system|arch|ohos-platform
- **触发工具**: conan|python3|qemu-aarch64|readelf
- **阶段**: testing

## 错误特征

交付物没有库 API，`test_package` 很容易退化成两种空壳之一：

1. 只跑 `工具 --version` / `--help` 冒烟（CI 的 L2 也会顺手做，等于没测）
2. 用架构守卫把**全部**断言圈起来，于是 x86 本地门禁整段跳过、断言数看起来正常，
   真正跑过目标产物的只有 CI 一次

```
$ python3 test_tool.py <pkg>/bin
104 checks passed, 0 failed
SKIP delivered helper execution — build machine is x86_64, the OHOS AArch64 worker runs it natively
```

还有一层更隐蔽的：`test_package` 没有自己的 `layout()` 时，Conan 把 `build_folder` 指到
`archives/<l>/<pkg>/<ver>/test_package/` **本身**，于是驱动写出的采集归档（`.tar`）留在源码树里，
下一次 `git add archives/<字母>/<包>` 就把它连同配方一起提交——JC3 / PF2 事后才拦。
更糟的是当时 `copy()` 没有 `chmod` 之类的小问题会让人以为"本地已经跑过一遍了"。

## 根因

交付物被拆成**架构相关**与**架构无关**两部分时，只有前者受"本机跑不了目标产物"限制：

- 架构无关部分（Python/Perl/shell 脚本主体）**在任何主机上都能真跑**，却常被 arch 门一起跳过，
  白丢绝大部分可执行断言；
- 架构相关部分（一个小 C 助手）如果只能靠"目标机上原生执行"验证，本地门禁对这段逻辑零覆盖。

叠加两个具体坑：

- 目标产物的正确性本来可以**纯文件断言**证明（ELF class / `e_machine` / `PT_INTERP`），
  根本不需要执行；
- 要让脚本主体拿到确定性数值，不必依赖目标机的 `/proc`、`/etc`，可以**按助手自己的归档格式
  合成一份输入**。

## 影响范围

- `build()` 只编译一两个 `.c`、`package()` 把 `.py`/`.pl` 当脚本安装的包（smem 及大量运维/诊断类老工具）
- 交付物是动态链接 OHOS AArch64 ELF（`interpreter` 为 AArch64 加载器）而本地/CI runner 不是 aarch64 的场景
- CI 强制 `test_package/test()` 有真实 `self.run` + 有测试源（L0c/L0d/L1d/R34/L1e）的场景

## 推荐方案

**方法**: `synthesize-the-tool-own-input-format-then-split-assertions-into-file-level-and-exec-level`

1. **先给断言分类**：
   - 文件级（存在性、可执行位、shebang、脚本能否被目标解释器 `compile()`、ELF `e_machine` /
     `PT_INTERP`、man 与许可证齐全）→ **无条件执行**，x86 与 aarch64 上都跑；
   - 执行级（真跑目标产物）→ 才加 `platform.machine()` 守卫，SKIP 时打印明确原因。
   这样"只能目标机跑"不再等于"本地零断言"。
2. **给脚本主体合成确定性输入**：读助手 C 源码，照它的 `writeheader()` / 归档写出顺序，
   用 Python 逐字节复刻一份归档（smemcap 的实测行为：tar 校验和 = 整块 512 字节求和时校验和字段
   仍是 8 个占位空格，等价于 tar 标准的"把校验和字段当空格"；uid/gid 写数字、uname/gname 恒空），
   数值字段填成**手算得出**的期望值，然后逐列断言。
3. **取值按"定宽 + 值可能含空格"解析**：工具按 `%8a` / `%-24.24s` 定宽打印，
   `command` / `map` / `area` 之类字段本身含空格。做法是"从行尾取固定个数的数值列 + 行首按 key 索引"，
   含空格的字段另用两列窄表单独校验。绝不能 `line.split()` 后按列号 zip。
4. **先证明输入本身合法再评价工具**：合成归档先用 `tarfile` 独立 reader 打开并核对成员集合与长度，
   否则 fixture 坏了会被误读成"工具坏了"。
5. **交付产物的运行取证按 macutils 先例做**：静态重链 + `qemu-aarch64` 实跑，并在 `notes.md` 写明
   "qemu 跑的是静态副本，不等于交付的动态产物已实跑，动态产物由 AArch64 CI worker 原生执行"。
6. **测试产物一律别落进 `archives/`**：驱动自选暂存目录（优先 `$SMEM_TEST_WORKDIR` →
   `tempfile.gettempdir()` → 自身目录），三条都不通才报错。既不假设 `/tmp` 可写，
   也不会污染源码树。

## 验证命令

```bash
# 文件级（任意主机）
python3 -c "import struct;d=open('<pkg>/bin/<tool>','rb').read();print(struct.unpack('<H',d[18:20])[0])"   # 期望 183 = EM_AARCH64
# 合成归档 + 全量断言
python3 test_package/test_<tool>.py <pkg>/bin
# 目标产物运行取证（x86 本机）
<clang> -O2 -static <src>.c -o /tmp/x && qemu-aarch64 /tmp/x > /tmp/live.tar && echo CAPTURE_OK
# 污染自检
git status --short archives/
```

## 取证记录

- 包：smem 1.5（`archives/s/smem/1.5`），Python 3 单文件主体 + 114 行 C 采集助手
- 环境：本地 x86_64 runner + profile `ohos-aarch64-wsl`；CI 为 AArch64 OHOS worker
- 逐字证据：`archives/s/smem/1.5/notes.md`（断言分组表 + qemu 取证输出 + 工作目录外置的两次提交）
- 断言数：恒执行 104 + AArch64 实机 6 = 110；鸿蒙特有 3
  （`reports/` 被仓库 `.gitignore` 排除，审计报告只落本地工作树，不随 PR 提交）