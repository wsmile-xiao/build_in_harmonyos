# E257 — init-build 嵌套源码提升误识别 Python sdist（docs/ 被当作源码根）

## 错误特征

init-build 解压后，`.work`/`.orig` 目录只包含 `docs/` 内容（Makefile、conf.py、
*.rst、api/ 等），看不到包本体（如 `chardet/`、`test.py`、`tests/`）。日志出现：

```
嵌套源码检测: 找到源码在 docs，正在提升到 chardet-5.2.0.work ...
```

后续 `cp -al`（硬链接复制 .work）还会报：

```
cp: chardet-5.2.0.work/LICENSE: Operation not permitted
```

## 触发条件

- 构建系统: custom（Python sdist，setuptools/hatch 等）
- 阶段: extract（init-build 嵌套源码提升 F068）
- 特征: sdist 顶层无 `configure`/`CMakeLists.txt`/`Makefile`/`meson.build`，
  但子目录 `docs/` 含 Sphinx 生成 Makefile

## 根因分析

`init_build._promote_nested_source()` 只按 C/C++ 构建标记识别源码子目录。
Python sdist 顶层没有这些标记，递归搜索浅层子目录时误命中含
Sphinx Makefile 的 `docs/`，把 docs/ 提升为源码根。另外 HMDFS 文件系统
禁止创建硬链接，`cp -al` 复制 .work 时必然失败。

## 解决方案

### 推荐方案

手动重新解压（与脚本逻辑一致，仅跳过错误的提升步骤）：

```bash
rm -rf chardet-5.2.0.work chardet-5.2.0.orig
mkdir -p chardet-5.2.0.orig
tar xzf chardet-5.2.0.tar.gz --strip-components=1 -C chardet-5.2.0.orig
sha256sum chardet-5.2.0.tar.gz | cut -d' ' -f1 > chardet-5.2.0.orig/.tarball-sha256
cp -a chardet-5.2.0.orig/. chardet-5.2.0.work/   # 勿用硬链接
rm -f chardet-5.2.0.work/.tarball-sha256
```

配方 build() 走 `pip install --prefix=staging` 路径，不依赖 init-build
的目录推断。

### 禁止做法

- ❌ 在 docs/ 内容上直接编译/打包（缺失包本体）
- ❌ 用 `cp -al`/`cp -l` 硬链接复制 .work（HMDFS 报 Operation not permitted）

## 验证

```bash
ls chardet-5.2.0.work/chardet/__init__.py
python3 -c "import sys; sys.path.insert(0,'chardet-5.2.0.work'); import chardet; print(chardet.__version__)"
```

## 关联条目

- 相关: E002（/tmp 只读）、HMDFS 软链接限制类条目
