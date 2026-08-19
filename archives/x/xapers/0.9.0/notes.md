# xapers 0.9.0 适配笔记

## 编译环境
- 构建系统: setuptools (Python, 非 autotools；init-build 因 Makefile 误判为 autotools，已手动修正)
- 编译日期: 2026-08-09
- 编译器: clang 15.0.4 (用于 xapian-bindings 源码构建)
- Python: 3.12.9 (社区 cmd-pkgs)
- 状态: built

## 编译步骤
1. 源码: GitLab 官方归档 `https://gitlab.com/wpettersson/xapers/-/archive/0.9.0/xapers-0.9.0.tar.gz`
   (SHA256: 30f3ea0000d9fb063d7515e6f69e3092e054208c23e387448051a1b19c2a7b71)
2. xapers 为纯 Python 包 (setup.py + entry_points)，构建方式: `pip install --prefix=$TEST_PREFIX`（setuptools）
3. 运行依赖安装: `pip install pybtex pycurl urwid` (社区 PyPI 镜像)
4. xapian Python 绑定由 conan 依赖 `xapian-bindings/1.4.26`（已发布，含 xapian-core）提供；poppler 提供 pdftotext（PDF 文本提取）
5. 测试: `./test/xapers-test` (bash 测试套件, 4 组 83 用例) — **82 PASS + 1 预期失败（全部符合预期）**

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | xapian-bindings configure 报 config.status Permission denied | HMDFS umask 077 权限问题 (E011) | `sed -i 's/umask 077/umask 022/g' configure config.status` |
| 2 | xapian-bindings 链接失败 `-lstdc++` not found | OHOS SDK 无 libstdc++，只用 libc++ | Makefile 中 `-lstdc++` 改为 `-lc++`，并加 `-stdlib=libc++` |
| 3 | `_xapian.so` import 报 `PyThread_allocate_lock: symbol not found` | python3 主程序未导出 Python C API 符号 | `PYTHON3_LIBS` 追加 `-L$PREFIX/lib -lpython3.12` |
| 4 | xapian `WritableDatabase` 创建失败 `Opening UUID generator failed (Permission denied)` | OHOS 上 `/proc/sys/kernel/random/uuid` 无读权限 (USE_PROC_FOR_UUID) | 用仓库 xapian-core 配方补丁 0003-uuids-urandom-fallback.patch 重建 xapian-core（/proc 失败时回退 /dev/urandom） |
| 5 | 上游 version.py 仍为 0.8.2 | 上游 0.9.0 发布时未更新 version.py | 补丁 0003 修改 version.py → `__version__ = '0.9.0'` |
| 6 | setuptools 缺失 | 干净环境未安装 | `pip install setuptools` |
| 7 | 测试报 `'FileFinder' object has no attribute 'find_module'` | Python 3.12 移除 pkgutil loader.find_module | 补丁 0002: source.py 改用 `importlib.util.find_spec` + `module_from_spec` + `exec_module` |
| 8 | 测试报 `No such file or directory: 'pdftotext'` | 环境缺 poppler-utils pdftotext；且 OHOS 上 Python posix_spawn 不搜索 PATH（bare-name 命令全失败） | 安装 poppler 25.12.0.2 预编译包 (含 pdftotext)；补丁 0001: pdf.py 用 `shutil.which('pdftotext')` 解析完整路径 |

## 源码修改（3 个补丁）
1. `xapers/parsers/pdf.py`: `shutil.which('pdftotext')` 解析完整路径（OHOS posix_spawn 不搜 PATH）
2. `xapers/source.py`: `find_module` → `importlib.util.find_spec`（Python 3.12 兼容）
3. `xapers/version.py`: `__version__` 0.8.2 → 0.9.0（上游 0.9.0 发布未更新版本号）

## 依赖版本
- xapian-bindings 1.4.26（制品仓 ohpcd 已发布，含 xapian-core/1.4.26）
- poppler 25.12.0.2（制品仓 ohpcd 已发布，提供 pdftotext 供测试）
- xclip 0.13.1（制品仓 ohpcd 已发布，交互式 UI 剪贴板复制）
- pybtex 0.26.1 / pycurl 7.45.6 / urwid 4.0.8 (pip, 社区镜像)

## 验证结果
```bash
# conan create (干净构建, 应用 3 个补丁, 依赖已发布的 xapian-bindings/poppler/xclip)
conan create ... # PASS (G1-G4 + L2/L4/L5)
# 上游测试套件 (bash, 4 组 83 用例)
./test/xapers-test   # ✅ 82 PASS + 1 预期失败（All 83 tests behaved as expected）
# 冒烟: xapers --version → xapers 0.9.0 (补丁后)
```

## 注意事项
- xapers 是命令行工具 (console_scripts: `xapers`)，已创建软件级 `commands.json` (R38)
- xapian Python 绑定由 conan 依赖 xapian-bindings/1.4.26 提供（配方 requirements 声明，runenv PYTHONPATH 注入）
- OHOS 平台注意：Python subprocess 默认 posix_spawn 不搜索 PATH，外部命令调用需完整路径（补丁 0001）
- 测试套件需 pdftotext (poppler)，配方已声明 poppler/25.12.0.2 依赖
- 配方为 Python 项目类型 (非 autotools)，参照 internetarchive 既有配方
---

**编译结束**: 2026-08-19 01:30
**最终状态**: built
