# routino — OpenHarmony 编译档案

## 软件简介
routino 是 OpenStreetMap 路由软件：提供 router（路径规划）、planetsplitter
（OSM 数据切库）、filedumper（数据库转储）等命令，以及可供二次开发的
libroutino / libroutino-slim 路由库（`routino.h` API）。

## OHOS 适配要点
- 自定义 Makefile（`Makefile.conf`），无 configure；编译器与归档工具经
  `generate()` 从 Conan conf 注入 conanbuild 环境（`$CC/$CXX/$AR/$RANLIB`，R33）
- `FASTMATHS=0` 追加 `-fno-fast-math`，消除上游默认 `-ffast-math` 的数值漂移
- **HMDFS 无 symlink**：OHOS 下 `validate()` 拒绝 `shared=True`，只发布静态包
  （bzip2 先例）；lib 型测试所需的 `.so` 在构建树内用实文件拷贝代替 soname 链接
- 测试脚本经 `$CONFIG_SHELL` 显式调用（OHOS 无 `/bin/sh`，R5）
- 上游 126 个 shell 用例全部按子进程退出码计数（rule4：禁 stdout 字符串计数）

## 依赖关系
- 编译依赖：zlib/1.3.1（gzip 支持）、bzip2/1.0.8（bzip2 支持）
- 构建时工具：perl（xml 数据生成、waypoints.pl）、diff
- 被依赖：无（首个版本）

## 参考资料
- [routino 官网](https://www.routino.org/)
- [libroutino API 文档](https://www.routino.org/documentation/library.html)
