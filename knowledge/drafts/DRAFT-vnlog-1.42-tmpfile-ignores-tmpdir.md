# 路径 B 候选：`TMPDIR` 与 libc `tmpfile()` 是两个验证点

状态：待审核草稿，不分配正式 E 编号；归属 `vnlog/1.42` 的适配 PR。与现有 `knowledge/graph/E002.kv`（构建工具默认临时目录只读，建议设置 `TMPDIR`）比对后，本条只提出尚未被该建议覆盖的 C 标准库 `tmpfile()` 行为。是否应合并到 E002 而非新建条目，由知识库维护者决定。

## 可复验现象

- 同一 HarmonyOS PC AArch64 真机、同一可写验证目录，Clang 编译测试程序最初报 `unable to make temporary file: Read-only file system`；设置 `TMPDIR=$run/tmp` 后，上游 C API 套件 12/12 通过。
- 首次 `conan create` 中的消费者 CTest 却因测试程序调用 `tmpfile()` 而失败。独立 C 小程序在可写 `TMPDIR` 下调用 `tmpfile()`，返回 `errno=13 (Permission denied)`。
- 消费者测试改为在 CTest 可写工作目录里用 `fopen("vnlog-test-input.vnl", "w+")` 写入同一输入，测试完成后删除；第二次 `conan create` 返回 0，CTest 1/1 通过。

## 根因与处理边界

本机观察证明 `TMPDIR` 能解决 Clang 的临时输出，却不足以保证该环境的 libc `tmpfile()` 使用相同的可写路径。未追踪 libc 实现或系统调用，因此不推断所有 HarmonyOS 版本的固定路径，也不把权限失败直接归因于 SELinux。遇到同类故障应分别做一个最小编译试验与一个独立 `tmpfile()` 探针，记录 `errno`，再确认测试工作目录可写。仅当文件确实只是测试夹具时，可改为工作目录中的命名文件并清理；生产代码依赖 `tmpfile()` 时须另行设计，不应以修改测试掩盖生产缺陷。

## 证据与范围

- 源码：`vnlog` 上游 v1.42，归档 SHA-256 `b50fd49dd2058d6286c7ccf253c017d0b692c840994f73d58240097c3a804f4d`；目标机 `/data/storage/el2/base/haps/entry/files/vnlog-1.42-20260926T142325`。
- 原始失败日志 `create.log` SHA-256 `f4e945060fcb5c14b9cfcb5686d062ee87f01f5eb5e961bfe19b278febb6fe7f`；修复后 `create2.log` SHA-256 `142e0e6bc81f186cf91f1e1810dd897609a07c30fc45f09a537eb9a881bcf2e2`。日志存于目标机私有工作区，不随 PR 上传。
- PR 中 `archives/v/vnlog/1.42/test_package/test.c` 可核对消费者测试前后处理；`notes.md` 记录了范围。独立探针源码留在贡献者本地工作区 `probe-tmpfile.c`，可按下段重建。
- 上游 `make check` 共 8 个套件，仅 C API 套件原样运行（12/12 检查）；其余 7 个 Perl/Python 套件未验证。交付物仅原生 C 静态库、头文件、`vnl-gen-header`，不宣称整包适配。

## 最小探针

```c
#include <errno.h>
#include <stdio.h>
#include <string.h>
int main(void) {
    FILE *f = tmpfile();
    if (f) { fclose(f); return 0; }
    fprintf(stderr, "tmpfile failed: errno=%d (%s)\n", errno, strerror(errno));
    return 1;
}
```

在目标机可写工作目录中编译、设置可写 `TMPDIR` 并执行。不要把本次现象外推成所有 libc 或系统版本的恒定行为。PR、CI、知识库入库和路径 B 评分均待官方评审。
