# python-magic 0.4.27 适配笔记

## 编译环境
- **类型**: 纯 Python noarch（无 C/C++ 编译）
- **编译日期**: 2026-08-28
- **平台**: OHOS PC（arm64）
- **状态**: built

## 编译步骤（conan create 全流程）

```bash
conan create archives/p/python-magic/0.4.27 --build=missing
```

### 1. 源码获取（source()）
`get()` 下载 PyPI sdist（python-magic-0.4.27.tar.gz），`strip_root=True` 解压。

### 2. 安装（build()）
```bash
pip install --break-system-packages --no-deps --prefix=<staging> <src>
```
- 需先 `pip install setuptools wheel`（构建依赖）
- 纯 Python 包——安装产物在 `staging/lib/pythonX.Y/site-packages/magic/`

### 3. 打包（package()）
`lib/pythonX.Y/site-packages` 整体拷入包内（`magic/` 模块 + `py.typed`）。

### 4. package_info()
`env_info.PYTHONPATH` 注入 site-packages——消费者 `import magic` 可用。

## 关键攻坚点（运行时依赖 libmagic）

- `magic/loader.py` Linux 分支：`ctypes.CDLL('libmagic.so.1')` 加载
- **libmagic 来源**：`file/5.48.1` Conan 包（提供 libmagic.so.1）——配方 `requires = "file/5.48.1"`
- 消费验证需 file 包在运行时依赖链（test_package 检查 libmagic 可加载 + 真实识别）

## 上游测试

- sdist **无 test/ 目录**（纯 Python 包 18 文件）——上游测试在 GitHub `test/`
  目录（python_magic_test.py 17 + libmagic_test.py 3 = 20 用例）
- **实测（rule 4 回填）**：build() 从 GitHub 0.4.27 tag 下载 test/ 跑 unittest——
  **12 passed / 6 failed / 2 skipped（20 用例 = 60%，分母=全部用例）**
- 运行前提（缺依赖就装上，本地实测可行）：
  1. **libmagic.so.1**：file 包按 R26 只出静态库（libmagic.a）——build() 用
     `clang -shared --whole-archive` 构建 libmagic.so.1（C 层 magic_open/
     magic_load 实测可用）
  2. **sys.platform**：OHOS Python 报 `'ohos'`，python-magic 的 loader 只在
     `sys.platform == 'linux'` 时 yield `libmagic.so.1`（加载失败实测）——
     sitecustomize.py 强制 `sys.platform = 'linux'`
  3. **magic 数据库**：magic.mgc 拷贝到 `~/.magic.mgc`（libmagic 默认数据库
     路径——否则 magic_load(NULL) core dump 实测）
  4. **LD_LIBRARY_PATH** 指向 libmagic.so.1 目录 + LC_ALL=en_US.UTF-8 +
     TMPDIR=/data/storage/el2/base/cache（沙箱 /tmp 只读）
- 6 failed：libmagic 5.48.1 输出与上游测试期望（基于旧版 libmagic 编写）的
  **版本差异**（两轮提升尝试后确认，逐用例分类）：
  1. `test_detect_from_content/filename/fobj`（3 个）：PDF 描述输出
     `'PDF document, version 1.2, 2 page(s)'` vs 上游期望 `'2 pages'`
     （单复数格式差异）
  2. `test_mime_types`：parquet 被 libmagic 5.48.1 更准确识别为
     `'application/vnd.apache.parquet'` vs 上游旧期望 `'application/octet-stream'`
  3. `test_extension`：gzip 扩展名列表更长
     `'gz/tgz/tpz/zabw/svgz/adz/kmy/xcfgz'` vs 上游旧期望
     `'gz/tgz/tpz/zabw/svgz'`（adz/kmy/xcfgz 为 5.48 新增）
  4. `test_descriptions`：parquet 描述 `'Apache Parquet file'` vs 上游期望
     `'Apache Parquet'`（后缀差异）
  → 均为 libmagic 数据库输出随版本演进，非 OHOS 环境可修项（修改上游测试
  期望违反 rule 4）——如实记录
- 2 skipped：上游标记（SKIP_FROM_DESCRIPTOR——magic_descriptor 在此版本
  libmagic 不可靠）

## 验证结果
- **构建**: `python-magic/0.4.27: Package created`
- **上游测试**: 实测 **12/20 通过（60%）**——build() 集成 unittest（rule 4，
  分母=全部 20 用例），6 failed 为 libmagic 5.48 输出格式差异、2 skipped 上游标记
- **R34 消费者验证**: import magic + `magic.from_buffer(b'...')` 真实识别
  （1/1 = 100%；libmagic.so.1 不可加载时精确匹配 `failed to find libmagic`
  签名如实 WARN——不伪造通过）
