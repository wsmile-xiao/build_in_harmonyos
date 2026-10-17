# 编译笔记 — pluggy 1.5.0

**软件名称**: pluggy (plugin and hook calling mechanisms for python)
**版本**: 1.5.0
**上游仓库**: https://github.com/pytest-dev/pluggy
**许可证**: MIT
**构建系统**: setuptools（纯 Python src layout: src/pluggy/）

## 软件简介

pluggy 是 pytest/tox/devpi 的核心插件系统，提供 HookspecMarker/HookimplMarker
装饰器与 PluginManager 1:N hook 调用机制。纯 Python 包，无 C 扩展
（src/pluggy/_hooks.pyx/_warnings.pyx 为 Cython 可选扩展，pip 默认构建纯 Python wheel）。

## 依赖

- 运行时依赖: 无
- 测试依赖: pytest, pytest-benchmark（上游 testing/ 目录）

## 构建方式

```bash
conan create archives/p/pluggy/1.5.0 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing -nr
```

- `pip install . --prefix=... --no-deps`（构建后端 setuptools + setuptools-scm，sdist 固定 __version__='1.5.0'）
- 不带 `--no-build-isolation`：构建 Python 未预装 setuptools/setuptools-scm，
  让 pip 自动创建隔离环境并从 pypi.cnb.cool 源下载构建依赖（同 pyparsing/cfgv 方案）

## 适配说明

1. **纯 Python 无 C 扩展**：构建用 sys.executable（Conan 运行的 Python），不使用 clang。
   conanfile 的 settings 含 os/arch 仅用于 R32 OHOS 平台兼容验证。
2. **源码下载缓存**：CI 无 GitHub 外网，源码 tarball 预置到 Conan 下载缓存
   （core.sources:download_cache=/storage/Users/currentUser/builds/conan-src-cache），
   get() 命中本地缓存不访问网络。
3. **PYTHONPATH 导出**：package_info 通过 runenv_info.append_path 导出
   site-packages 路径，供下游消费者和 test_package import pluggy。
4. **R32 平台兼容**：conanfile validate() 拒绝非 Linux/OHOS 的 OS。

## 质量门禁

- R32: settings.os 判断使用 in ("Linux", "OHOS") ✅
- R34: test_package 实质性测试（模块导入 + 版本断言 + HookspecMarker/HookimplMarker/
  PluginManager 注册 + hook 调用 + add_hookspecs + call_historic）✅
- R33: build() 使用 sys.executable，不依赖 shell 环境变量 ✅
