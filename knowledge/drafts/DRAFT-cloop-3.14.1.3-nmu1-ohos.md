# DRAFT-cloop-3.14.1.3-nmu1：旧版 cloop 用户态工具的 HarmonyOS 适配链

> Status: Draft；仅提交到 `knowledge/drafts/`，不提升为正式 E 条目。

## 背景

cloop 3.14.1.3+nmu1 同时包含 Linux 内核模块和用户态压缩/解压工具。HarmonyOS PC 适配边界是用户态工具；内核模块不纳入 Conan 包。

## 可复用问题

- 旧 `config.guess` 不识别 HarmonyOS/aarch64，必须显式传入 build/host。
- HMDFS 下生成的 Autoconf `confstatXXXXXX` 临时目录受 `umask 077` 影响，后续文件写入失败；将生成脚本的临时目录模式调整为 `022`。
- OHOS libc++ 中未限定的 `bind` 会与 `std::bind` 冲突，应使用 `::bind`。
- OHOS sysroot 不提供 Linux 专用 `loff_t`，可用 `int64_t` 保持 cloop 64 位偏移格式。
- 配方把 `advfs` 复制为两个命令名，并显式恢复执行位，因为 HMDFS 可能拒绝硬链接替换，也可能不保留复制文件的执行位。

## 验证边界

已验证用户态压缩器和解压器能够编译，消费者测试验证了压缩—解压前缀一致以及块尾零填充。上游 `make check-local` 已实际执行，但发布包中的测试目标仍使用过时的 `advfs` 参数形式，在功能断言前失败；该失败必须如实保留，不能统计为通过。
