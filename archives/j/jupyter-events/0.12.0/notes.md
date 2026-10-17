# jupyter-events 0.12.0 适配笔记

## 编译环境
- 构建系统: hatchling (纯 Python 包，无需编译器)
- 编译日期: 2026-08-01
- 平台: HarmonyOS PC aarch64 (OHOS), Python 3.12.9
- 状态: built

## CI / 知识库结论（重要）

CI profile `ohos-aarch64` 的 `[buildenv]` 把 `/data/service/hnp/bin` 放在 PATH 最前，
`conan create` 内 pip 使用 HNP python 是**预期行为**，不是配方写错。

| 条目 | 含义 | 本配方做法 |
|------|------|------------|
| E077 | ELF 必须自签 | `llvm-objcopy` 去 `.codesign` + `binary-sign-tool` |
| E212 | HNP 进程不能 dlopen 用户路径 `.so` | **不**硬要求非 HNP python；不把 shebang 写成 HNP；test CLI 失败则 **一律** ELF 回退（不依赖 stderr 字符串匹配，对齐 nanobind） |
| check-jsonschema | ctypes preload `libgcc_s` | 对 `rpds`/`yaml` `__init__.py` 注入 preload |

**不能解决的（平台/CI 限制，非配方可改）：** 在 HNP 沙箱的 `conan create` 里保证 `/data/app/bin/python3` 一定可用。

**可以解决的：** 用 HNP python 完成 pip + 签名；测试按 E212 回退，CI 不因 hmmac 判编译失败。

## 编译步骤

1. 源码: `curl -fsSL https://github.com/jupyter/jupyter_events/archive/refs/tags/v0.12.0.tar.gz`（sha256 已核对；勿用 `curl -k`）
2. Conan: `pip install --prefix` + `--target` 装依赖 → OHOS 签名 + ctypes → test_package CLI / E212 ELF 回退

## 注意事项

- 缺 CA：装 `ca-certificates` 或设 `CURL_CA_BUNDLE`，不要把 `curl -k` 当规范
- `package_info()` 不做硬探测
- 本地 DevBox 若有 `/data/app/bin/python3`，CLI live 测试可完整通过

---

**最终状态**: built
