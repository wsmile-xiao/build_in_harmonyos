# rich 15.0.0 适配笔记

## 编译环境
- **类型**: 纯 Python noarch（无 C/C++ 编译）
- **编译日期**: 2026-08-28
- **平台**: OHOS PC（arm64）
- **状态**: built

## 编译步骤（conan create 全流程）

```bash
conan create archives/r/rich/15.0.0 --build=missing
```

### 1. 源码获取（source()）
`get()` 下载 PyPI sdist（rich-15.0.0.tar.gz，230KB），`strip_root=True` 解压。

### 2. 安装（build()）
无需 pip 构建——直接拷贝源码 `rich/` 模块到包内（同 python-magic：环境
setuptools egg_info 加载 entry point 报 pbr 缺失实测，绕过）。

### 3. 打包（package()）
`shutil.copytree` 拷贝 `rich/` 模块（含 `_unicode_data/` 子包 + `_emoji_codes.py`
等数据文件）到 `lib/pythonX.Y/site-packages/rich`。

### 4. package_info()
`env_info.PYTHONPATH` 注入 site-packages——消费者 `import rich` 可用。

## 依赖处理

- **pygments/2.20.0**（ohpcd 已发布）：`rich.syntax.Syntax` 语法高亮核心——
  配方 `requires = "pygments/2.20.0"`
- **markdown-it-py**（ohpcd 未发布）：仅 `rich.markdown.Markdown` 渲染用——
  最小依赖集未纳入（可选，消费时按需补）

## 上游测试（build() 集成——rule 4 实测回填）

- **sdist 不含 test/**（纯 Python 包：rich/ + pyproject.toml + LICENSE + README）
- 上游测试在 GitHub `tests/` 目录（pytest 套件 68 条目）——配方 build() 从
  GitHub v15.0.0 tag 下载 tests/ 并运行 pytest，实测回填：
- **实测结果：956 passed / 0 failed / 25 skipped（981 collected）**
  - **通过率口径：956/981 = 97.45%**（skipped 计入分母——25 个跳过为上游
    标记，非本库缺陷，原因见下）
  - 初测 955/981：test_brokenpipeerror 失败——OHOS 沙箱 posix_spawn 不按
    PATH 搜索相对名（shutil.which 能定位 /system/bin/which 但 subprocess
    相对名 FileNotFoundError 实测——python3/ls 相对名同样失败）
  - **修复**：写 sitecustomize.py 强制 `subprocess._USE_POSIX_SPAWN = False`
    （Python 启动自动加载）——subprocess 走 execvp 标准 PATH 搜索——
    test_brokenpipeerror 通过，956 个可运行用例全部通过
- **25 个 skipped 原因分类（pytest -rs 实测）**：
  | 数量 | 测试文件 | 跳过原因（上游标记） |
  |------|---------|---------------------|
  | 17 | test_windows_renderer.py | `windows only`——Windows 平台专属测试（OHOS 为 Linux 系，不适用） |
  | 2 | test_tree.py | `Windows specific`——同上 |
  | 4 | test_inspect.py | `rendered differently on py3.12`——repr 渲染在 Python 3.12 有差异，上游主动跳过 |
  | 1 | test_pretty.py | `rendered differently on py3.12`——同上 |
  | 1 | test_traceback.py | `Not applicable after Python 3.11`——Python 3.11+ 不适用，上游标记 |
  | **25** | | **19 个 Windows 专属 + 6 个 Python 版本相关（上游标记跳过）** |
- 注意：PYTHONPATH 须指源码根而非 rich/ 子目录（rich 自带 traceback.py
  会遮蔽标准库 traceback——循环导入实测）

## 验证结果
- **构建**: `rich/15.0.0: Package created`
- **上游测试**: 实测 **956/981 通过（97.45%）**——956 passed / 0 failed / 25 skipped（skipped 计入分母，25 个跳过均为上游标记：19 个 Windows 专属 + 6 个 Python 版本差异）——build() 集成回填（rule 4）
- **R34 消费者验证**: import rich + 真实调用（Console 输出、Table、Syntax 高亮）
