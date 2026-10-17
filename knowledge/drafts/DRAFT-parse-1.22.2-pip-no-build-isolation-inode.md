# DRAFT-parse-1.22.2-pip-no-build-isolation-inode：pip 构建隔离 overlay 在 inode 受限 worker 上触发 Errno 28——纯 Python 包配方须加 --no-build-isolation

> Contributor: pc1-15 | Status: Draft | Updated: 2026-09-21
> Source: parse 1.22.2 适配（Path B 知识库扩展）；触发场景：`finish` W3 本地 CI 模拟 conan create 阶段
> 对应：`knowledge/drafts/DRAFT-parse-1.22.2-pip-no-build-isolation-inode.kv`

## 现象

`ohc-run.py finish <lib> <ver> built` 的 W3 本地 CI 模拟中 conan create 失败：

```text
ERROR: Could not install packages due to an OSError: [Errno 28] No space left on device:
'/storage/Users/currentUser/tmp/pip-build-env-*/overlay/lib/python3.12/site-packages/setuptools/_vendor/tomli-2.4.0.dist-info/METADATA'
note: This error originates from a subprocess, and is likely not a problem with pip.
ERROR: parse/1.22.2: Error in build() method
```

**关键点**：`df -h` 块空间充足（928G/66%），报错却是 "No space left on
device"——这是 **inode 耗尽**（`df -i` IUse%=100），不是磁盘满。

## 根因

pip 对带 `[build-system].requires` 的 pyproject.toml 默认做**构建隔离**：
创建 `pip-build-env-*` overlay 并安装 build backend（setuptools 及其
vendored 依赖，成百上千个小文件）。worker 共享分布式文件系统（HMDFS）
inode 池全局 100% 水位时，overlay 的任意文件创建都会触发 Errno 28。
parse 是纯 Python 包，环境已装 setuptools 84.0.0 >= pyproject 要求
61.2，构建隔离纯属多余——复用已装 backend 即可。

## 修复（已验证）

conanfile.py `build()` 中 pip 命令加 `--no-build-isolation`：

```bash
python3 -m pip install --no-deps --no-build-isolation \
    --target="{install_target}" "{source_folder}"
```

- `--no-build-isolation`: 复用已安装 setuptools（>= pyproject 要求），
  不创建 pip-build-env overlay，inode 占用仅为本包文件
- `--no-deps`: 纯 Python 包无运行时依赖时不经 pip 拉取（保持既有范式）

复验：修改后 `conan create` 全绿（test_package 15 项断言全 PASS），
finish W3 build_and_test.sh RC=0，`.ci-result.json` exit_code=0。

## 适用范围

任何纯 Python 包（`pip install` 路径）在 inode 受限共享文件系统 worker
上的 Conan 配方与直编；环境已具备 >= pyproject 要求版本的 build backend
时通用（worker 全局 inode 池共享，任何新库 R01 都可能触发）。

## 边界 / 反例

- 若 build backend **缺失**（如 vfit 的 legacy poetry 后端），
  `--no-build-isolation` 无法绕过（仍需现场安装后端）——见
  DRAFT-vfit-2.1.0-legacy-poetry-copytree-wrapper，走 copytree 免构建方案
- 必须先确认报错是 inode（`df -i` 100%）而非块空间；盲目加超时预算不解决
- `--no-build-isolation` 不改变 `--no-deps` 语义，两者独立

## 关系

- caused_by / similar_to: DRAFT-shared-fs-inode-exhaustion（inode 诊断与错峰）
- similar_to: DRAFT-vfit-2.1.0-legacy-poetry-copytree-wrapper（pip 相关纯 Python 打包）
- 适用原则: W3（本地编译验证）、R33（build() 不依赖未定义 shell 环境变量）
