# acronym 2.0.0 适配笔记

## 编译环境
- 构建系统: python3 (pip wheel + installer)
- 编译日期: 2026-08-07
- 编译器: N/A（纯 Python 包）
- 状态: published
- 目标平台: HarmonyOS PC aarch64 (ohos-aarch64 profile)

## 编译步骤

纯 Python noarch 包，无 C/C++ 编译：

1. **下载源码**: PyPI sdist `acronym-2.0.0.tar.gz`（sha256 163cc163...bbf1）
2. **构建 wheel**:
   ```bash
   python3 -m pip wheel --no-deps -w .dist .
   # 产物: acronym-2.0.0-py3-none-any.whl
   ```
3. **安装到 staging**（conanfile.py 中）:
   ```bash
   python3 -m pip install --break-system-packages --no-deps \
     --prefix="$STAGING" "$SRC_DIR"
   ```
4. **打包**: 复制 site-packages 到 `lib/python3.12/site-packages`，console_scripts 到 `bin/`
5. **测试**: test_package 运行补全的 13 个单元测试

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | import 卡住/失败 | 上游模块顶层 `nltk.corpus.*.ensure_loaded()` 在语料缺失时自动联网下载，OHOS 受限网络下阻塞 import | 补丁 0001：改为惰性加载，`ensure_corpus()` 在 find_acronyms/main 中显式调用，缺失时抛清晰错误 |
| 2 | ohc conan-verify G2 报 `/bin/sh: syntax error: unexpected '('` | 工作目录路径含空格和括号 `build_in_harmonyos-main (1)`，`_run` 用 `/bin/sh -c` 执行字符串命令时括号被解析为子 shell 语法 | scripts/ohc/conan_verify.py G2 命令构造对 archive_dir 与 profile 路径加引号 |

## 源码修改

- `patches/0001-lazy-nltk-corpus-loading.patch`：移除 import 时的 NLTK 语料下载，新增 `ensure_corpus()`，在 `find_acronyms()` 与 `main()` 中调用。

## 依赖版本

| 依赖 | 版本 | 说明 |
|------|------|------|
| python3 | 3.12.9 | 鸿蒙已适配运行时 |
| numpy | 2.5.1 | C 扩展（本机已装） |
| pandas | 3.0.3 | C 扩展（本机已装） |
| nltk | 3.10.2 | 纯 Python |
| tqdm | 4.69.1 | 纯 Python |

## 验证结果

```bash
# 本地 conan 验证（ohc-run.py conan-verify）
G0 预构建风险: PASS
G1 配方完整性: PASS
G2 conan create（干净构建）: PASS
G3 系统同名库隔离: PASS
G4 产物完整性: PASS
L2 平台功能矩阵: PASS
L4 静态安全扫描: PASS
L5 产物基线对比: PASS
# 补全测试: 13/13 OK（Acronym Scoring System）
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | 纯 Python 包配方 |
| conandata.yml | PyPI sdist 源 + sha256 |
| patches/0001-lazy-nltk-corpus-loading.patch | NLTK 惰性加载补丁 |
| test_package/test_acronym.py | 路径 B 补全的 13 个单元测试 |
| test_package/MANIFEST.yml | 测试清单 |

## 注意事项

- 运行时依赖 numpy/pandas 为 C 扩展库，鸿蒙 aarch64 上如无预编译 wheel 需源码编译，属运行时环境问题，不影响本包 noarch 安装
- 路径 B：上游 sdist 无任何测试文件，本适配补全 13 个测试覆盖核心评分逻辑
