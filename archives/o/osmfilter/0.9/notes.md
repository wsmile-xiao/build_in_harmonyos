# osmfilter 0.9 适配笔记

## 编译环境
- 构建系统: makefile
- 编译日期: 2026-06-16
- 编译器: clang/clang++
- 状态: built
- 许可证: AGPL-3.0
- 源码: https://gitlab.com/osm-c-tools/osmctools.git（git 仓库，tag 0.9）

## 编译步骤

1. 源码来自 git 仓库 https://gitlab.com/osm-c-tools/osmctools.git，tag 0.9
2. 克隆 git 仓库后创建 tar.gz 包供 init-build 使用（init-build 不支持 git URL）
3. `autoreconf -fi` 生成 configure 脚本（源码来自 git 仓库，不包含预生成 configure）
4. `bash ./configure --prefix=/storage/Users/currentUser/usr/local`
5. 修改 config.status 中 `umask 077` 为 `umask 007`（HMDFS 平台适配）
6. 运行 `bash ./config.status` 生成 Makefile
7. `make -j1` 编译 osmfilter, osmconvert, osmupdate
8. `make install DESTDIR=$TEST_PREFIX` staging 安装
9. `ohc-run.py verify-build` 质量门禁 → PASS
10. `ohc-run.py package` 制作预编译包
11. `make install` 本地安装
12. `ohc-run.py finish osmfilter 0.9 built` 完成收尾

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 无法下载 git 仓库 URL | 脚本期望 tar.gz URL，不支持 git clone | 手动 git clone 并创建 tar.gz，用 file:// URL |
| 2 | autoreconf -fi 需要手动运行 | git 仓库不包含预生成的 configure 背景脚本 | 运行 autoreconf -fi 生成 configure |
| 3 | config.status 创建临时目录写入文件 Permission denied | HMDFS 文件系统 umask 077 创建的目录不允许写入（即使 owner） | 修改 config.status 中 `umask 077` 为 `umask 007`，允许 group 访问 |

## 源码修改

无补丁。仅修改了生成的 config.status（umask 077 → umask 007），这是平台适配而非源码修改。

## 依赖版本

- zlib（系统已安装，osmconvert 迨行时动态链接）

## 功能测试结果

使用自建测试数据（3个节点、1条路径、1个关系，包含 amenity/highway/name 等标签）：

### osmfilter 测试

| 测试项 | 命令 | 结果 |
|--------|------|------|
| 版本信息 | `osmfilter --help` | 输出 "osmfilter 1.4.4"，✅通过 |
| 标签过滤（保留highway） | `osmfilter test.osm --keep=highway -o=out.osm` | 正确保留 highway 标签元素，✅通过 |
| 标签删除（移除amenity） | `osmfilter test.osm --drop-tags=amenity -o=out.osm` | 正确移除 amenity 标签，✅通过 |
| 精确值过滤 | `osmfilter test.osm --keep=amenity=cafe -o=out.osm` | 仅保留 amenity=cafe 节点，✅通过 |

### osmconvert 测试

| 测试项 | 命令 | 结果 |
|--------|------|------|
| 版本信息 | `osmconvert --help` | 输出 "osmconvert 0.8.10"，✅通过 |
| OSM→PBF转换 | `osmconvert test.osm -o=test.pbf` | 480字节 PBF 文件，✅通过 |
| OSM→o5m转换 | `osmconvert test.osm -o=test.o5m` | 198字节 o5m 文件，✅通过 |
| PBF→OSM反向转换 | `osmconvert test.pbf -o=back.osm` | 数据完整还原，✅通过 |
| 统计信息 | `osmconvert test.osm --out-statistics` | 正确显示3节点/1路径/1关系，✅通过 |

### osmupdate 测试

| 测试项 | 命令 | 结果 |
|--------|------|------|
| 版本信息 | `osmupdate --help` | 输出 "osmupdate 0.4.5"，✅通过 |

### 二进制属性检查

| 项目 | osmfilter | osmconvert | osmupdate |
|------|-----------|------------|-----------|
| 文件类型 | ELF 64-bit aarch64 dynamic | ELF 64-bit aarch64 dynamic | ELF 64-bit aarch64 aarch64 dynamic |
| 动态链接 | libc.so | libc.so | libc.so |
| 本地安装大小 | 166,336字节 | 362,944字节 | 55,680字节 |
| 打包后大小 | 219,008字节 | 370,560字节 | 79,680字节 |

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| osmfilter-0.9-ohos-aarch64.tar.gz | 673,915字节 | 预编译包（包含3个二进制） |
| osmfilter-0.9-ohos-aarch64-debug.tar.gz | 119,846字节 | 调试符号包 |

## 注意事项

- 源码 URL 为 git 仓库，需要先 clone 再打包为 tar.gz 供 init-build 使用
- HMDFS 上 config.status 的临时目录需要 umask 007（而非 077），否则 Permission denied（E081）
- osmctools 包含三个工具：osmfilter、osmconvert、osmupdate，osmconvert 运行时需要 zlib
- G0 干净构建验证失败：tarball 不含 configure 脚本（git 仓库需 autoreconf），需手动介入

---
**编译结束**: 2026-06-16
**最终状态**: built
---

**编译结束**: 2026-07-21 10:51
**最终状态**: built
