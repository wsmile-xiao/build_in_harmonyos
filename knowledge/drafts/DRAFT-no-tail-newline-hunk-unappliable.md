# DRAFT-no-tail-newline-hunk-unappliable

## 症状

conandata.yml 注册的补丁触及"目标文件末行无换行符"的文件末行时（hunk 携带
`\ No newline at end of file` 尾标记），OHOS worker 上两条应用路径都失败：

- 设备 `patch` 命令（toybox 0.8.12）：

  ```
  Hunk 1 FAILED 1/1.
  ```

  rc=1，且目标文件未被修改——即使 hunk 的删除行与目标文件逐字节一致。
- conan `apply_conandata_patches` 的执行体 patch_ng（纯 Python）：在 parse
  阶段即抛解析异常，补丁应用在更早环节中断。

## 根因

目标文件末行无 LF 时，触及末行的 unified diff hunk 必须携带尾标记；而：

1. toybox patch 未实现尾标记匹配语义，上下文全匹配仍判 FAILED（与 GNU patch
   行为不同）；
2. patch_ng 解析器不接受含尾标记的 hunk。

两条路径全灭，属工具能力组合缺口，不是补丁内容写错。上游高频触发面是 Rust
生态的小配置文件——`.cargo/config.toml`、`rust-toolchain.toml` 等常无尾换行
（comet v0.3.2 的 `.cargo/config.toml` 尾字节实测无 LF，`od -c` 可复验）。

## 修复

不依赖 patch 工具：在 conanfile 的 source() 中直接移除或重写该文件，并在
notes.md 说明动机：

```python
def source(self):
    get(self, ...)
    # 上游 .cargo/config.toml 强制 gnu 交叉 linker，对原生 OHOS 构建无效；
    # 链接改由 RUSTFLAGS/CARGO_TARGET_*_LINKER 驱动。文件末行无换行，
    # 补丁在 toybox patch/patch_ng 双路径均不可应用，故移除。
    os.remove(os.path.join(self.source_folder, ".cargo", "config.toml"))
```

先例：comet/0.3.2（本条）、scooter/0.9.1 移除 rust-toolchain.toml。

## 退路（有代价）

先在 source() 给目标文件补上尾换行，再应用不带尾标记的常规 hunk。改变目标
文件字节、与上游 SHA 偏差，仅在文件不可移除时使用；应用后仍需确认 patch_ng
解析通过。

## 适用范围

- 所有经 apply_conandata_patches 或 patch 命令应用补丁的配方；
- hunk 触及无尾换行目标文件的末行即触发，与补丁内容正确与否无关。

## 反例/边界

- 补丁文件自身末尾缺换行是**另一互补面**（见 DRAFT-c-ares-lite-1.33.1：补丁
  文件必须保留末尾换行）——那条管补丁文件，本条管目标文件；
- 目标文件有尾换行时，toybox patch 应用常规 hunk 正常（E254/E510 讨论的是
  toybox patch 的其他面：--dry-run 污染、fuzz 容差）；
- 本 run（comet/0.3.2）无真实构建失败：Builder 探明风险后主动在 source() 规避，
  双路径失败由 Curator 自包含探针补证。

## 触发实例

- comet/0.3.2（2026-09-11）：conandata 补丁对上游 `.cargo/config.toml` 在设备
  上 `Hunk 1 FAILED 1/1.`；改为 source() 移除后 CI 全 gate PASS。

## 相关

- E010 / E098 / E254 / E510 / E402：toybox 能力差异族；
- DRAFT-c-ares-lite-1.33.1：补丁文件自身尾换行（互补面）；
- P-PATCH-001 / P-PATCH-004：补丁管线纪律。
