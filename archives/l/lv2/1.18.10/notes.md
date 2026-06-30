# lv2 1.18.10 适配笔记

## 编译环境
- 构建系统: meson
- 编译日期: 2026-05-29
- 编译器: clang/clang++ (clang 15.0.4)
- 状态: built

## 编译步骤

1. 初始化: `python3 $SKILL_ROOT/scripts/ohc-run.py init-build lv2 1.18.10 --url=https://github.com/lv2/lv2/archive/refs/tags/v1.18.10.tar.gz`
2. 安装测试依赖: `python3 -m pip install rdflib` (lv2 spec 测试需要 rdflib)
3. meson 配置: `meson setup builddir --prefix=$DEFAULT_PREFIX -Ddocs=disabled -Dplugins=disabled`
4. 编译: `ninja -C builddir -j2`
5. 安装 (DESTDIR模式): `DESTDIR=$TEST_PREFIX ninja -C builddir install`
6. 测试: `ninja -C builddir test` (28/28 全部通过)
7. 打包: `python3 $SKILL_ROOT/scripts/ohc-run.py package lv2 1.18.10`
8. 收尾: `python3 $SKILL_ROOT/scripts/ohc-run.py finish lv2 1.18.10 built`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | spec 测试需要 rdflib | lv2 规范检查依赖 rdflib Python模块 | pip install rdflib |
| 2 | docs 和 plugins 依赖较多可选组件 | 本平台无 doxygen/serdi/sord_validate | -Ddocs=disabled -Dplugins=disabled |

## 源码修改

无源码修改，不需要补丁。

## 依赖版本

- meson 1.11.1
- ninja 1.13.1
- clang 15.0.4
- rdflib 7.6.0 (Python 模块，用于 spec 测试)

## 验证结果

```bash
ninja -C builddir test
# 28/28 全部通过 (OK)
# spec 测试 (16 个) + build 测试 (2 个) + unit 测试 (2 个)
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| lv2-1.18.10-ohos-aarch64.tar.gz | ~xxx KB | 预编译包 (headers + LV2 bundles + pkg-config + lv2_validate) |
| lv2-1.18.10-ohos-aarch64-debug.tar.gz | ~xxx KB | debug 预编译包 |

## 注意事项

- lv2 是 header-only 库 + 规范数据 + 工具，无共享库/静态库产物
- docs 和 plugins 禁用不影响核心功能
- lv2_validate 工具依赖 Python rdflib 模块
---

**编译结束**: 2026-05-29 10:39
**最终状态**: built
