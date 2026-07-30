# screenresolution 1.6 路径 B 候选方案

## 方案

将上游 macOS CoreGraphics 专用的 `screenresolution` 拆成能力分层:

- macOS: 保留上游完整能力，使用 Foundation/ApplicationServices/CoreGraphics。
- OHOS: 新增 NativeDisplayManager 只读后端，支持 `-version` 和 `get`。
- OHOS: `list` 和 `set` 不伪装通过，返回明确 unsupported。

## 路径 B 候选理由

这不是单纯修 Makefile 参数，而是把一类 Apple 平台框架专用 CLI 的适配拆成:

1. 识别平台私有 API 依赖，不把 framework 当作可拆 Conan 依赖。
2. 查找 OHOS public native C API 的最小等价能力。
3. 建立“可迁移能力真实实现，不可等价能力明确拒绝”的测试边界。
4. 用消费者测试证明 OHOS 后端真实调用系统显示管理 API。

该方案可作为“macOS CoreGraphics 显示工具向 OHOS NativeDisplayManager 的能力分层迁移”路径 B 候选。

## 已完成交付物

- OHOS NativeDisplayManager 只读后端已实现并通过真机验证。
- `test_package` 覆盖 `-version`、`get`、`list` unsupported、`set` unsupported 四类断言。
- `list` 未枚举所有可切换模式是明确能力边界，不伪装为成功。
- `set` 未实现是明确能力边界，因为当前采用的公开 C API 没有等价物理分辨率 setter。
- 已新增知识图谱草稿: `knowledge/graph/draft/E240-draft-F72D.kv`。

## 申请前证据清单

- `CI_PACKAGES="archives/s/screenresolution/1.6" zsh ci/conan/build_and_test.sh` 通过日志。
- `test_package/test.sh` 输出:
  - `screenresolution version 1.6`
  - `Display 0: <width>x<height>x32@<refresh>`
  - `set is not supported on OHOS NativeDisplayManager backend`
- PR 正文明确:
  - 基础适配能力: `get/-version`
  - 平台能力边界: `list/set` unsupported
  - 不申请 Path C
  - 路径 B 仅作为候选，最终以官方审核为准

## 2026-07-25 validation update

True-device heavy validation passed:

```text
run_dir=/storage/Users/currentUser/ohos-test-runs/codex-1.6-screenresolution-1.6-native-display-conan-20260725-174545-48199
exit_code=0
L0_RESULT=pass: all checks passed
L1_RESULT=pass: test_package executed
L2_RESULT=skip: screenresolution version/help failed
L4_RESULT=pass: patches clean
L5_RESULT=pass: bin/ has content
```

Observed runtime behavior:

```text
screenresolution version 1.6
Display 0: 3120x2080x32@60
Error: list is not supported on OHOS NativeDisplayManager backend: the public C API used here exposes current default-display metrics, not the full switchable mode list
Error: set is not supported on OHOS NativeDisplayManager backend: the public C API used here does not expose a physical display mode setter
```

Path B can now be requested as a candidate based on a real OHOS backend, test-covered capability boundaries, and a screenresolution-specific knowledge draft.
