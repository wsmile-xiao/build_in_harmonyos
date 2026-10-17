# csh 20240808 适配笔记

## 软件与来源

- 软件：csh（Berkeley C shell）
- 上游来源：Debian 官方源码镜像中的 OpenBSD 派生源代码
- URL：`https://deb.debian.org/debian/pool/main/c/csh/csh_20240808.orig.tar.xz`
- SHA-256：`df916baa73c264516177c6667cc0a061f6eb9743f862b625f17067d74a3f4d1c`
- 构建系统：BSD make（本适配使用 Conan 手工 clang 驱动）
- 编译目标：`aarch64-unknown-linux-ohos`
- 状态：built（未上传 Conan 制品）

## 适配范围

上游 C 源码保持为基础，仅通过 `patches/` 记录适配改动。Debian 已有的可移植性修复被合并到逐文件补丁中，主要包括 GNU glob/`strsignal` 兼容、`TIOCSTAT` 和 pledge 处理；`kill -l` 的 BSD 短信号名由本地兼容层补回，避免把 `strsignal()` 的长描述误当作信号名。

OHOS SDK 不提供上游依赖的部分 OpenBSD libc 接口，因此增加了两个补丁文件：

- `0005-ohos-compat.c.patch`：实现上述命名空间化兼容函数和 OHOS 所需的短信号名表。
- `0006-ohos-compat.h.patch`：声明并映射缺失的 `strlcpy`、`strlcat`、`reallocarray`、`strtonum`、`vis`/`strvis`/`strnvis`，并提供必要的宏。

其余替代包括用 GNU `fopencookie` 替代 `funopen`、用 `fflush` 替代 `fpurge`、用逐项 close 循环替代 `closefrom`，以及为缺失的 `_PATH_CSHELL` 提供默认值。`TIOCSTAT` 相关代码在目标头文件没有该接口时不编译。

## Conan 构建

1. `source()` 从 `conandata.yml` 下载并校验官方 tarball，然后调用 `apply_conandata_patches()`。
2. 配方使用 Conan `Environment` 和 `VirtualBuildEnv` 导出选定的 clang、CFLAGS 和静态链接标志；不调用 BSD Makefile 或 autotools。
3. 配方以 clang 预处理 `const.c` 生成 `const.h`，从 `error.c` 提取 `ERR_*` 定义生成 `error.h`。
4. 22 个上游 C 源文件和 `ohos-compat.c` 一起编译为 `bin/csh`，使用静态链接。
5. OHOS package() 使用 `llvm-objcopy`、`binary-sign-tool` 和 `llvm-readelf` 添加并验证 `.codesign`。

## 测试与限制

- 上游源码没有独立的 `check` 或 `test` 目标。直接对 BSD Makefile 运行 GNU `make check`/`make test` 会因 `.include <bsd.prog.mk>` 语法报 `missing separator`；这不是上游测试结果，已作为构建系统限制记录。
- 补丁文件本身是 unified-diff 文本；为保持 BSD 源码的原始制表符缩进和空白上下文，`git diff --check` 会把补丁负载中的上下文行报告为 whitespace（空上下文行或 space-before-tab），而不是报告补丁新增的源代码行。已验证 9 个补丁可清洁应用，所有新增行无尾随空白，且 fresh Conan 构建通过；不对这些语义必要的上下文空白做无依据的归一化。
- Conan `test_package` 从已安装的 `bin/csh` 执行脚本和 `-c` 命令接口，覆盖变量/算术、条件、命令执行、glob、管道、重定向和短信号名解析（6/6）。
- 额外的 OHOS smoke test 覆盖 `echo`、变量/算术、条件、管道、glob、重定向和 `kill` 短信号名解析（7/7）；输出见 `reports/ohos-smoke.log`。
- PR 描述已按 `templates/积分赛事PR模板.md` 补全“补全测试用例说明”章节，并明确勾选“是”，列出 13 个新增 OHOS consumer/smoke 用例及其范围。
- 通用 `finish` 的 G0 configure 步骤对该 BSD-make 项目不适用（源码没有 `configure`，返回 127）；随后 W3 又被仓库级 junk-check 的既有 cloog 标记阻断。没有伪造 `.staging-verified`、删除无关标记或弱化 Conan、消费者、签名检查。

## 交付文件

- `conanfile.py`
- `conandata.yml`
- `manifest.yaml`
- `notes.md`
- `commands.json`
- `test_package/`
- `patches/0001-*.patch` 至 `patches/0009-*.patch`
- `reports/test-report.md`

## 结束

- 编译结束：2026-09-13
- 最终状态：built（fresh Conan create、consumer、签名和手工 smoke 通过；verifier 的 L2/L4/L5 因未找到 cache 路径而跳过；未上传制品）
