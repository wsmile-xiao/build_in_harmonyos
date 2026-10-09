# libc 私有 `__S_IF*` 常量与可移植的 `stat` 文件类型判断

状态：知识库扩展草稿，是否独立入库或归并由维护者判断。通用触发特征是 C/C++ 源码直接使用 `__S_IFMT`、`__S_IFREG`、`__S_IFDIR` 等双下划线实现细节；不是 YAZE-AG 独有问题。

## 现象与根因

在 HarmonyOS PC AArch64 的 musl/Clang 环境，YAZE-AG 2.51.3 原始 `monitor.c` 编译报 6 个 `use of undeclared identifier '__S_IF*'`。该源码以 `__EXTENSIONS__` 条件选择公开的 `S_IF*` 或 glibc 私有的 `__S_IF*`，却没有跨 libc 保证。目标 `<sys/stat.h>` 不提供私有名字；这不代表 `stat()` 或常规文件挂载不可用。

## 可复用处理

1. 先区分文件类型判断的源码接口缺失与底层 `stat()` 系统能力缺失；不要基于编译错误推断运行能力。
2. 对常规文件和目录分别用 `S_ISREG(st.st_mode)`、`S_ISDIR(st.st_mode)` 替代位掩码比较，不引入 `__OHOS__` 专属分支。
3. 在目标机以真实常规文件和目录复验涉及的功能路径，避免只记录“编译通过”。本例新增 Conan 消费者测试用已打包的两张 `.ydsk` 常规文件挂载为 A/B 盘，并列出挂载结果。

该规则只覆盖文件类型谓词；特殊文件类别、权限位处理或 `stat` 失败原因须分别验证。补丁未修改 Z80 执行核心；不能据此声称完整模拟器指令回归通过。

## 证据

- 官方源码归档 SHA-256：`2b0a90c3bf3a27574b0427cf4579dc2347b371bec3fea5739e1527edf74b2809`。
- 真机隔离目录：`/data/storage/el2/base/haps/entry/files/yaze-ag-2.51.3-20260926T170600`。原始编译日志 `build.log` SHA-256：`3b50e1ea33c22a8197eb4ef98d84bec6619e0c54d39ec8790cf191e709240117`，含 6 个私有宏未声明错误。
- 修补后的最终 `conan create` 日志 `create-v4.log` SHA-256：`2a2f4d10337e6f3b233cddb085fdb616b211110657004806a8ae293943e02691`，消费者测试输出 `YAZE-AG boot, disk mounts and monitor exit: PASS`。上游自动化测试因发布包缺少 Makefile 所列 `test/` 目录而未运行。
