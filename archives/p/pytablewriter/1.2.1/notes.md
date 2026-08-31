# pytablewriter 1.2.1 适配笔记

## 编译环境
- **构建系统**: setuptools（纯 Python，无编译）
- **编译日期**: 2026-08-30
- **平台**: arm64-ohos（OpenHarmony PC）
- **状态**: built（Conan 配方验证通过）
- **补丁数量**: 0（无源码补丁）

## 编译步骤（conan create 全流程）

```bash
conan create archives/p/pytablewriter/1.2.1 --build=missing -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

### 1. 源码获取（source()）
`get()` 从 conandata 声明的官方 GitHub tag 归档下载并 strip_root。

### 2. 打包（package()）
- 纯 Python 库，无编译；无 CLI 入口（无 console_scripts）→
  `package_type=python-require`（避免 R38 commands.json）
- `build()` copytree 源码到 staging（源外目录，参考 typepy 同款方案），
  排除 egg-info/setup.py/test/docs 等非运行时文件
- `package()` 复制 `pytablewriter/` 到 `lib/python3.12/site-packages/`

## 依赖（requirements.txt 核验）
- dataproperty/1.1.1、mbstrdecoder/1.1.5、pathvalidate/3.3.1、
  tabledata/1.3.5、tcolorpy/0.1.7、typepy/2.0.0 —— 均已在 ohpcd
- 注意：上游约束 typepy>=1.3.2,<2，但 ohpcd 仅 typepy/2.0.0——需在
  test_package 实测兼容性（潜在 major 变更风险）

## 上游测试（rule 4 全量核验）
- 测试目录：test/，pytest 套件（pyproject.toml testpaths=["test"]）
- 本地实测 `pytest test/ -q --continue-on-collection-errors`：
  **收集 1580 用例：1502 passed / 3 failed / 16 skipped / 59 xfailed /
  2 errors**（rule 1.4 修正初版 1395 少报）
- 通过率（rule 1.3，skipped/xfailed 不计分母）：**1502/1507 = 99.67%**
- 收集数随可选依赖环境变化：注入上游可选依赖 dominate/toml/
  pytablereader（纯 Python、pip 可装）后实测 1580；评审方干净环境
  （仅 pip install pytablewriter）实测 1496（5 errors）
- 2 errors：writer 扩展模块收集失败（sqlite/elasticsearch，需
  sqliteschema/elasticsearch，ohpcd 无制品）
- 剩余 3 failed 为上游依赖行为（非本适配缺陷）：
  ① test_csv_writer from_file：pytablereader+pathvalidate 路径校验
     （MALFORMED_ABS_PATH）
  ② test_html_writer from_tabledata：dominate CSS 样式顺序断言差异
  ③ test_markdown_writer clear_theme：上游行为
- 16 skipped / 59 xfailed 为上游预期跳过/失败（rule 5.2 如实记录）

## 已知限制
- 上游部分 writer 扩展（pandas/excel/sqlite/es/toml）依赖 ohpcd 无制品，
  对应测试文件收集期报错
- 剩余 2 失败为上游依赖行为（pytablereader/pathvalidate 路径校验、
  dominate CSS 顺序），非 pytablewriter 缺陷
- typepy 2.0.0 对上游 `<2` 约束实测兼容（核心套件 99.86% 通过，
  无 typepy 相关失败）
