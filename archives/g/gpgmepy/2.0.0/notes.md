# gpgmepy 2.0.0 适配笔记

## 编译环境
- 构建系统: setuptools (SWIG 生成扩展，绕过 autotools —— 本机无 automake/libtool)
- 编译日期: 2026-08-29
- 编译器: clang (OpenHarmony 工具链 /data/service/hnp/bin/clang)
- 状态: built

## 产品
- `gpg._gpgme` — SWIG 生成的 C 扩展（%module gpgme，.i 在源码根 gpgme.i）
- `gpg/` — 纯 Python 包（src/*.py，setup.py.in 用 packages=[...] 组包）
- 安装位置: `<pkg>/lib/python3.12/site-packages/gpg/`（含编译出的 `_gpgme*.so`）

## 构建步骤

1. 下载源码（conan create 自动，url/sha256 见 conandata.yml）
2. setup.py.in 占位符替换生成 setup.py：
   - `@VERSION@` = 2.0.0
   - `@GPGME_CFLAGS@` = `-I<gpgme pkg>/include`（E217: 打包 gpgme-config 不含自身 include）
   - `@GPGME_LIBS@` = `-L<gpgme pkg>/lib -lgpgme`
   - `@GPG_ERROR_CFLAGS@` = `-I<libgpg-error pkg>/include`
   - `@GPG_ERROR_LIBS@` = `-L<libgpg-error pkg>/lib -lgpg-error`
3. 复刻 autotools copystamp：gpgme.i/helpers.c/helpers.h/private.h 复制到构建 CWD，`gpg -> src` 符号链接
4. `<py pkg>/bin/python3.12 setup.py build`，环境：
   - PYTHONHOME/解释器 = conan python/3.12.9
   - PYTHONPATH = 本地解包的 setuptools-84.0.0 wheel（conan python 不带 setuptools）
   - PATH 前置 swig/4.4.1 包 bin；SWIG_LIB = swig 包 share/swig/4.4.1
   - CPP/LDFLAGS 含 Python include/lib、-lpython3.12、-fuse-ld=bfd
5. package(): 从 build/lib.*/gpg 拷 `*.py` + `*.so` 到 site-packages/gpg，
   然后 binary-sign-tool 自签 `_gpgme*.so`（E212: HMDFS 拒绝 dlopen 未签名 .so，
   conan copy 会抹掉签名，必须拷后重签）

## 依赖版本
- gpgme: 1.24.0
- libgpg-error: 1.55
- python: 3.12.9（构建+运行解释器）
- swig: 4.4.1（tool_requires）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| E001 | 无 automake/libtool，autogen.sh 无法跑 | OHOS PC 工具链只带基础工具 | 完全绕过 autotools，setup.py.in 手动替换 + setup.py build |
| E217 | setup.py 报 `gpgme.h not found` | 打包 gpgme-config --cflags 缺自身 include 目录 | 不依赖 gpgme-config，占位符直接填 conan 包路径 |
| E101 | `No such file or directory: 'gpgme.i'` | setup.py build 假设 in-tree 布局（autotools copystamp 产物） | 构建 CWD 复制 4 个文件 + gpg -> src 符号链接 |
| E102 | conan python 无 setuptools | python/3.12.9 recipe 不打包 setuptools | PYTHONPATH 挂本地解包的 setuptools-84.0.0 wheel，缺失时回退 pip |
| E212 | dlopen _gpgme*.so: Permission denied | HMDFS 拒绝加载未签名 .so；conan copy 抹掉签名 | package() 内 copy 后 llvm-objcopy 去旧签名 + binary-sign-tool 重签 |
| E201 | 测试环境无 gpg 运行时 | GnuPG 未发布到 ohpcd 制品仓 | 系统级 GnuPG 2.4.9 (~/tmp/gnupg-install)，GPG_BIN_DIR 可覆盖；readelf -d 取 NEEDED 库名后在 conan cache glob 拼 LD_LIBRARY_PATH |
| E202 | gpg-agent 无法启动: bind AF_UNIX EPERM | 本机 seccomp 过滤 AF_UNIX bind（socketpair 可用，path/abstract bind 全拒） | 平台级限制，非代码问题；依赖引擎的测试如实报 FAIL/ERROR |

## 测试
- 上游测试: 26 个 tests/t-*.py 本地实跑（`python tests/run-tests.py t-*.py --srcdir tests`，
  判据 0=PASS 77=SKIP 99=ERROR 其它=FAIL），需系统级 GnuPG 2.4.9 运行时（~/tmp/gnupg-install，
  非 conan 制品；gpgsm 另需 libksba）；通过率如实记于 PR body。
  上游测试树不随归档（参考 calceph 5.0.0 紧凑消费测试模式）。
- 已知平台限制: AF_UNIX bind 被拒 → gpg-agent 不启动 → 引擎类上游测试失败（输出如实保留，不掩盖）。
- 消费测试: test_package/test_gpgmepy.py——import gpg（_gpgme SWIG 扩展 dlopen，E212 签名）
  + 版本属性（__version__=2.0.0、gpgme.GPGME_VERSION）+ 核心 API（Context/Data、gpgme 模块
  属性、callbacks/results）+ gpg.Data 内存读写（5 断言；不启动 gpg 引擎，CI 自包含）。

## 交付物
| 文件 | 说明 |
|------|------|
| conanfile.py | recipe（build 绕过 autotools；package 装 site-packages/gpg 并签名） |
| conandata.yml | url + sha256 |
| manifest.yaml | 版本 manifest（status: built） |
| test_package/ | MANIFEST.yml + conanfile.py + test_gpgmepy.py（紧凑消费测试） |
