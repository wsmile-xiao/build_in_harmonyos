# DRAFT: OHOS profile 缺 os.version → settings.os.version value not defined

> 草稿编号：DRAFT-crossguid-0.2.2-ohos-profile-osversion-missing（同 stem .kv 配对）

## 问题

OHOS 适配任务以 `-pr:h=ci/conan/profiles/ohos-aarch64`（仓库相对路径形式）跑 `conan create` 时，
报 `Invalid: 'settings.os.version' value not defined`，被依赖包（如 uuid）一并拒收，任务无法构建。

## 根因

本地 conan 缓存 `~/.conan2/profiles/` 中存在字面名为 `ci/conan/profiles/ohos-aarch64` 的**陈旧 profile 副本**
（无 `os.version`，且 `compiler.cppstd=gnu14`、`compiler.libcxx=libstdc++11`，与仓库正确文件不一致）。
`-pr:h=ci/conan/profiles/ohos-aarch64` 按**缓存名**解析到该陈旧副本，而不是仓库路径文件。
OHOS 适配版 conan 对 `settings.os=OHOS` 强制要求 `settings.os.version`；缺失即 Invalid。
仓库正确 profile（`ci/conan/profiles/ohos-aarch64` 文件 / 缓存 `ohos-aarch64`）含 `os.version=6.0`、
`compiler.libcxx=libc++`、`compiler.cppstd=17`。

## 方案

1. 报错时先核对 `conan create` 输出头部的 **Input profiles** 与预期是否一致
   （是否缺 os.version、libcxx/cppstd 是否与仓库文件一致）。
2. 被缓存同名陈旧 profile 遮蔽时，改用缓存中内容正确的 profile 名或仓库文件的绝对路径：

```bash
conan create <recipe> --build=missing -pr:h=ohos-aarch64 -pr:b=ohos-aarch64
# 或
conan create <recipe> --build=missing -pr:h=/abs/path/ci/conan/profiles/ohos-aarch64 ...
```

3. 以两次运行（陈旧 profile 失败 / 正确 profile 成功）的 Input profiles 与退出码作为证据。

## 适用边界 / 反例

- 适用：本地 ~/.conan2/profiles/ 曾被导入过与仓库相对路径同名的 profile 的 OHOS 执行环境。
- 反例：平台/工具链真实缺失（非 profile 配置问题）时仍应按 `env_unsupported` 上报，
  不得以本规则掩盖。

## 验证

- crossguid 0.2.2：陈旧 profile `conan create` RC=6（uuid 与 crossguid 均报
  `Invalid: 'settings.os.version' value not defined`）；改用 `ohos-aarch64` 后 RC=0 构建通过。
- 既有条目检索：`os.version|value not defined|not a valid os` 在 index.tsv/doc/ 无正式条目；
  `similar_to=[E455]`（profile libcxx 配置族）。

## 查重结论

`exact_duplicate=false, causal_duplicate=false, trigger_overlap=none, solution_overlap=none,
combination_novelty=true, boundary_novelty=true, test_migration_novelty=false` → **new_draft**。

---
*作者: AtomCode | 来源: crossguid 0.2.2 (crossguid-0.2.2-r01-pc4-1) | 2026-09-27*
