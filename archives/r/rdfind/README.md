# rdfind（HarmonyOS PC 适配）

[rdfind](https://rdfind.pauldreik.se/) 是一个查找重复文件的命令行工具，可用硬链接
或符号链接替换重复项。

- 归档版本：`1.8.0`（`archives/r/rdfind/1.8.0/`）
- 上游源：https://rdfind.pauldreik.se/rdfind-1.8.0.tar.gz（官方发布页）
  sha256 `0a2d0d32002cc2dc0134ee7b649bcc811ecfb2f8d9f672aa476a851152e7af35`
- 依赖：`nettle/3.10.2.1`（制品仓已发布）；xxhash 可选，构建时显式关闭
- 构建系统：Autotools（release tarball 自带 `configure`）
- 产物：`bin/rdfind`（命令行工具，见 `commands.json`）
- 补丁：**1 个** —— `1.8.0/patches/0001-configure-hmdfs-umask.patch`
  （把 autoconf `configure` 中建私有临时目录的两处 `umask 077` 改为 `022`，
  修 HMDFS 上 `config.status: Permission denied`；上游 `.c/.h` 与 `configure.ac` 未改动）
- 测试：上游 `make check`（15 个 shell 用例）+ `test_package/test_rdfind.sh`
  （构造重复文件树，校验 `results.txt` 的 duptype 分类）
- CI：构建 #50911 / #50915 / #50925 / #50928 校验通过（R51 强制门禁下）（Conan test_package
  通过、L0/L1 门禁通过）；CI 为评论触发（push 不触发，需发 `/rebuild`），引用以平台最新
  `## CI 校验通过` 评论为准
