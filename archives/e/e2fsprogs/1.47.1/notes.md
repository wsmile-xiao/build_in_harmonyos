# e2fsprogs 1.47.1 编译笔记（HarmonyOS PC · 标准 Conan autotools）

## 定位
- 产出 libext2fs.so 等 4 个库，供链接与 dlopen。

## 关键适配

### 补丁 `e2fsprogs-0001-unconditional-sys-types.patch` —— 上游缺陷

公开安装的 `lib/ext2fs/ext2fs.h` 把 `#include <sys/types.h>` 守在

    #ifdef HAVE_SYS_TYPES_H
    #include <sys/types.h>
    #endif

后面，而 `HAVE_SYS_TYPES_H` 是 **e2fsprogs 自己构建时**的 configure 宏 ——
消费方编译时根本没有它，于是该 include 被跳过，而本头文件下面用到了
`dev_t` / `mode_t`。

glibc 下靠 `stdio.h` 等间接引入侥幸能过；musl 不引入，消费方直接报

    error: unknown type name 'dev_t'; did you mean 'div_t'?
    error: unknown type name 'mode_t'

**公开安装的头依赖私有 configure 宏本身就是缺陷**，且会打到每一个下游消费方，
所以在这里去掉守卫，而不是让每个使用者自己先 include 一遍。

⚠️ 这个缺陷**在 e2fsprogs 自己构建时完全不暴露**（它有自己的 config.h），
只有以消费方视角编译才会发现 —— 本包的 test_package 正是这么发现的。

### `--enable-symlink-build` / `--enable-symlink-install`

**HMDFS 不支持硬链接。** 上游用 `ln` 把库发布到 `lib/`：

    ln: cannot create hard link from 'et/libcom_err.a' to
        'libcom_err.a': Operation not permitted

这两个开关把构建期与安装期的 `ln` 都换成 `ln -s`（`LINK_BUILD_FLAGS=-s`）。
这是平台文件系统的固有限制，重跑无用，必须改链接方式。

### 选项取舍

- `--disable-fsck` / `--disable-e2initrd-helper`：ai-models 要的是**库**，
  命令行工具不进制品。
- `--disable-nls`：本地化文件不进制品。
- **不关** `--enable-elf-shlibs`：库形态由 conan 的 `-o shared` 控制，
  显式传会把它顶掉。

## 消费方注意

`com_err` 的错误码表**不会自动加载**，使用前须调 `initialize_ext2_error_table()`，
否则 `error_message()` 只返回 `Unknown code ext2 19`。上游自己的代码
（`icount.c` / `inline_data.c` 等）也都是先调这个。本包 test_package 已覆盖该路径。

## 状态

built（真机 conan create + test_package 通过）
