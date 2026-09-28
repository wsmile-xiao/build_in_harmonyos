# DRAFT-conan-settings-ohos-os-version-null：settings.yml 枚举缺 null 导致的 os.version 校验失败

## 触发场景

systemd 261.1 conan create（2026-09-19）r01-r04 连续四轮复现
`Invalid: 'settings.os.version' value not defined`：
liblzma/5.8.1、libzstd/1.5.7 与本包 systemd/261.1 三包同时 Invalid，构建无法启动。

## 症状签名

```
ERROR: There are invalid packages:
liblzma/5.8.1: Invalid: 'settings.os.version' value not defined
libzstd/1.5.7: Invalid: 'settings.os.version' value not defined
systemd/261.1: Invalid: 'settings.os.version' value not defined
```

即便 profile 已带 `os.version=6.0` 仍复现（r02/r03 绝对路径 + os.version=6.0 依旧失败）。

## 根因

Conan 2 中 os.version 是 os 的子设置。recipe 声明 `settings = "os", "arch",
"compiler", "build_type"`（未列 os.version 子设置）时，conan 校验该子设置值为
None 而 settings.yml 的 OHOS `version: ["5.0","6.0"]` 枚举不含 null → 抛
`'settings.os.version' value not defined`。这是工具链侧校验面：

- 与既有 DRAFT-elfio-3.9（profile 相对路径被 home 同名副本遮蔽）**同签名双根因**；
  本轮全程绝对路径仍失败，证明二者独立（elfio 方案不足以覆盖本根因）。
- 修复：本机 `~/.conan2/settings.yml` OHOS 块 `version: [null, "5.0", "6.0"]`，
  修复后 r09+ conan create 全绿（G2 PASS + test_package PASS）。

## 快速判定

```
grep -A1 '^    OHOS:' ~/.conan2/settings.yml
# ["5.0", "6.0"]（无 null）→ 命中本根因
# [null, "5.0", "6.0"] → 另查 profile 相对路径遮蔽（DRAFT-elfio-3.9）
```

## 验证

- 修改前：conan create r01-r04 exit=6/7，三包 Invalid；
- 修改后：conan create r09-r12 exit=0，G0-G4 + L2/L4/L5 全 PASS；
- CI 侧 settings.yml 允许 null，故仅本机环境差异，不属库配方缺陷。

## 适用边界

- 命中：未声明 os.version 子设置的 recipe + 本机 settings.yml 枚举不含 null。
- 反例：recipe 显式声明 os.version；settings.yml 已含 null（CI）。
- 关系：similar_to DRAFT-elfio-3.9-conan-profile-relative-path-shadowing（同签名，互补根因）。