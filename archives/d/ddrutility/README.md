# ddrutility

## 简介

ddrutility 是一组配合 GNU ddrescue 使用的数据恢复辅助工具，用于在坏盘救援过程中
定位坏道与哪些文件相关、导出 NTFS 分区已用空间位图，以及通过 SCSI 直通命令对源盘
执行操作。

本仓库交付 **ddrutility 2.8** 的 HarmonyOS PC（aarch64 / OHOS）Conan 配方。

## 交付程序

| 程序 | 类型 | 用途 |
|------|------|------|
| `ddrutility` | C | 工具集入口，展示版本与包含的程序列表 |
| `ddru_ntfsbitmap` | C | 读取 NTFS 分区 bitmap，生成 ddrescue domain logfile（只恢复已用区域） |
| `ddru_ntfsfindbad` | C | 依据 ddrescue 日志列出 NTFS 分区上涉及读取错误的文件 |
| `ddru_diskutility` | C | 通过 SCSI 直通命令对源盘执行操作的多用途工具 |
| `ddru_findbad` | POSIX sh | 依据 ddrescue 日志定位坏道相关文件（脚本） |

分类：系统/工具类命令行程序（`commands.json` → `type: tool`）。

## 构建

- 构建系统：上游手写 makefile（2.8 起不再使用 automake）
- 编译器：OHOS clang 15（aarch64-linux-ohos）
- 关键构建命令：

```bash
make CC=<clang> CFLAGS='-O2 -Wall -W' -j1
```

- 补丁 `0001`/`0002`：旧 C 代码在头文件里直接定义全局变量，靠编译器默认
  `-fcommon` 合并 tentative definition；clang 15 默认 `-fno-common` 时会报
  `duplicate symbol`。按知识库正解改为「头文件 `extern` 声明 + `ddru_ntfscommon.c`
  单一定义点」，**不使用 `-fcommon` 兜底**。

## 依赖

- 编译依赖：无（仅 libc）
- 运行期外部命令（`ddru_findbad` 按需调用，非链接依赖）：`sleuthkit`、`ntfs-3g`、
  `gnu-fdisk`、`gnuddrescue`

## 测试

- 上游 ddrutility 2.8 无测试套件（tarball 无 `tests/`、makefile 无 `check`/`test`
  目标、全树无测试源文件），上游用例数 N=0。
- 适配后补全鸿蒙特有消费者测试 `test_package/test.sh`：实执行 5 个交付程序的
  `--version`/`--help`（10 项），并做 3 项非法输入边界断言（证明程序真实解析
  参数与输入数据），共 13 项断言。

## 适配说明

- 上游 makefile 写死 `CC= gcc`，配方以 `make CC=<clang>` 覆盖（命令行赋值优先），
  不引入源码补丁。
- `ddru_findbad` 交付名为 `ddru_findbad.sh`，upstream makefile 安装时改名为
  `ddru_findbad`；配方在 `package()` 中同样改名并补执行位。
- 无平台宏、无 stub：`__linux__` 与 `scsi/sg.h`、`iconv.h` 在 OHOS clang/sysroot
  下均可用。

## 参考资料

- 官网：https://ddrutility.sourceforge.net/
- 上游发布页：https://sourceforge.net/projects/ddrutility/files/
