# 【知识库扩展】feat(libbtrfs-dev): 6.2 适配 HarmonyOS PC

## 问题

旧版 btrfs 消费者可能直接包含 btrfs-progs 的内核兼容头文件。后续版本重构已安装的 `kerncompat.h` 时删去 `gfp_t`、`GFP_KERNEL` 等宏，依赖这些宏的下游代码会在编译期失败。btrfs-compsize 1.5 的交叉编译实测要求将头文件基线固定为 btrfs-progs v6.2。

## 适配

本包固定上游 tag `v6.2`，交付 libbtrfs 公共头文件、`libbtrfs` 库和消费者所需的 btrfs kernel/UAPI 头闭包。上游版本头按其 `version.h.in` 生成。配方只编译上游 `libbtrfs` 的实现单元，不运行与开发库无关的工具程序配置流程。

## 鸿蒙验证边界

HarmonyOS PC 消费者测试使用包内 include/lib 元数据构建并链接外部 C 程序，检查 `ctree.h`、`ioctl.h`、`sizes.h` 闭包和公开库符号；独立的 AArch64 测试检查指针与 long 的 LP64 ABI 及 ioctl 结构布局。`libbtrfsutil/btrfs_tree.h` 与配套 `btrfs.h` 不纳入同一 include 目录，因为它们与旧版 libbtrfs 的 `ioctl.h` 重复定义多个 ioctl 结构。测试不声称执行需要 btrfs 内核文件系统的 ioctl。

## 可复用经验

开发包应同时锁定头文件与库的上游版本。若消费者依赖上游内部兼容宏，升级头文件时应在目标交叉编译器下保留消费者编译验证，不能仅以包自身成功构建作为兼容性证据。

## 关联记录

- 依赖任务：[#14633](https://ohpcd.atomgit.com/contrib/tasks/14633)
- 父任务：[#14599](https://ohpcd.atomgit.com/contrib/tasks/14599)
- 适配 PR：[#13778](https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/pulls/13778)
- 路径 B 知识库 Issue：[#3576](https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/3576)
