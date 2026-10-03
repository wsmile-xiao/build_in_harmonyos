# furo(任务号 2024.8.30 / 上游 2024.8.6)— HarmonyOS PC (aarch64) 适配笔记

## 任务

- 平台任务:`furo/2024.8.30`(自导入,开源鸿蒙PC专项积分赛-依赖 5 火种,分支 `feat/furo-2024.8.30`)
- **版本溯源**:任务号 2024.8.30 在上游无对应发布(furo 的 2024 线实际发布为 2024.8.6;
  2025 线为 2025.7.19/2025.9.25/2025.12.19)。与 libzippp 6.2 先例同型:目录/分支用任务号,
  基线取任务号所在时间线的上游真实版本 **2024.8.6**,溯源链(source url/sha256/notes)完整。
- 源:**官方 PyPI wheel** `furo-2024.8.6-py3-none-any.whl`(341,333 B,sha256 6cd97c58…14f5c)。
  不取 sdist:sdist 的 CSS/JS 是 src/ 下的 SCSS/JS 源,主题资产需 node/webpack 构建,
  OH 构建环境无 node 链;wheel 即上游构建产物(py3-none-any,85 文件:80 主题文件 + 5 dist-info)。

## 形态与验证

- **纯 Python/纯资产包,零编译**(Sphinx 文档主题:HTML 模板+CSS+少量 JS+`__init__.py`)。
  按 pari-seadata-big / agnostic-lizard 确立的**数据/源码包豁免模式**:
  `package_type=unknown`、`package_id()` 清空(noarch),`build()` 运行确定性校验器
  `verify_furo.py`——85 文件 size+sha256 钉死,MISSING/EXTRA/SIZE/SHA256 四类失败全列,
  本地实测 **85/85 byte-identical**。
- wheel 即 zip:`get()` sha256 校验下载 → `unzip()` 展开,不依赖 pip。

## 安装与消费

- 布局:`share/python/site-packages/furo/…` + `furo-2024.8.6.dist-info/`(Debian/PyPI 惯例)。
- 消费:Sphinx 通过 dist-info 的 entry point(`sphinx.html_themes`)发现主题;
  配方导出 `PYTHONPATH`(buildenv/runenv)与 `FURO_THEME_DIR`。
  使用:`conf.py` 里 `html_theme = "furo"`。
- 运行时依赖(仅在使用端):`sphinx>=6,<9`、`beautifulsoup4`、`sphinx-basic-ng`、`pygments`
  ——主题包本体不含这些依赖(wheel metadata 未声明运行时 requires,消费端负责),
  属平台 Python 生态前置任务,与本包互不阻塞。

## 版本号说明

目录/分支/conan 版本用任务号 `2024.8.30`(与 R40 分支名规则一致);源用上游 2024.8.6,
差异与溯源见 manifest.yaml 与本笔记。
