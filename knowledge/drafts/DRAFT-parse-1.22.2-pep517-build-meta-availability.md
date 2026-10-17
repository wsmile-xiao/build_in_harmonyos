# DRAFT-parse-1.22.2-pep517-build-meta-availability：--no-build-isolation 下 CI 环境缺 setuptools.build_meta——build() 首步显式安装 setuptools

> Contributor: pc1-15 | Status: Draft | Updated: 2026-09-21
> Source: parse 1.22.2 r02 返工（远端 CI conan create PEP 517 BackendUnavailable）；触发场景：PR #11627 远端 CI 配方修复
> 对应：`knowledge/drafts/DRAFT-parse-1.22.2-pep517-build-meta-availability.kv`

## 现象

PR #11627 远端 CI conan create 阶段失败：

```text
BackendUnavailable: Cannot import 'setuptools.build_meta'
prepare_metadata_for_build_wheel 失败
ERROR: parse/1.22.2: Error in build() method
conan create 退出码 1 → L1_RESULT=fail，L2/L4/L5 skip
```

**关键点**：同样的配方在本机 conan create 通过（r01 已全绿），在远端 CI 设备
Python 上失败——同一配方跨环境的后端可用性假设不一致，属当前库配方适配问题，
不得标为 external_blocked。

## 根因

r01 为规避 inode 受限 worker 的 pip-build-env overlay（Errno 28）在配方中加入
`--no-build-isolation`。该选项跳过构建隔离、直接复用执行环境的 PEP 517 build
backend（setuptools.build_meta）。本机 python3 自带该后端（r01 通过），远端
CI 设备 Python 缺该后端 → pip 导入后端失败 → BackendUnavailable。

修复必须同时满足两个环境的约束：
- 本机 worker：inode 池 100% 水位，pip build isolation overlay 会 Errno 28
- 远端 CI：`--no-build-isolation` 下必须能导入 setuptools.build_meta

## 修复（已验证，terminator/2.1.5 同款路径）

conanfile.py `build()` 首步显式安装 setuptools，随后保留 `--no-build-isolation`：

```bash
python3 -m pip install --break-system-packages --timeout 120 --retries 3 setuptools
python3 -m pip install --no-deps --no-build-isolation --target="{install}" "{src}"
```

- 首步 `pip install setuptools`：wheel 安装、**不创建 pip-build-env overlay**
  （不触碰 inode 上限）；`--break-system-packages` 绕过 PEP 668 externally-managed
  守卫；`--timeout/--retries` 增强 PyPI 网络韧性
- 两步效果：本机 setuptools 已装（幂等，秒过）；CI 先装后端后
  `--no-build-isolation` 导入 `setuptools.build_meta` 成功

复验（2026-09-21）：本地 `conan create` 全绿（test_package 15/15），鸿蒙专项
8/8，finish W3 RC=0，`.ci-result.json` exit_code=0；构建依赖核验
`import setuptools`=84.0.0、`import setuptools.build_meta` OK（11:58:19Z，退出码 0）。

## 适用范围

所有纯 Python 包配方在 `pip install --no-build-isolation` 下跨环境（本地/CI）
执行、而任一环境缺 PEP 517 后端（setuptools.build_meta / hatchling /
flit_core 等）时的通用修复。

## 边界 / 反例

- 反例（fallback）：若执行环境 inode 充足，可去掉 `--no-build-isolation`
  让 pip 自建隔离环境并自动安装后端（internetarchive/5.10.1 路径）；但
  inode 受限 worker 上 overlay 会 Errno 28（r01 首错），必须先确认环境
- 与 DRAFT-vfit-2.1.0-legacy-poetry-copytree-wrapper 的区别：vfit 的 legacy
  poetry 后端整体缺失且不可安装 → 走 copytree 免构建；本候选的 setuptools
  后端可安装 → 显式安装后仍走正常 pip install。不要照搬 copytree。
- `--break-system-packages` 仅影响 PEP 668 守卫，不改变 `--no-build-isolation`
  与 `--no-deps` 语义

## 关系

- similar_to: DRAFT-vfit-2.1.0-legacy-poetry-copytree-wrapper
  （BackendUnavailable 同 error_signature 族，方案不同）、
  DRAFT-parse-1.22.2-pip-no-build-isolation-inode（caused_by 链：
  inode 方案引入 --no-build-isolation → 触发 CI 后端缺失）
- 适用原则: W3（本地编译验证）、R33（build() 不依赖未定义 shell 环境变量）