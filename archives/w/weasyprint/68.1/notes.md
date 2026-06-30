# weasyprint 68.1 编译笔记

2026-05-28

## 编译环境
- 构建系统: pip (flit_core build backend)
- 编译日期: 2026-05-28
- 编译器: clang/clang++
- 状态: built (质量报告 FAIL，受限 HMDFS .so 加载限制)

## 编译步骤

weasyprint 是纯 Python pip 包，使用 `python3 -m pip install` 方式安装。

1. 初始化: `python3 ohc-run.py init-build weasyprint 68.1 --url=https://files.pythonhosted.org/packages/source/w/weasyprint/weasyprint-68.1.tar.gz`
2. 安装依赖: cffi 需要 ffi.h (来自 /data/service/hnp/libffi.org/libffi_3.4.4/)
3. pip 安装: `pip install weasyprint==68.1 --prefix=$DEFAULT_PREFIX --root=$TEST_PREFIX`
4. DESTDIR 模式: TEST_PREFIX 作为 staging 目录
5. 打包: `ohc-run.py package weasyprint 68.1`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | pip install 下载超时 (Pillow 47MB) | PyPI 网络慢 | 分批下载依赖；使用已构建的 tarball |
| 2 | cffi 编译失败: ffi.h not found | 缺少 libffi 开发头文件 | 设置 C_INCLUDE_PATH 包含 /data/service/hnp/libffi.org/libffi_3.4.4/include |
| 3 | _cffi_backend.so Permission denied | HMDFS 限制 dlopen() 加载 | **未解决**: HMDFS 上 /storage/Users/currentUser/ 目录中的 .so 无法被 dlopen() 加载 |
| 4 | PIL _imaging.so Permission denied | 同上 HMDFS 限制 | **未解决**: HMDFS 权限模型不支持从用户目录加载 .so |
| 5 | sign-elf 将 .so 权限改为 770 | sign-elf 用 shutil.move 替换文件，HMDFS 默认 770 | umask 022 cp 后仍为 770 (HMDFS 不支持 chmod) |

## 源码修改

无补丁文件（0 个补丁）

## 依赖版本

- cffi >= 0.6 (实际安装 1.17.1 / 2.0.0)
- Pillow >= 9.1.0 (实际安装 12.2.0)
- pydyf >= 0.11.0 (实际安装 0.12.1)
- tinycss2 >= 1.5.0 (实际安装 1.5.1)
- cssselect2 >= 0.8.0 (实际安装 0.9.0)
- tinyhtml5 >= 2.0.0b1 (实际安装 2.1.0)
- Pyphen >= 0.9.1 (实际安装 0.17.2)
- fonttools[woff] >= 4.59.2 (实际安装 4.59.2+)

## 验证结果

```bash
# 质量报告: FAIL
# G1 Binary Integrity: FAIL (weasyprint 是 Python 脚本, file 命令无法识别)
# G2 Functional: PASS (有警告)
# G3 Portability: PASS (有警告)
# G4 Archive: FAIL (manifest 缺少字段)

# HMDFS 限制: .so C 扩展无法加载
# PYTHONPATH=... python3 -c "import weasyprint" → ImportError: Permission denied (_cffi_backend.so)
# 系统 Python site-packages (/data/service/hnp/) 中的 .so 可以正常加载
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| weasyprint-68.1-ohos-aarch64.tar.gz | ~28 MB | 主包（含 weasyprint + 依赖 Python 包 + .so + external libs） |
| weasyprint-68.1-ohos-aarch64-debug.tar.gz | ~937 KB | 调试包 |

## 注意事项

1. **HMDFS 限制**: Python .so C 扩展模块（_cffi_backend, _imaging 等）无法从 `/storage/Users/currentUser/` 目录被 dlopen() 加载。这是 HMDFS 的安全策略，非权限或签名问题。
2. **未来解决方案**: 可能需要将 .so 文件安装到系统 Python site-packages (`/data/service/hnp/python.org/python_3.12/lib/python3.12/site-packages/`)，或修改 HMDFS 安全策略。
3. **pip install 超时**: PyPI 网络慢导致大包（Pillow 47MB）下载超时，需分批处理。
---

**编译结束**: 2026-05-28 21:23
**最终状态**: built
