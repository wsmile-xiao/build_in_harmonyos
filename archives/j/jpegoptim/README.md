# jpegoptim

**描述**: JPEG 无损优化/压缩命令行工具（Huffman 表优化、渐进式转换、元数据剥离）

**主页**: https://github.com/tjko/jpegoptim

**官方源码**: https://www.kokkonen.net/tjko/src/ （GitHub tag 包与官方 dist 包字节一致，同一 sha256）

**许可证**: GPL-2.0-or-later（1.4.7）/ GPL-3.0-or-later（1.5.5 起上游改票）

**语言**: C

## 常用用法

```bash
jpegoptim photo.jpg                  # 无损优化，原地改写
jpegoptim --strip-all photo.jpg      # 优化并剥离所有可选标记段
jpegoptim -m85 -S200k *.jpg          # 限制质量上限 / 目标体积
jpegoptim -n -t photo.jpg            # 只试算、不写文件，并打印汇总
```

## 鸿蒙适配要点

| 问题 | 做法 | 知识条目 |
|---|---|---|
| 自带 `tools/config.guess`、`tools/config.sub` 不认识 HarmonyOS，`configure` 报 `cannot guess build type` | 注入 `*:HarmonyOS:*:*)` 分支（该代脚本无 `GUESS` 尾部兜底，分支必须自带 `echo <三元组>; exit 0`）+ config.sub 两处接受 `linux-ohos` | E007 |
| `config.status` 用 `umask 077 && mktemp -d` 建临时目录，HMDFS 上连属主都写不进去 | 补丁改 `umask 022` | E011（同族签名 E114） |
| 1.4.7 的手写 `Makefile.in` 编译规则无 `-I` 构建目录，out-of-tree 直接 `'config.h' file not found` | 配方用 in-source 布局（`folders.source == folders.build`） | - |
| `make -j` 需要 jobserver FIFO，HMDFS 拒绝创建 | `autotools.make(args=["-j1"])` | E074 |
| 测试图不能由 `cjpeg` 生成（其 DT_RPATH 是相对路径，加载器按 CWD 解析失败） | fixture 以 base64 形式写在 `test_package/conanfile.py` 里，由 conan 自己的 Python 落盘 | - |
| 1.5.5 起上游 CMake 默认 `USE_MOZJPEG=1`，构建期下载 MozJPEG | 显式传 `LIBJPEG_INCLUDE_DIR`/`LIBJPEG_LIBRARY` 且 `USE_MOZJPEG=0` | - |

产物为单个可执行文件（`bin/jpegoptim`），因此需要软件级 `commands.json`（R38）；
它是命令行工具而非库，`package_info` 里 `libs = []`。

## 已编译版本

| 版本 | 状态 | 构建系统 | 补丁 | 日期 |
|------|------|----------|------|------|
| 1.4.7 | built | autotools | 3 | 2026-09-19 |
| 1.5.5 | built | cmake | 0 | 2026-09-12 |
