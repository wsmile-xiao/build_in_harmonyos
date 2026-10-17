# krep 3.0.0 适配笔记

## 编译环境
- 构建系统: makefile
- 编译日期: 2026-07-14
- 编译器: clang/clang++
- 状态: built

## 编译步骤
1. `init-build` 下载并解压 krep 3.0.0 源码，生成归档骨架。
2. 使用 clang 和通用 C11/pthread/fPIC 参数构建：
   `make CC=clang CFLAGS='-Wall -Wextra -O3 -std=c11 -pthread -D_GNU_SOURCE -D_DEFAULT_SOURCE -fPIC' LDFLAGS='-pthread'`
3. 执行上游测试：`make test`、`make test-directory`、`make test-cli`。
4. 生成补丁并编写 Conan 2.x 配方、conandata.yml、test_package/conanfile.py、test_package/test.sh、MANIFEST.yml。
5. 通过 `conan create` / `ohc-run.py conan-verify` / `finish` 的 G0 与 W3 本地 CI 模拟进行配方自包含构建验证。

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `REG_STARTEND` 未定义导致编译失败 | `REG_STARTEND` 是 GNU regex 扩展，OHOS/musl 不支持 | 在 `krep.c` 中用 `#ifdef REG_STARTEND` 条件保护 |
| 2 | `make install` 失败：`install: No such file or directory` | OHOS 环境缺少 coreutils `install` 工具 | Makefile 安装规则改用 `mkdir -p`、`cp`、`chmod` |
| 3 | G0 clean-verify 默认执行 `./configure`，plain Makefile 项目无 configure | clean-verify 兼容旧 autotools 流程 | 增加 no-op `configure` shim，仅用于兼容 clean-verify |
| 4 | G0 clean-verify `make` 调用未传入 CC，默认 `gcc` 不存在 | 上游 Makefile 用 `CC = gcc` 覆盖环境 | 改为 `CC ?= gcc`、`CFLAGS ?=`、`LDFLAGS ?=`，允许环境变量覆盖 |
| 5 | 多线程测试创建临时文件失败：`/tmp` 只读 | 上游测试硬编码 `/tmp` | 测试改为尊重 `TMPDIR` 或使用当前工作目录 |
| 6 | 初次 HTTPS 下载证书校验失败 | 环境 CA 证书缺失/过期 | 由环境检查安装 CA 证书；手动缓存 tarball 后继续初始化 |

## 源码修改
- `0001-Makefile.patch`: 允许环境覆盖 CC/CFLAGS/LDFLAGS，并将安装规则从 `install` 替换为 `mkdir/cp/chmod`。
- `0002-configure.patch`: 新增 no-op `configure` shim，用于 clean-verify 兼容 plain Makefile 项目。
- `0003-krep.c.patch`: 对 GNU `REG_STARTEND` 添加条件编译保护。
- `0004-test-test_directory.c.patch`: 目录测试避免硬编码 `/tmp`。
- `0005-test-test_krep.c.patch`: 多线程测试临时文件路径使用 `TMPDIR`。

## 依赖版本
- clang 15.0.4
- make 4.4.1
- conan 2.29.1
- pthread / POSIX regex: 系统库

## 验证结果
```bash
make test                       # 169 passed, 0 failed
make test-directory             # 10 passed, 0 failed
make test-cli                   # krep CLI v3 integration tests passed
python3 scripts/ohc-run.py conan-verify krep 3.0.0  # PASS
python3 scripts/ohc-run.py finish krep 3.0.0 built  # G0 PASS, W3 本地 CI PASS；legacy packaging 预检 WARN
```

## 注意事项
- krep 是纯可执行 Conan 包，无 lib/include 输出。
- `conandata.yml` 未将 `0002-configure.patch` 纳入 Conan patch 列表；该补丁仅用于 ohc clean-verify 兼容，不参与 Conan build。
- finish 的 step8 仍提示缺少 legacy `packaging/*.tar.gz`，但 Conan 配方体系的 CI 输入与验证已完整。

---

**编译结束**: 2026-07-14 23:21
**最终状态**: built
