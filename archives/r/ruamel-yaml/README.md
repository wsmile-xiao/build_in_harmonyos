# ruamel.yaml

ruamel.yaml 是 YAML 1.2 解析器/生成器（纯 Python），核心特性为 roundtrip 模式保留注释、锚点/别名与原始格式，是 awscli 依赖链 L1。

## 基本信息

- **名称**: ruamel-yaml
- **版本**: 0.19.1
- **许可证**: MIT
- **官方网站**: https://sourceforge.net/p/ruamel-yaml/
- **构建系统**: python（零编译，源码直装 site-packages）

## HarmonyOS 编译状态

| 版本 | 状态 | 编译日期 | 备注 |
|------|------|---------|------|
| 0.19.1 | ✅ built | 2026-09-01 | 纯 Python 命名空间包，零必需依赖 |

## 构建配置

- **构建系统**: python（copytree 源码 → staging → 平铺为 `ruamel/yaml/` 命名空间包）
- **编译器**: 无（纯 Python）
- **目标三元组**: aarch64-unknown-linux-ohos

## 依赖

- 无必需依赖（clib/clibz 仅 `extra=oldlibyaml/libyaml` 可选 C 加速，默认不启用）

## 安装

```bash
# conan 消费（ohos-aarch64 profile）
conan install --requires=ruamel-yaml/0.19.1 -pr:h=ci/conan/profiles/ohos-aarch64 --build=ruamel-yaml/*
```

## 编译笔记

详见 [0.19.1/notes.md](0.19.1/notes.md)。

## 知识沉淀

1. **sdist 无测试**: PyPI tar.gz 实测不含 `_test/`——上游测试需从 git 仓库（SourceForge git / GitHub 镜像 pycontribs/ruamel-yaml）获取
2. **命名空间包布局**: pip 实测布局为 `ruamel/yaml/` + 空 `ruamel/__init__.py`，package() 按此复制
3. **平台包装层**: HarmonyOS 对 `os.system` 有 `_harmonyos_compat` 包装——依赖其类型名的上游测试按平台行为差异分类

## 注意事项

1. `build()` 上游测试下载 GitHub 镜像 tarball 失败时不阻断构建（warning 透传）
2. 上游 test_cyaml 3 用例在纯 Python 运行时按设计失败（clib 可选 extra 未装）
