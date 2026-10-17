# chardet 5.2.0 适配笔记

## 编译环境
- 构建系统: custom（纯 Python，无 C/C++ 编译）
- 编译日期: 2026-08-28
- 编译器: clang/clang++（不参与 Python 包构建）
- 状态: published

## 编译步骤

1. init-build 下载 PyPI sdist 并解压（嵌套源码提升误识别 docs/，手动 tar --strip-components=1 重新解压）
2. conanfile.py: pip install setuptools/wheel/pytest → pip install --no-deps --prefix=staging
3. build() 内实跑上游测试: PYTHONPATH=staging python -m pytest test.py -q
4. package(): 复制 staging site-packages 与 bin/chardetect
5. conan-verify 全门禁通过（G0-G4 + L2/L4/L5）→ finish published

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 解压后 .work 只有 docs/ 内容 | _promote_nested_source 仅认 C/C++ 构建标记，Python sdist 误命中含 Sphinx Makefile 的 docs/ | 手动 tar xzf --strip-components=1 解压 .orig，cp -a 复制 .work（HMDFS 禁硬链接）→ 沉淀知识草稿 E257 |
| 2 | conan-verify G1 失败 | 配方缺 export_sources() 与 apply_conandata_patches 调用 | 按 6.0.0 先例补全（patches: {} 时为空操作） |

## 源码修改

无（纯 Python sdist 原样打包，零补丁）

## 依赖版本

- 运行时依赖: 无（PyPI requires_dist 核验为零依赖）
- 构建期: setuptools/wheel/pytest（pip 安装）

## 验证结果

```bash
python3 -m pytest test.py -q   # 上游测试实跑: 754 passed, 10 xfailed, 0 failed (45.68s)
python3 test_chardet.py        # 消费者测试: OK: chardet 5.2.0 (detect ok, version check)
conan create ...               # 完整构建通过（G2），包内产物齐全
```

## 注意事项

- chardet 5.2.0 为纯 Python 包（LGPL-2.1），sdist 顶层 chardet/ 目录布局（区别于 7.6.0 的 src/chardet/）
- 上游 10 个 xfail 为 test.py EXPECTED_FAILURES 显式标记（5 文件 × 2 函数），属预期行为
- 2 个 hypothesis 属性测试依赖 hypothesis 库未安装，未收集（如实分类）
---

**编译结束**: 2026-08-28 23:25
**最终状态**: published
