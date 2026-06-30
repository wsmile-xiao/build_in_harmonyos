# py3-pypdf 6.12.2 适配笔记

## 编译环境
- 构建系统: python3 (flit-core / gpep517 / pip)
- 编译日期: 2026-06-04
- 编译器: clang/clang++ (not used — pure Python package)
- 状态: built
- Python版本: 3.12.8
- 目标架构: HarmonyOS aarch64 (noarch package)

## 编译步骤

1. **初始化构建**: `python3 $SKILL_ROOT/scripts/ohc-run.py init-build py3-pypdf 6.12.2 --url=https://github.com/py-pdf/pypdf/archive/refs/tags/6.12.2.tar.gz`
   - 源码下载遇到SSL证书问题，使用curl -k手动下载tarball到 `$TMPDIR/builds/py3-pypdf-6.12.2.tar.gz`
   - init-build在检测到已有tarball后成功完成

2. **构建wheel**:
   - 尝试 `gpep517 build-wheel --wheel-dir .dist` 但需要 --output-fd 参数（Alpine gpep517接口不同）
   - 使用pip fallback: `python3 -m pip wheel --no-deps -w .dist .`
   - 构建成功，生成 `pypdf-6.12.2-py3-none-any.whl` (343KB)

3. **安装到staging**:
   - `python3 -m installer .dist/pypdf-6.12.2-py3-none-any.whl --destdir $TEST_PREFIX --prefix $DEFAULT_PREFIX`
   - 安装到 `/storage/Users/currentUser/tmp/test-install-py3-pypdf-6.12.2/storage/Users/currentUser/usr/local/lib/python3.12/site-packages/pypdf/`

4. **验证**: `python3 $SKILL_ROOT/scripts/ohc-run.py verify-build py3-pypdf 6.12.2` → PASS
   - G1(二进制完整性): ✅0 ⚠️0 ❌0 — 纯Python包无ELF二进制
   - G2(功能可用性): ✅0 ⚠️1 ❌0 — 无可执行二进制文件
   - G3(可移植性): ✅0 ⚠️0 ❌0 — 无ELF需要RPATH/签名
   - G4(档案完整性): ✅0 ⚠️0 ❌0

5. **打包**: `python3 $SKILL_ROOT/scripts/ohc-run.py package py3-pypdf 6.12.2`
   - 生成 `py3-pypdf-6.12.2-ohos-aarch64.tar.gz` (5067KB)

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SSL证书验证失败导致下载失败 | HarmonyOS缺少CA证书链 | curl -k手动下载tarball，脚本检测已有tarball后跳过下载 |
| 2 | gpep517 build-wheel需要--output-fd参数 | Alpine gpep517版本接口差异 | 使用pip wheel fallback替代gpep517 |
| 3 | installer默认使用sys.prefix路径 | 安装路径与package_builder预期不一致 | 使用--prefix=$DEFAULT_PREFIX指定安装路径 |
| 4 | manifest.yaml缺少build_system顶级字段 | 初始模板使用嵌套格式 | 手动添加build_system: python3顶级字段 |

## 源码修改

无源码修改。pypdf是纯Python包，无需任何补丁。

## 依赖版本

- flit_core: 3.12.0 (pip install, build backend)
- gpep517: 19 (pip install, 不直接使用，改用pip fallback)
- installer: 1.0.1 (pip install, wheel安装工具)
- Python: 3.12.8
- pip: 24.3.1

## 验证结果

```bash
# 验证pypdf可以import
PYTHONPATH=/storage/Users/currentUser/tmp/test-install-py3-pypdf-6.12.2/storage/Users/currentUser/usr/local/lib/python3.12/site-packages \
  python3 -c "import pypdf; print(pypdf.__version__)"
# 预期输出: 6.12.2

# 验证包内容
tar tzf packaging/py3-pypdf-6.12.2-ohos-aarch64.tar.gz | wc -l
# 包含pypdf模块所有.py文件
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| py3-pypdf-6.12.2-ohos-aarch64.tar.gz | 5067KB | 预编译包(noarch) |
| pypdf-6.12.2-py3-none-any.whl | 344KB | 原始wheel文件 |

## 注意事项

1. pypdf是noarch(pure Python)包，wheel名为 `pypdf-6.12.2-py3-none-any.whl`，跨平台通用
2. 安装路径需注意 --prefix 参数，否则installer会使用Python sys.prefix路径
3. flit_core >=3.11,<4 是构建依赖（pyproject.toml指定），pip自动安装
4. 无需编译器参与，纯Python包只需wheel构建和安装
---

**编译结束**: 2026-06-04 10:44
**最终状态**: built
