# vnlog 1.42 适配笔记

## 范围与来源

- 上游：[dkogan/vnlog v1.42](https://github.com/dkogan/vnlog/releases/tag/v1.42)，源码 SHA-256：`b50fd49dd2058d6286c7ccf253c017d0b692c840994f73d58240097c3a804f4d`。
- 交付范围：`libvnlog.a`、`vnlog.h`、`vnlog-parser.h`、`vnlog-base64.h` 和 `vnl-gen-header`。
- 未交付：其余 Perl CLI、Perl 模块、Python 模块。它们不能随本 C 库的验证结论一并宣称适配。
- 上游 README 将库声明为 LGPL-2.1-or-later；`b64_cencode.c` 在 README 中说明为公有领域。

## 构建与依赖

上游 `GNUmakefile` 在进入编译前需要 `mrbuild`，目标机上不存在。配方直接以 Clang 编译上游原始 `b64_cencode.c`、`vnlog.c`、`vnlog-parser.c`，用 `ar` 组成静态库；未改上游源码。Conan W0 隔离环境运行 `conan graph info --build=never`，依赖图为空。

真机：`10.62.210.132:2222`，`currentUser`，HarmonyOS aarch64；SSH ED25519 主机指纹为 `SHA256:DFfqMHwsW7a2AYgyrWePX6tgJTrm6jpppNyeBWqmXxQ`。同一次验证目录为 `/data/storage/el2/base/haps/entry/files/vnlog-1.42-20260926T142325`。源码 tarball 与配方 tarball 两端 SHA-256 一致，并从目标机独立读回原始字节复核。

## 测试结果

上游 `make check` 列出 8 个测试套件。本次原样执行 `test/test_c_api.sh`：2 个输出比对、6 个有效输入比对、4 个预期失败输入，共 12/12 检查通过。其余 7 个套件未运行：目标机缺少 Perl `List::MoreUtils`、`Text::Table`、`IPC::Run`、`Text::Diff` 和 Python NumPy；不得据此宣称上游全套测试通过。

隔离 `CONAN_HOME` 的第二次 `conan create -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 -c tools.build:jobs=1` 通过，消费者 CTest 为 1/1 通过。构建和测试均在真机执行；本地 Windows 仅用于源码校验和传输。

## 失败、修复和边界

1. 首次手动编译时，目标机默认临时目录只读，Clang 在编译测试程序时报告 `unable to make temporary file: Read-only file system`。在同一验证目录设置可写 `TMPDIR` 后，上游 C API 检查通过。
2. 首次 Conan 消费者测试失败。测试程序原用 `tmpfile()`；独立探针证明即使设置了可写 `TMPDIR`，该调用在此机仍返回 `EACCES`。未追踪 libc 内部实现，不断言其固定落盘路径。测试夹具改为在 CTest 可写工作目录内用 `fopen(..., "w+")` 创建输入并在成功后删除。第二次构建在同一验证目录通过。两次尝试分别保留 `create.log/create.rc` 与 `create2.log/create2.rc`，不覆盖失败证据。
3. 此 PR 证明的是 C 库及生成器可交付、C 测试通过；完整 Perl/Python 工具链仍需依赖解析与独立验证。当前状态为 `built`，不代表合并、发布、CI 或路径 B 加分已获认可。
