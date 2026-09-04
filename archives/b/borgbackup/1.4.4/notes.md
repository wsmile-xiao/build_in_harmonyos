# borgbackup 1.4.4 适配笔记

## 编译环境
- 构建系统: Python setuptools (Cython C extensions)
- 编译日期: 2026-06-03
- 编译器: clang 15.0.4
- Python: 3.14.5
- 状态: built

## 编译步骤
1. 下载源码: borgbackup-1.4.4.tar.gz from PyPI
2. 安装 Python 依赖: pip3 install msgpack Cython pkgconfig packaging setuptools_scm
3. 创建 stub ACL headers (OpenHarmony 没有 libacl)
4. 修改 setup.py:
   - 禁用 Cython 并行编译 (multiprocessing forkserver 在 OHOS 上不工作)
   - 使 libacl 成为可选依赖
   - 添加 stub ACL include 目录
5. 构建扩展: python3 setup.py build_ext
6. 安装: python3 setup.py install --prefix=$DEFAULT_PREFIX --root=$TEST_PREFIX
7. 验证: borg --version → 1.4.4

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Cython multiprocessing forkserver 崥溃 | OHOS/musl forkserver 不工作 | 禁用 nthreads (并行 cythonize) |
| 2 | libacl 缺失 | OpenHarmony 无 POSIX ACL 库 | 创建 stub headers + 使 libacl 可选 |
| 3 | pip wheel build 头 /lib/ld-musl 权限错误 | OHOS /lib 只读 | 用 setup.py install 替代 pip |
| 4 | Python SSL import 失败 | LD_LIBRARY_PATH 不包含 harmonybrew openssl | 设置 LD_LIBRARY_PATH 包含 harmonybrew lib |
| 5 | init-build 提取 docs 子目录 | 嵌套检测误判 docs 为源码 | 手动提取 borgbackup-1.4.4 根目录 |

## 源码修改
- setup.py: 緻加 optional 参数给 lib_ext_kwargs，禁用 nthreads，添加 stub_acl include_dirs
- 新增 stub_acl/sys/acl.h 和 stub_acl/acl/libacl.h

## 依赖版本
- Python 3.14.5
- OpenSSL 3.6.2 (harmonybrew) + 1.1.1w (usr/local)
- liblz4 1.10.0 (harmonybrew)
- libzstd 1.5.6 (harmonybrew)
- libxxhash 0.8.2 (usr/local)
- msgpack 1.1.2
- Cython 3.2.5
- pkgconfig 1.6.0

## 验证结果
```bash
$ borg --version
borg 1.4.4
```

## 交付物
- borgbackup-1.4.4-r0-ohos-aarch64.tar.gz (待创建)
- bin/borg, bin/borgfs (脚本)
- lib/python3.14/site-packages/borg/ (Python包+C扩展.so)

## 注意事项
- OpenHarmony 上没有 libacl，ACL 功能不可用
- Python .so 模块需要 ELF 签名才能加载
- borgfs 是 borg 的符号链接/包装脚本
---

**编译结束**: 2026-08-05 11:32
**最终状态**: built

**Conan adaptation complete**: 2026-08-27
