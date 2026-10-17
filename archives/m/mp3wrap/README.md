# Mp3Wrap

> Command-line utility to wrap multiple MP3 files into one large playable MP3 file without losing filename and ID3 information.

## 简介

Mp3Wrap 是一个轻量级命令行工具，由 Matteo Trotta 于 2002 年开发。它将两个或多个 MP3 文件合并为一个大的可播放 MP3 文件，同时保留原始文件名和 ID3 信息。输出文件命名为 `OUTPUTFILE_MP3WRAP.mp3`，其中 `_MP3WRAP` 字符串是必要的标记，便于拆分工具（mp3splt）识别该文件已被 mp3wrap 包装。

合并后的文件本身是一个完全合法的 MP3 文件，可以正常播放；使用 [mp3splt](http://mp3splt.sourceforge.net) 可以无损还原原始文件。

## OHOS 适配要点

1. **`u_int32_t` → `uint32_t`**：`crc.c` 使用 BSD 风格的 `u_int32_t` 类型，该类型在 musl libc（OHOS 使用的 C 库）中未定义。替换为 C99 标准的 `uint32_t`（来自 `stdint.h`），功能完全等价。
2. **`configure` umask 修复**：mp3wrap 0.5 的 `configure` 脚本（automake 1.5 生成）使用 `umask 077` 创建 `config.status` 临时目录。在 OHOS 的 hmdfs 文件系统上，`mkdir` 会附加 setgid 位，`umask 077` 创建的 `drwx--S---` 目录构建进程自身无法写入。补丁将其改为 `umask 022`。
3. **无 config.sub/config.guess**：mp3wrap 0.5 发布于 2003 年，使用 automake 1.5，`configure` 不包含 `config.sub` / `config.guess` 文件。交叉编译三元组通过 `--build` / `--host` 直接传递，configure 仅探测 `CC` 和 `INSTALL`，不涉及目标平台检测。
4. **无上游测试套件**：Makefile.in 的 `check` 目标仅重新构建（`check-am: all-am`），不存在任何 TESTS、check_PROGRAMS、test/ 目录或测试脚本。

## 排除与替代

- mp3wrap 仅安装 `mp3wrap` 可执行文件和 man 手册页（`mp3wrap.1`），无需排除任何组件。
- 拆分工具 mp3splt 是独立项目，不在本包范围内。

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| 无 | — | mp3wrap 是纯 C 程序，仅依赖 libc（stdio、stdlib、string、unistd、dirent） |

## 功能验证

```bash
# 合并两个 MP3 文件
mp3wrap output.mp3 input1.mp3 input2.mp3
# 生成 output_MP3WRAP.mp3

# 列出已包装的文件
mp3wrap -l output_MP3WRAP.mp3

# 添加文件到现有包装
mp3wrap -a output_MP3WRAP.mp3 input3.mp3
```

## 参考

- [Mp3Wrap 官方主页](https://mp3wrap.sourceforge.net/)
- [SourceForge 项目页](https://sourceforge.net/projects/mp3wrap/)
- [mp3splt（拆分工具）](http://mp3splt.sourceforge.net)
