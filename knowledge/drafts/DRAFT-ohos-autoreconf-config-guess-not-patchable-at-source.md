# autoreconf 生成的 config.guess 无法用 source 期补丁修

> Draft: `DRAFT-ohos-autoreconf-config-guess-not-patchable-at-source`
> 配对同 stem 的 `.kv`：`DRAFT-ohos-autoreconf-config-guess-not-patchable-at-source.kv`
> 来源：swtpm 0.10.1 适配（`archives/s/swtpm/0.10.1`，2026-09-20）
> 严重度：medium（阻塞 configure，但修法明确、一次到位）

## 差异化定位（避免与既有条目重复）

| 既有条目 | 讲的是什么 | 与本文的差别 |
|----------|-----------|--------------|
| **E007 / E072 / E268** | `patch-autotools-ohos.pl` 如何给**已在源码树里**的 `config.guess`/`config.sub` 打 OHOS 分支；老版脚本格式差异 | 那类前提是文件**已经存在**。本文讲的是更前一步：**文件根本还不存在**（构建期才由 autoreconf 生成），故常规补丁无从落点 |
| **DRAFT-ssdeep-oldautotools-m4-config-guess-chain** | 2012 年代老 autotools tarball：`m4/libtool.m4` 缺失 + 2005 版 config.guess，靠 vendored `patches/autotools/` + `libtoolize --copy --force` 解决 | ssdeep 是**tarball 自带旧 config.guess**（存在但过老），修法走 vendored 替换；swtpm 是**完全没有该文件**，修法必须在 build() 内就地插入分支 |
| **DRAFT-autotools-config-guess-two-generation-formats** | GNU config.guess/sub 两代格式（2023 vs 2024+）的补丁写法差异，重点在 `config.sub` 的 kernel-os 列表与 `\` 续行 | 讲的是**补丁内容怎么写**（generation 差异）；本文讲的是**补丁该放在哪个阶段**（source 期 vs build 期），与内容无关 |
| **E601** | `ohc-run.py refresh-patch` 在 `prebuild.sh`/autoreconf 场景下的 patch 刷新问题 | 属工具链流程（refresh-patch）问题，非「补丁落点阶段」问题 |

**一句话差异**：既有条目都在讨论「怎么给 config.guess 打补丁」或「补丁内容格式」，
本文讨论的是「**这个文件在 source() 阶段还不存在，所以补丁必须换个时机打**」。

## 现象

上游为 git archive tag 快照（`v0.10.1.tar.gz`），包内**没有** `configure`、
`config.guess`、`config.sub`，只有 `configure.ac` / `Makefile.am`。因此配方按
本仓惯例使用 `tool_requires("automake/1.18") + tool_requires("libtool/2.5.4")`
并在 `build()` 内执行 `autoreconf -fi` 自行生成构建系统。

此时在 HarmonyOS 上 configure 直接失败：

```
checking build system type... configure: error: cannot guess build type; you must specify one
```

手工执行 `config.guess` 可看到根因：

```
config.guess: unable to guess system type
  uname -m = aarch64
  uname -s = HarmonyOS
  ...
This script (version 2024-07-27), has failed to recognize the operating system
```

## 根因

1. **文件是「现造」的**：`config.guess` 由 autoreconf 从 automake 安装目录复制
   （实测来源 `<automake-prefix>/share/automake-1.18/config.guess`）。
2. **该版本不认 HarmonyOS**：`grep -c HarmonyOS` 结果为 **0**（`grep -c ohos` 亦为 0）。
   HarmonyOS 的 `uname -s` 返回 `HarmonyOS`，脚本没有对应分支即报
   `unable to guess system type`。
3. **补丁放错阶段必然失败**：写在 `conandata.yml` 的补丁在 `source()` 阶段应用，
   而那时 `config.guess` **尚未生成**，没有可打的文件。

> 对比：`config.sub` **无需处理**。实测 `automake/1.18` 自带的 `config.sub`
> 已能接受 `aarch64-unknown-linux-ohos`（原样输出、rc=0），这与老版 autotools
> 需要补 `linux-ohos*` 内核白名单的情况**不同**（见 E268）。

## 修法（推荐）

在 `build()` 内、`autoreconf` 成功之后、`configure` 之前就地插入 HarmonyOS 分支：

```python
def _patch_config_guess(path):
    """等价于本仓 scripts/patch-autotools-ohos.pl 的 config.guess 部分。"""
    with open(path, "r", encoding="utf-8") as f:
        data = f.read()
    if "HarmonyOS" in data:
        return False
    block = (
        "    *:HarmonyOS:*:*)\n"
        "\tcase \"$UNAME_MACHINE\" in\n"
        "\t    aarch64|arm64) MACHINE=aarch64 ;;\n"
        "\t    armv7*|armv8*) MACHINE=arm ;;\n"
        "\t    x86_64|amd64)  MACHINE=x86_64 ;;\n"
        "\t    i?86)         MACHINE=i686 ;;\n"
        "\t    *)            MACHINE=\"$UNAME_MACHINE\" ;;\n"
        "\tesac\n"
        "\tGUESS=${MACHINE}-unknown-linux-ohos\n"
        "\t;;\n\n"
    )
    marker = "    *:NetBSD:*:*)\n"
    idx = data.find(marker)
    if idx < 0:
        raise ConanException(
            "config.guess: NetBSD insertion point not found; upstream layout changed.")
    with open(path, "w", encoding="utf-8") as f:
        f.write(data[:idx] + block + data[idx:])
    return True

def build(self):
    self.run("autoreconf -fi", cwd=self.source_folder, env="conanbuild")
    if str(self.settings.os) == "OHOS":
        _patch_config_guess(os.path.join(self.source_folder, "config.guess"))
    autotools = Autotools(self)
    autotools.configure()
```

要点：
- 插入点选 **NetBSD 分支之前**（case 顺序上安全，且与本仓 perl 脚本一致）。
- 找不到插入点时**显式抛错**，不要静默跳过——否则上游将来改布局会退化成
  「无法 guess」的难查故障。

## 禁止做法

**不要用 `--build` / `--host` 传三元组绕过**：

- 违反本仓 **R1**（native 编译，禁止显式三元组）；
- 且 CI 上传 `--build=<gnu triplet>` 会触发
  `C compiler cannot create executables`（psfex / weightwatcher / skymaker 同报），
  **本地验证通过不代表 CI 通过**。

## 验证

```bash
# 1) 上游快照确实不含 configure / config.guess
tar tzf v0.10.1.tar.gz | grep -E '(^|/)(configure|config\.guess)$'   # 期望：无输出

# 2) automake 自带的 config.guess 不认 HarmonyOS
grep -c HarmonyOS <automake-prefix>/share/automake-1.18/config.guess  # 期望：0

# 3) 修补后实测
sh config.guess        # 期望：aarch64-unknown-linux-ohos

# 4) 端到端
conan create archives/s/swtpm/0.10.1 --version=0.10.1 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing
```

实测（swtpm 0.10.1，OHOS aarch64）：
- 修补前：`unable to guess system type` → configure 报 `cannot guess build type`
- 修补后：`aarch64-unknown-linux-ohos`（rc=0），configure 正常推进
- 端到端：`conan create` EXIT=0

## 相关条目

- `E007` / `E072` / `E268` — 给**已存在**的 config.guess/sub 打 OHOS 补丁
- `DRAFT-ssdeep-oldautotools-m4-config-guess-chain` — tarball 自带**旧版** config.guess 的 vendored 替换
- `DRAFT-ohos-install-truncates-large-binaries-codesign-loss` — 同一 PR 的另一个发现（install 期产物截断）
