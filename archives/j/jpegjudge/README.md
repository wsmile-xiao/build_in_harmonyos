# jpegjudge

jpegjudge（上游程序名 `judge`，作者 Marc Lehmann）是一个按 JPEG 编码参数
判定与比较图片的命令行小工具：它用 IJG libjpeg 以固定解码设置
（`JDCT_ISLOW` + 关闭 dither 与 fancy upsampling）解出像素，按 8x8 块做 DCT
并统计近零系数的比例，输出一个 0~1000 的「质量指示值」。同一图像用不同编码
质量保存会得到不同数值，因此可用于判重、比较与批量归类。

## 功能概述

- 逐个读取命令行给出的 JPEG 文件（`-` 表示 stdin），输出 `<文件名>: <指示值>`
- `-b` 只输出数值、抑制文件名，便于脚本管道处理
- `-v` 打印版本；`-h` 打印用法
- 正常判定退出码 0；遇到打不开的文件返回 1；用法错误返回 2
- 支持 IJG 库能读的全部 JPEG（含 progressive）

## OHOS 适配

- 构建系统是**随包发布的 autoconf 2.13 产物** `configure` + automake 1.4 的
  `Makefile.in`（输入文件名为 `configure.in`，并带 `acconfig.h`/`config.h.bot`/
  `stamp-h.in` 这一套 2.13 专属机制；包内无 `autogen.sh`、无 `config.guess`/
  `config.sub`）⇒ 不跑 autoreconf 重新生成，直接使用随包产物，避免新版工具链
  覆盖手写/旧版生成物。
- 随包 `configure` 不识别 Conan 默认注入的 `--datarootdir`，配方把 configure
  参数收敛为只传 `--prefix=/`，安装靠 `make install DESTDIR=<package_folder>`。
- 上游 CLI 只有 getopt 短选项，`--version`/`--help` 会以 2 退出，与平台
  smoke 门禁不兼容 ⇒ 用 `patches/0001-cli-long-options.patch` 补上这两个
  GNU 长选项（信息性选项，返回 0），不改 `-v`/`-h` 既有语义。
- 已知上游限制：图像宽度不足一个 8x8 块时统计分母为 0，指示值由整数除零结果
  决定（AArch64 除零不陷入，实测输出 1000 且退出码 0），上游 man 页也自陈
  「算法是盯直方图 10 分钟想出来的」，数值仅作相对比较用。

## 依赖关系

- 运行/编译依赖：`libjpeg`（本仓归档 `libjpeg/10`，静态制品 `libjpeg.a`）
- 构建工具：clang、make、随包 configure（无需 autoconf/automake 重新生成）
- 安装产物：`bin/judge`、`man/man1/judge.1`

## 参考资料

- 上游主页：<https://oldhome.schmorp.de/marc/judge.html>
- 源码包：<https://oldhome.schmorp.de/marc/data/judge-0.0.2.tar.gz>
- 许可：包内无 LICENSE 文件；`judge.c` 头部写明「可任意使用，但不得声称是自己
  写的」，内嵌代码来自 IJG JPEG 库（见 `README-jpeg6a` 的 IJG 许可条款）
  ⇒ 配方按 `IJG` 声明。
