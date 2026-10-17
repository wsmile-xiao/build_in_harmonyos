# E-DRAFT: refresh-patch 在 HMDFS 上 dry-run 创建 0 字节占位 → 新增文件补丁头误判

- **触发实例**：libfec 1.0 适配（2026-09-18，任务 libfec-1.0-r01-pc3-10）
- **错误签名**：`conan: Apply patch ... source/target file does not exist: --- a/cpu_mode_arm64.c`
- **类别**：hmdfs, tooling, conan, autotools
- **严重度**：2（W3 门禁确定性阻塞，修复模式固定）

## 症状

```text
libfec/1.0: Apply patch (portability): Add cpu_mode_arm64.c ...
libfec/1.0: .../patches/0005-cpu_mode_arm64.c.patch: source/target file does not exist:
  --- b'a/cpu_mode_arm64.c'
  +++ b'b/cpu_mode_arm64.c'
libfec/1.0: ERROR: Error in build() method (apply_conandata_patches)
```

## 根因

`refresh-patch --auto` 对新增源文件（.orig 中不存在，如 `cpu_mode_arm64.c`）生成
`--- /dev/null` 头的正确补丁后，会在 .orig 目录执行 `patch --dry-run -p1` 验证。
在 HMDFS（chmod 被忽略、写语义异常）上该 dry-run **实际创建了 0 字节目标文件**
（`$BUILD_SRC_ORIG_DIR/cpu_mode_arm64.c`，0 bytes）。

下一轮 refresh-patch 检测到 .orig 已存在该文件 → 判定为"修改文件"而非"新增文件"
→ 生成 `--- a/cpu_mode_arm64.c` 头。conan 的 apply_conandata_patches 对 `--- a/`
新增文件补丁报 source/target file does not exist（干净 tarball 中无该文件），
W3 门禁确定性失败。

## 解决方案

每轮 refresh-patch 前删除 .orig 中 0 字节占位文件：

```bash
rm -f $BUILD_SRC_ORIG_DIR/cpu_mode_arm64.c
python3 scripts/ohc-run.py refresh-patch --auto libfec 1.0
head -2 archives/l/libfec/1.0/patches/0005-cpu_mode_arm64.c.patch
# 必须为: --- /dev/null / +++ b/cpu_mode_arm64.c
```

生成后核对补丁头；若占位文件已随其他库入库（如 cloog 的 .build-closed），
按 baseline_isolation_audit 记录隔离复验，不得修改其他库文件。

## 适用边界 / 反例

- 适用于在 HMDFS 上为新增源文件生成补丁并经 conan 应用的适配任务。
- 反例：新增文件补丁头必须是 `--- /dev/null`（conan patch 工具要求），
  不能把 0 字节占位文件提交入库（JC1 full 模式拦截）。

## 验证

```text
head -2 .../0005-cpu_mode_arm64.c.patch   →  --- /dev/null / +++ b/...
conan create（W3 build_and_test.sh）      →  L0 pass / L1 pass（test_package 执行）
```