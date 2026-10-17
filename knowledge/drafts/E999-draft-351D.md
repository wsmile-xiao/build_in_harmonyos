# E999-draft-351D — 抽取式包的语言预检口径（上游语言 ≠ 交付物语言）

> 草稿，等待主编审核分配正式编号。
> 首次发现：`cargo-bash-completions 1.97.0`（上游 rust-lang/cargo，交付物为其中一个 bash 补全脚本）。

## 现象

源码 checkout 后按 R47 跑语言预检，默认口径直接失败并写终态回执：

```console
$ python3 scripts/ohc-run.py lang-preflight cargo-bash-completions 1.97.0 --src $BUILD_SRC_DIR
❌ 语言不匹配: task=cpp, detected=rust → env_unsupported
⚠️   协议要求: 不要硬着头皮适配；平台将按 detected_language 迁移/取消
{
  "error_type": "env_unsupported",
  "error_detail": "任务标记 cpp，实测源码为 rust（cargo），无法按 cpp 适配——按协议 v0.8 §7.2 交平台语言迁移",
  "detected_language": "rust",
  "language_evidence": {
    "build_system": "cargo",
    "manifest": "Cargo.toml",
    "source_stats": "源文件 1440 个（rust:1437, bash:6, python:2, nodejs:1），主体占比 100%"
  }
}
# rc=2，且已落 draft:false 的终态 result.json
```

## 根因

`scripts/ohc/lang_detect.py` 的判定对象是**整棵源码树**（优先级：manifest > 构建系统 >
源文件统计），而这类包的适配对象只是树里的**一个**非主体语言文件：

| 包 | 上游仓库（判定语言） | 实际交付物 |
|---|---|---|
| `cargo-bash-completions` | rust-lang/cargo（`Cargo.toml` → rust） | `src/etc/cargo.bashcomp.sh` |
| `docker-completion` | docker/cli（`go.mod` → go） | `contrib/completion/bash/docker` |
| 各类资源/数据抽取包 | 任意非 C/C++ 仓库 | man page / 图标 / 数据表 |

叠加规则 D.4「bash 文件不参与主体占比」，交付物自身对判定**零贡献**。于是
`expected=cpp` 与 `detected=rust|go|…` 必然不匹配，`lang_preflight_cli` 走 mismatch 分支，
自动写 `status=env_unsupported` 终态并 `exit 2`。

此时若按 R47 字面「非 C/C++ 立即终止」处理，会把一个**完全不需要该语言工具链**的纯数据包
误判为环境不支持。两种情形的判据不同：

| 情形 | 判据 | 正确处置 |
|---|---|---|
| 真 Rust/Go 应用（如 mcfly） | **构建**需要该语言工具链，CI 无 → 必然红 | 如实 `env_unsupported`（R47 本意） |
| 抽取式数据/脚本包（本条） | 交付物不编译，CI 不需要该工具链 | 显式 `--lang <上游语言>` 继续适配 |

## 处置（推荐）

1. **留证**：默认口径的输出存进 `archives/<l>/<pkg>/<ver>/reports/lang-preflight-default.log`
   （`rc=2` 与 `detected_language` 都是证据，不要抹掉）。
2. **如实声明**：用检测器给出的语言原值重跑：

   ```bash
   python3 $SKILL_ROOT/scripts/ohc-run.py lang-preflight <pkg> <ver> \
       --src $BUILD_SRC_DIR --lang rust        # rc=0 → 继续主流程
   ```

3. **配方三条自证**（缺一则说明判断错了，应回退到如实上报）：
   - 不声明该语言的 `requires` / `tool_requires`；
   - `build()` 不调用该语言工具链（本例只做脚本存在性/内容核验）；
   - `notes.md` 与 PR 正文写明「本包不编译该语言代码，CI 无需其工具链」。
4. **覆盖回执**：默认口径写出的 `env_unsupported` 终态，最后用
   `result … --force` 覆盖为真实终态。

## 禁止

- ❌ 用 `--lang cpp/c` 去「凑」过预检：伪造判定证据，W4/主编按 R52 审计失真一票否决。
- ❌ 为「让语言一致」而引入 `tool_requires rust/go`：把零依赖包变重型依赖包，并触发 PF4 依赖闸。

## 社区既有同口径先例（查重证据）

| 归档 | 口径 | 场景 |
|---|---|---|
| `archives/c/cronic/3` | `--lang other` | 纯脚本包 |
| `archives/p/pari-galpol/20180625`、`archives/p/pari-nflistdata/20220729` | `--lang other` | 纯数据包 |
| `archives/o/overdrive/2.4.1` | `--lang other` | 纯 Bash 包 |
| `archives/c/crunch64/0.6.2` | `--lang rust` | Rust 包（需工具链，另有 rust-toolchain） |
| `archives/d/d-shlibs/0.109` | `--lang bash` | Bash 包 |
| `archives/b/breeze-grub/6.7.2` | `--lang other` | 资源包 |

以上先例覆盖的是「包自身就是脚本/数据」的场景；**本条补充的新面**是
「包寄生在一个语言明确的大型上游仓库里，检测器判定正确但与交付物无关」——
此时正确口径不是 `other`，而是**上游实际语言**（如 `rust`），并附三条配方自证。

## 相关

- 相似但不同：`E172`（Rust 工具链 ELF 在鸿蒙不可执行 → 真正的 Rust 项目阻塞）。
- 规则：R47（语言预检前置）、W0b（CI 能力矩阵）、R52（审计证据一致性）。
