# carburetor 4.5.1 适配笔记

## 编译环境
- 构建系统: meson (原项目使用 pyproject.toml/flit，为适配 OpenHarmony 预编译框架创建 meson.build)
- 编译日期: 2026-05-29
- 编译器: clang/clang++ (本项目为纯 Python 项目，无 C/C++ 编译)
- 状态: built

## 编译步骤

1. `ohc-run.py init-build carburetor 4.5.1 --url=... --no-download`
   - 使用阿里云镜像下载源码包（pythonhosted.org 直连超时）
2. 创建 `meson.build` 文件（原始项目无 meson 构建文件）
3. 创建 `bin/carburetor` 入口脚本（替代 pip/flit 的 gui-scripts 入口点）
4. `meson setup builddir --prefix=$DEFAULT_PREFIX`
5. `ninja -C builddir` (纯 Python 项目，ninja 无编译工作)
6. `DESTDIR=$TEST_PREFIX ninja -C builddir install` (安装到 staging 目录)
7. `ninja -C builddir test` (无测试定义)
8. `ohc-run.py verify-build carburetor 4.5.1` (质量门禁 PASS)
9. `ohc-run.py package carburetor 4.5.1` (打包 release 版)
10. 手动创建 debug 版本包（纯 Python 项目，debug 与 release 相同）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | pythonhosted.org 下载超时 | 网络环境无法直连 PyPI CDN | 使用阿里云 PyPI 镜像下载 |
| 2 | meson setup 失败 - 缺少 meson.build | 原项目是 Python/flit 构建，无 meson 构建文件 | 为项目创建 meson.build 文件 |
| 3 | 缺少启动入口脚本 | meson 不生成 Python entry point | 手动创建 bin/carburetor 入口脚本 |
| 4 | G4 门禁 FAIL - manifest 缺少 build_system | 初始模板缺少 build_system 字段 | 更新 manifest.yaml 添加 build_system: meson |
| 5 | 缺少 aarch64-debug 包 | package --debug 未生成独立 debug 包（纯 Python 项目） | 手动复制创建 debug 版本包 |

## 源码修改

### 新增文件
1. **meson.build** - 为 Python GTK 项目创建 meson 构建配置，安装 Python 模块、gresource、locale、desktop 文件、图标、man 页面等
2. **bin/carburetor** - Python 入口脚本，调用 `carburetor.carburetor:main()` (替代 pip gui-scripts)

### 补丁
- 0001-meson-build-and-entry-point.patch (包含 meson.build 和 bin/carburetor)

## 依赖版本

- Python 3.12.8 (系统自带)
- meson 1.11.1 (预编译)
- ninja 1.13.1 (预编译)
- GTK 4 / libadwaita (运行时依赖，非编译依赖)
- traxtor (运行时 Python 依赖)

## 验证结果

```bash
# meson 构建验证
meson setup builddir --prefix=$DEFAULT_PREFIX → 成功
ninja -C builddir → 成功 (0 编译目标)
DESTDIR=$TEST_PREFIX ninja -C builddir install → 成功 (37 文件安装)
ninja -C builddir test → 无测试定义
ohc-run.py verify-build → PASS (G1-G4 全通过)
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| carburetor-4.5.1-ohos-aarch64.tar.gz | 250KB | release 预编译包 |
| carburetor-4.5.1-ohos-aarch64-debug.tar.gz | 250KB | debug 预编译包（纯 Python 项目，与 release 相同） |

## 注意事项

1. 这是纯 Python GTK (libadwaita) 项目，运行需要 GTK4/libadwaita/gi 等图形库
2. 原项目依赖 `traxtor` (Python 包)，需要作为运行时依赖安装
3. carburetor 是 Tractor (Tor 代理管理器) 的 GTK 前端，需要 tractor 服务在后台运行
4. 源码下载需要使用国内 PyPI 镜像（阿里云等），pythonhosted.org 直连超时
5. debug 和 release 包内容相同（纯 Python 项目无 ELF 二进制文件）---

**编译结束**: 2026-08-05 16:46
**最终状态**: built
---

**编译结束**: 2026-08-05 16:52
**最终状态**: built
