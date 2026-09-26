# wput 0.6.2-git20130413 适配记录

## 上游与版本

- 上游项目：[Wput](https://wput.sourceforge.net/)
- 官方 Git 仓库：<https://git.code.sf.net/p/wput/code>
- 固定提交：`4af565604695b397e50c0595e03dd0062066648e`（2013-04-13）
- 许可证：GPL-2.0-or-later
- 构建系统：Autotools configure + 手写 Makefile
- 目标：HarmonyOS PC AArch64

## 适配方式

- Conan 应用包构建 `wput` 命令行程序，并保留 man page 与许可证文件。
- 本配方用 `--without-ssl` 构建。该快照的 TLS 代码通过 `gnutls/openssl.h` 调用 OpenSSL 兼容 API；已发布的 HarmonyOS `gnutls/3.8.10` 包不含此头文件或 `libgnutls-openssl`，因此不能据此启用 TLS。
- `src/wput.h` 原先在头文件中定义全局对象 `opt`，被多个翻译单元重复定义；按仓库 E491 规范改为头文件 `extern` 声明，并在 `src/wput.c` 保留唯一实体定义。
- 上游 Makefile 不是 VPATH-safe；recipe 在源码目录执行 configure 和 make。
- 上游 `configure` 在创建 `config.status` 临时目录时以 `umask 077` 调用 `mktemp -d`，失败时也以相同 umask 调用 `mkdir`。HarmonyOS/HMDFS 的 setgid 目录语义使这类目录无法供 `config.status` 写入，CI #61796 的错误路径虽位于 TMPDIR 下仍发生 Permission denied。按仓库已有 HMDFS 适配做法，将两处 umask 改为 `007`，保留组遍历与写权限；单纯切换 TMPDIR 不能修复该权限模式问题。
- Wput 0.6.2 是 FTP 上传客户端，网络上传功能以 loopback FTP 服务进行消费者验证。

## 上游测试清点（R51）

固定提交的源码树中没有 `tests/` 目录，也没有 CTest 或 pytest 注册。根目录 `Makefile.in` 只定义 `all`、`clean`、`win-clean`、`install`、`uninstall`，不存在 `check`/`test` target。因此本版本没有可逐项运行的上游测试；适配后的测试由 Conan test_package 执行。

## 适配测试

`test_package/test_wput.py` 要求运行环境报告 `HarmonyOS` 与 AArch64，调用打包后的 `wput --version`，再向 loopback FTP 服务上传含二进制字节的 fixture 并逐字节核对。测试服务使用 CRLF 收发 FTP 行，且测试直接执行 Conan 包中的二进制。

## 验证结果

- HarmonyOS 6.0 AArch64（armv8）、Clang 15：应用 `umask 007` 补丁后，强制源码重建的 `conan create` 配置、编译和打包通过。
- Conan `test_package` 在真机上运行成功：平台与架构断言、`wput --version`、loopback FTP 上传退出码及二进制内容逐字节比对均通过（5 项检查）。
- 仓库本地 CI：`tests/run_all.py` 的 12 个套件全部通过。Windows 环境下先用仓库原命令检查时，`test_v1220.py` 的 Git 路径指向 HarmonyOS 设备；使用临时 `sitecustomize` 将该路径映射到本机 Git 后复跑全绿，未修改测试文件。
- `scripts/ohc-run.py graph validate` 通过（知识图谱 540 条记录，存在既有提示项）。
---

**编译结束**: 2026-09-26 12:42
**最终状态**: built

### 对话 #1 — 2026-09-26 真机验证

- HarmonyOS 6.0 AArch64 真机执行仓库官方 `ci/conan/setup.sh` 与 `ci/conan/build_and_test.sh`，wput 1/1 构建成功，L0/L1/L2/L4/L5 全部通过。
- `finish` 的 W3 步骤通过，`.ci-result.json` 由工具自动生成，`exit_code=0`，日志 SHA-256：`4447bcacf49a93870ea3654163cb2559d32674d87f6fd7e8042af684359e1270`。
- 将 Conan 产物打包为 `packaging/wput-0.6.2-git20130413-ohos-aarch64.tar.gz`，在设备上解包后运行同一 HarmonyOS FTP 消费者测试通过。
- 详细用例与限制见上文“上游测试清点”“适配测试”和“验证结果”。此前 `finish` 的后续通用归档、知识图谱和 W2 检查仍未完成，因此不据此前记录声称提交预检已全部完成。
