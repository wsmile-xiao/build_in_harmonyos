# kicad-library 3d-10.0.5 测试报告

> **项目**: kicad-library 3d-10.0.5（上游 kicad-packages3D tag 10.0.5）
> **测试日期**: 2026-09-24
> **测试类型**: 上游数据普查、配方静态检查、消费者测试（本地/真机/CI 结果已回填）

## 一、上游数据普查（GitLab API，2026-09-24）

| 指标 | 数值 | 说明 |
|:----:|:----:|:------|
| `.3dshapes` 目录 | 105 | 与 tag 10.0.5（commit `67538dca…`）根目录一致 |
| `.step` 文件 | 7245 | 全量遍历 105 个目录统计 |
| `.wrl` 文件 | 0 | KiCad 10 已移除 VRML 模型 |
| 上游 CTest | 0 | `.gitlab-ci.yml` 仅 include 外部 kicad-library-utils 模板，无本地测试 |

## 二、配方静态检查

| 测试项 | 命令/证据 | 结果 |
|--------|-----------|------|
| 生产配方语法 | `python -m py_compile conanfile.py test_package/conanfile.py` | ✅ PASS |
| YAML 结构 | `yaml.safe_load(conandata.yml, manifest.yaml, MANIFEST.yml)` | ✅ PASS |
| 源码校验和 | sha256 `318d41cf…47e4c` 与 Ubuntu `kicad-packages3d_10.0.5-1.dsc`（PGP 签名）Checksums-Sha256 一致，本地下载实测（313174800 字节） | ✅ PASS |
| 源码可达性 | USTC / 阿里云 Ubuntu pool 双镜像 200 OK（CI 无法直连 gitlab.com 的替代源，2026-09-24 实测） | ✅ PASS |
| 探针编译 | 本地 C++17 编译消费者探针 | ✅ PASS |

## 三、消费者测试（探针断言清单）

探针 `kicad_library_3d_probe` 在安装树上执行以下断言（合计约 120 条）：

1. 资源根目录存在；
2. `KICAD10_3DMODEL_DIR` 已导出且与测试根一致；
3. 恰有 105 个 `.3dshapes` 目录；
4. 每个 `.3dshapes` 目录至少 1 个 `.step` 模型（105 条）；
5. 全树恰有 7245 个 `.step` 文件；
6. 4 个代表性模型（电阻/电容/电池/LED）存在且 STEP 结构标记完整；
7. 截断 STEP 输入被拒绝；
8. OHOS 构建的 `__OHOS__` / `--require-ohos` 门禁。

## 四、执行结果（真机 + CI）

### 4.1 真机验证（2026-09-25，OpenHarmony PC aarch64，Conan 2.29.1 OHOS 适配版）

- **conan 包构建**：源码经 USTC Ubuntu pool 镜像下载（sha256 `318d41cf…` 校验通过）
  → 3.3GB 解包 → 上游 CMake 安装规则执行 → **7245 个 `.step` 全部安装**，
  `LICENSE.md` 安装至 `licenses/`，`package()` 成功（`Packaged 7245 '.step' files`）；
- **探针编译**：test_package 使用仓库 `ci/conan/profiles/ohos-aarch64` profile
  （os=OHOS / arch=armv8 / clang 15.0.4 / libc++ / C++17）编译链接成功；
- **探针真机运行**：对 conan 包安装树执行消费者探针，输出
  `kicad-library probe passed: assertions=120 shape_dirs=105 steps=7245 ohos_build=true`，
  **120/120 断言全部通过**（`ohos_build=true`，`__OHOS__` 编译门禁生效）；
- 真机环境备注：真机 GNU make 4.4.1 在 `-j20` 并行编译模式下存在静默失败缺陷
  （无诊断直接退出），以串行编译验证，不影响结果正确性；CI 官方 worker 无此问题。

### 4.2 CI 验证

- 仓库原生 CI（ohpcd-robot）构建 **#60400 通过**：PR 模板检查、L0 质量门禁、
  conan create（含 test_package 构建执行）全绿。

### 4.3 测试摘要

| 测试项 | 结果 |
|--------|------|
| 上游测试 | 无（unavailable，上游源码归档无 CTest 套件） |
| 消费者探针断言 | **120/120（100%，真机实测）** |
| 真机运行环境 | OHOS aarch64 / clang 15.0.4 / libc++ / C++17 |
