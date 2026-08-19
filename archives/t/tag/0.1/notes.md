# tag 0.1 适配笔记

## 编译环境
- 构建系统: makefile
- 编译日期: 2026-08-19
- 编译器: clang
- 状态: built

## 编译步骤

1. 源码获取：官方归档 `https://github.com/mafintosh/tag/archive/refs/tags/0.1.0.tar.gz`
   （sha256 `2584198e...d04ac4a`，上游 git tag 为 0.1.0；任务版本号记作 0.1）。
2. 构建：`make CC=<conan-conf clang> -j1`（R9 单任务；R33 编译器取自 Conan 工具链，不裸用 `${CC}` 环境变量）。
   上游 Makefile 的 `all` 目标直接用 `$(CC) src/tag.c -std=c99 -O3 -Wall -o tag`，无 configure 步骤。
3. 打包：上游 `make install` 依赖 `install` 工具（OHOS 上可能缺失），配方改为用 Conan `copy()`
   把构建产物搬运到 `package/bin/`（R19：搬运的是本次构建产物，非预编译二进制）。
4. test_package：对打包后的 `tag` 二进制做真实功能验证（stdin 打标 / %l 行号 / %d 日期格式 / 退出码），
   输出 `HMBS_TEST_PACKAGE_RESULT` 标记；上游无测试套件，build() 末尾输出
   `HMBS_UPSTREAM_TEST_RESULT={"status":"no_tests",...}`（airspy 先例）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游 `make install` 依赖 `install` 工具 | OHOS 工具集未必提供 install 可执行文件 | 配方直接用 Conan `copy()` 搬运构建产物到 package bin/ |
| 2 | 测试输出流含 NUL 字节 | `compile_format()` 以 `' '` 与 `''` 结尾填充 stamp，`main()` 按 `stamp_len` 整段 `write()`，NUL 一并写出（2013 年上游行为） | test_package 脚本用 `tr -d '\000'` 归一化后再比对，语义与 README 示例一致 |
| 3 | 真机 conan create 失败：`ConanException: [conf] 'tools.build:compiler_executables:c' does not exist in configuration list` | Conan 2 中 `tools.build:compiler_executables` 是 dict 型 conf，不能按 `:c` 子键读取 | build() 改为整体读取 dict（`check_type=dict`），再取 `"c"` 键，缺省回退 `clang`；同日志中的 `/tmp` 只读报错经 grep 审计来自 hmbs 包装脚本 preflight.sh 的 mktemp，配方无 /tmp 引用，不改配方 |
| 4 | 真机 conan create 失败：`make: *** No targets specified and no makefile found.`，build() line 56 `self.run("make CC=... -j1")` 退出码 2 | Conan 2 `basic_layout` 将 build_folder 与 source_folder 分离，`self.run()` 默认在 build_folder 执行；上游 tag 无 configure 步骤，Makefile 只存在于源码根目录，build_folder 中永远没有 Makefile | build() 的 make 改为 `cwd=self.source_folder` 的 in-source 构建（aa3d/accrete 先例），package() 相应从 `self.source_folder` 拷贝 `tag` 二进制 |

## 源码修改

无补丁（纯构建适配，不改上游源码）。

## 依赖版本

无第三方依赖（仅 libc）。

## 验证结果

- 本机完成配方结构与语法校验；真机 conan create 由 HMBS 预检执行并产生 evidence。
- test_package 共 5 个真实用例：消息前缀、%l 行号计数、%d 日期戳格式、无参用法退出码 1、非法格式 %z 退出码 2。

## 注意事项

- 上游无任何自动化测试：0.1.0 归档仅 4 个文件（Makefile / README.md / package.json / src/tag.c），
  Makefile 无 check/test 目标，package.json 无 test 脚本字段，src/tag.c 是单 main() 程序无测试代码。
  `test_package/MANIFEST.yml` 已写 `upstream_tests_exist: false` + 非空审计结论。
- 许可：README.md 与 package.json 均声明 MIT（上游仓库本身无 LICENSE 文件）。

## CI 失败修复（2026-08-19，build #27515）

### 失败证据
- CI Worker（OHOS 设备）同时缺 `curl` 与 Python SSL 模块：
  - 预下载步骤：`[fail] [Errno 2] No such file or directory: 'curl'`
  - conan source()：`Can't connect to HTTPS URL because the SSL module is not available.`
  - gh-proxy.com 与 github.com 两个 HTTPS URL 均下载失败 → `conan create` 失败。
- 命中知识库草稿 E2149（pkgconf 3.0.5 先例，PR #5532）：Worker 无 curl + Python 无 SSL
  时，conan 的 HTTPS 下载不可用，需在 conandata.yml 提供镜像 fallback 让 conan 逐个尝试。

### 修复方案
- `conandata.yml` 的 `sources.url` 由单值改为有序列表（复用 ci/conan/build_and_test.sh 的
  GitHub 镜像映射，镜像在前、官方原始 URL 保留在最后作为回退）：
  1. `https://gh-proxy.com/https://github.com/mafintosh/tag/archive/refs/tags/0.1.0.tar.gz`
  2. `https://github.com/mafintosh/tag/archive/refs/tags/0.1.0.tar.gz`
- sha256 保持不变（`2584198e...d04ac4a`）；已实测 gh-proxy.com 返回 1913 bytes 与官方归档
  逐字节一致（sha256 均 `2584198ed073b74a2b521561a95475b5db8a417f228c055cb9f6ab919d04ac4a`）。
- 未修改官方 URL、未改校验值、未引入来源不明的下载地址（E2149 安全边界）。

### 备注
- 本机为受限环境（git bash 无完整网络栈），gh-proxy.com 镜像一致性验证在可联网环境完成；
  真机 conan create 由 HMBS 预检执行并产生 evidence。
