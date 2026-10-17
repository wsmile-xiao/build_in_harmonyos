# DRAFT-ohos-elf-skip-strip-codesign：跳过 strip、打包 unstripped 的替代路径

> Contributor: nymphcast-0.2 适配 | Status: Draft（扩展项，合并候选） | 2026-08-27
> Source: archives/n/nymphcast/0.2-alpha0（patch 0007）+ round-5 真机实测

## 现象

nymphcast 0.2-alpha0 在 OHOS 上链接后的二进制被 GNU strip / llvm-strip 修改后，
真机 exec 报 `operation not permitted`（EXIT=126）；unstripped 二进制
`--version` 正常（EXIT=0）。`readelf -x .codesign` 显示 strip 前后 `.codesign`
段内容一致——签名校验失败，不是权限问题。

## 根因分析

OHOS clang/lld 在**链接期自动生成自签的 `.codesign` 段**（lld 自签）。任何后续
修改 ELF 内容（strip、patchelf、objcopy）都会使该签名失效，而 `binary-sign-tool`
无法覆盖已有签名段（"section already exists"）。E077/harmonyos-specifics §5
给出的是**重签名流程**（先 `llvm-objcopy --remove-section .codesign`，再
`binary-sign-tool sign`，最后 `chmod a+x`）——正确但需要 3~5 步且依赖
binary-sign-tool。

## 替代路径（本条目）

对**不需要 strip/调试分离**的产物（tool/app 型配方，体积敏感度不高），更简单
可靠的方案是**跳过 strip，直接打包 unstripped 二进制**：

```makefile
# Makefile（nymphcast 0007）
ifneq ($(OHOS),true)
$(STRIP) $(TARGET)
endif
```

- 产物可执行、无需重签名，无 `.codesign` 失效路径。
- 代价：体积增大（nymphcast 实测 53MB unstripped）；无 .debug 分离。
- README/notes 需声明"unstripped + 无调试分离"（nymphcast NCF-07 已声明）。

round-9 权威 CI PASS，test_package 在 conanrun env 下真实运行 `--version`。

## 与既有条目的关系（合并建议）

- **E077.kv** / **knowledge/operations/harmonyos-specifics.md §2/§5**：均以
  "重签名流程"为唯一方案，未记录"跳过 strip 直接打包 unstripped"的替代路径。
- 建议：作为 E077 的 similar_to / §5 的补充小节并入，明确"什么时候可以跳过
  strip、什么时候必须走重签名流程（体积敏感/调试分离需求）"。
- 差异：E077 覆盖"已 strip 后如何修复"；本条目覆盖"如何从一开始避免 strip
  引发签名失效"，属于前置规避路径。

## 验证证据

- round-5：unstripped --version EXIT=0；GNU strip 2.45 / llvm-strip 后 EXIT=126
  EPERM；readelf -x .codesign 两文件内容一致 → 签名校验失败。
- round-9：权威 CI PASS，产物 53MB unstripped 打包成功。

## 禁止做法

- 不要裸 strip 而不处理签名（EXIT=126 EPERM，被误判为权限问题）。
- 不要以为 chmod 能修复——签名失效与权限无关（E077 同）。
