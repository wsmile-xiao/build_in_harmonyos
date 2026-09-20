# binwalk 2.3.4 适配笔记

## 编译环境
- 构建系统: Python (setuptools)
- 编译日期: 2026-09-18
- 编译器: 无需编译器（纯 Python 项目）
- 状态: built

## 编译步骤

1. 源码获取：官方 GitHub v2.3.4 tarball（sha256 已校验）
2. 应用 3 个补丁（imp→importlib ×2 + extractor 平台修复）
3. setuptools 私有安装（系统 Python 无 setuptools）:
   ```bash
   python3 -m pip install --no-deps --target "$BUILD_DIR/pydeps" setuptools
   ```
4. 构建 + 安装到 Conan 包目录（私有 prefix，不污染系统 site-packages，R49）:
   ```bash
   PYTHONPATH="$BUILD_DIR/pydeps" python3 setup.py build
   PYTHONPATH="$BUILD_DIR/pydeps" python3 setup.py install --no-compile --prefix="$PACKAGE_DIR"
   ```
5. package_info 通过扫描 lib/pythonX.Y/site-packages 设置 PYTHONPATH（不硬编码解释器版本）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | binwalk v3 (Rust版本) 无法编译 | Rust 工具链依赖 glibc 动态链接器，鸿蒙使用 musl | 使用 binwalk v2.3.4 (Python版本) 替代 |
| 2 | Python 3.12 不支持 `imp` 模块 | `imp` 模块在 Python 3.12 已移除 | 补丁 0001/0002：使用 importlib.util 替代 |
| 3 | pip 命令不可用 | pip 未安装为独立命令 | 使用 `python3 -m pip` 替代 |
| 4 | 系统 Python 无 setuptools | HNP 打包的 Python 3.12 未携带 setuptools | `pip install --target` 安装到构建目录私有 prefix，经 PYTHONPATH 注入 |
| 5 | `binwalk -e` 提取功能崩溃：Failed to load Extractor module | OHOS 上当前 uid 不在 passwd 数据库，`pwd.getpwuid()` 抛 KeyError | 补丁 0003：KeyError 时回退到进程凭据 (os.getuid/os.getgid) |
| 6 | 提取时外部工具 (tar 等) 找不到：FileNotFoundError | OHOS 捆绑 Python 的 subprocess 对裸命令名不走 PATH 搜索（posix_spawn 未用 p 变体） | 补丁 0003：shell_call 中先 `shutil.which()` 解析为绝对路径 |

## 源码修改

- `src/binwalk/core/module.py`（补丁 0001）: `import imp` → `import importlib.util`，`imp.load_source()` → `spec_from_file_location()` + `module_from_spec()` + `exec_module()`
- `src/binwalk/core/plugin.py`（补丁 0002）: 同上修改
- `src/binwalk/modules/extractor.py`（补丁 0003）:
  - `load()`: `pwd.getpwuid()` 增加 KeyError 回退（OHOS 无该 uid 的 passwd 条目）；root 检查改用 `os.getuid()`
  - `shell_call()`: 裸命令名先经 `shutil.which()` 解析为绝对路径（OHOS Python 的 subprocess 限制）

## 依赖版本

- Python 3.12.9（系统自带，CI worker 与本机一致）
- setuptools 84.x（构建期经 pip --target 私有安装）
- 无其他编译依赖

## 验证结果

### test_package 冒烟测试（conan create 内执行）
```bash
$ python3 -c "import binwalk; print(binwalk.__version__)"
2.3.3
$ binwalk --help
Binwalk v2.3.3
Craig Heffner, ReFirmLabs
https://github.com/ReFirmLabs/binwalk

Usage: binwalk [OPTIONS] [FILE1] [FILE2] [FILE3] ...
```

### 实际功能验证
```bash
$ binwalk v2.3.4.tar.gz
DECIMAL       HEXADECIMAL     DESCRIPTION
--------------------------------------------------------------------------------
0             0x0             gzip compressed data, from Unix, last modified: 1970-01-01 00:00:00 (null date)

$ binwalk -e firmware.gzip   # 提取链路（补丁 0003 修复后可用）
→ 生成 _firmware.gzip.extracted/0.gz
```

### 上游测试（R51 三步法）
上游测试套件位于 `testing/tests/`（nose 风格，共 7 个用例）。nose 在 Python 3.12
上已死（自身依赖被移除的 imp 模块），故用 pytest 9 + 10 行 nose.tools 兼容 shim 运行：

| 用例 | 结果 |
|------|------|
| test_dirtraversal.py | PASS（补丁 0003 后；含 tar 外部工具调用与符号链接消毒验证） |
| test_firmware_cpio.py | PASS |
| test_firmware_gzip.py | PASS |
| test_firmware_jffs2.py | PASS |
| test_firmware_squashfs.py | PASS |
| test_firmware_zip.py | FAIL：4 != 2。上游期望值与自带 magic 库不符（嵌套 zip local file header 也会命中 PK\003\004 签名）；纯字节匹配行为，与平台无关，属上游测试用例陈旧 |
| test_lzma.py | PASS |

**实测 6/7 通过**。唯一失败项 test_firmware_zip 为上游固有（同版 magic 库在任何平台均报 4 个结果），非鸿蒙适配缺陷。

## 交付物

| 文件 | 说明 |
|------|------|
| bin/binwalk | setuptools 生成的入口脚本（shebang 指向构建期 python3 绝对路径） |
| lib/python3.12/site-packages/binwalk | Python 模块 + magic 签名库 |

## 注意事项

1. binwalk 是纯 Python 项目，无需 C/C++ 编译
2. 需要修改源码以兼容 Python 3.12（imp 模块已移除）—— 补丁 0001/0002
3. 提取功能依赖外部工具（tar/cpio/unzip/lzma 等），OHOS worker PATH 需包含 /system/bin（默认满足）；裸命令名解析限制由补丁 0003 规避
4. v3 (Rust版本) 在鸿蒙上无法编译，需要使用 v2 (Python版本)
5. 上游 setup.py 的 MODULE_VERSION 硬编码为 2.3.3（上游标签自身的怪癖），`binwalk --help` 报 2.3.3 属正常现象
---

**编译结束**: 2026-09-18 18:00
**最终状态**: built
