# libwps 0.4.11 适配笔记

## 编译环境

- 构建系统: autotools（dist 自带预生成 `configure`，GNU Autoconf 2.69；单一 configure）
- 平台任务: contrib-14198（libwps 0.4.11），claimer j669539
- 目标平台: HarmonyOS PC arm64（`os=OHOS arch=armv8 compiler=clang 15 libc++`），本机原生构建
- 编译器: clang/clang++ 15.0.4
- 依赖: `librevenge/0.0.5`、`zlib/1.3.1`（zlib 不被 configure 探测，但 librevenge 静态库链接需要 `-lz`）
- 上游: 项目主页即 SourceForge（https://sourceforge.net/projects/libwps/）
- 源码 sha256: `48e2fd81758a785914ab415279027ffbaaa76da39db6bff477f76e580d3eaf85`（与 best_release.json 官方元数据一致）
- 状态: built（G0-G4 全过，库级 10/10 + CLI 级 5/5）

## 源码面貌（摸底结论）

- 主体 **C++**：`src/lib/` 大量 `.cpp`（WPS/Lotus/Quattro/Multiplan/MSWrite/DosWord/XYWrite 等格式解析器）；`src/conv/` 是转换工具（wps2html/wps2raw/wps2text/wks2csv/wks2raw/wks2text 共六个），`src/fuzz/` 是 fuzzer（默认关）
- 交付形态：静态库 `libwps-0.4.a` + 头 `include/libwps-0.4/libwps/{libwps.h,WPSDocument.h}` + 六个 CLI 工具 + `libwps-0.4.pc`
- 依赖探测（configure.ac 实读）：
  - `PKG_CHECK_MODULES([REVENGE],[librevenge-0.0])`（必需）
  - `--enable-tools` **默认 yes** → 额外需要 `librevenge-generators-0.0` 与 `librevenge-stream-0.0`
  - **无 boost 检查**：configure.ac 无 AC_CHECK_HEADERS(boost/...)，src/ 源码 grep 无 boost 引用（与 libwpd 的关键差异，配方少一个 tool_requires）
  - libwpd/libwpg 是并列兄弟库（同属 DLP），**不是 libwps 的依赖**
- 上游**无测试套件**：无 `TESTS`/`check_PROGRAMS`、无 test 目录、无 `*test*` 源文件，也不分发 Works 样例文档

## 编译步骤（设备实机）

```sh
cd ~/huawei/worktrees/j669539/libwps-0.4.11
conan create archives/l/libwps/0.4.11 -pr:h=~/.conan2/profiles/ohos-aarch64 --build=missing -c tools.build:jobs=2
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SourceForge 下载 404/连接失败（多种 URL 形态） | SF 的文件 URL 路径结构按项目而异，盲猜形态失败；且 SF 下载重定向对 TLS 抖动敏感 | 用 `https://sourceforge.net/projects/libwps/best_release.json` 一次拿到官方 `url` 与 `sha256sum`；实测直链 `https://downloads.sourceforge.net/project/libwps/libwps/libwps-0.4.11/libwps-0.4.11.tar.bz2` 可用（与 libwpd 同形态）；重试间隔拉长即可穿过抖动 |
| 2 | （预期项）configure 阶段 `C compiler cannot create executables` | conan 的 `AutotoolsToolchain` 只把 CC/CXX 写进自己的 env 脚本，裸 subprocess 看不到 | `_compiler_environment_items()`：从 profile 的 `tools.build:compiler_executables` 显式导出 `CC`/`CXX`（R33，继承 libwpd #1） |
| 3 | （预期项）设备无 pkg-config，三处 `PKG_CHECK_MODULES` 无法通过 | `PKG_CHECK_MODULES` 在对应 `<PREFIX>_CFLAGS` 非空时短路，不调用 pkg-config | 分别导出 `REVENGE_*`、`REVENGE_GENERATORS_*`、`REVENGE_STREAM_*` 三组变量（`*_LIBS` 带 `-lz`，静态库场景必须；继承 libwpd #6） |
| 4 | （预期项）链接时报 `libtool: error: cannot find the library '//lib/librevenge-0.0.la'` | librevenge 用 `--prefix=/` + DESTDIR 打包，其 `.la` 里 libdir='//lib'；libtool 在 `-L` 目录里优先找 `.la` | `-L` 指向构建目录内只放 `.a` 不放 `.la` 的干净目录（`_clean_link_dir()`，继承 libwpd #4/#5） |
| 5 | 消费者测试首版 makeWorksV2 的 size 兜底写在 vector 构造后 | 逻辑顺序缺陷（size<2 时仍先按原 size 构造） | 兜底前置到构造之前 |

## 源码修改

无补丁，未改动上游任何源码。

## 依赖版本

- `librevenge/0.0.5`（文档模型基础库；静态库，其 stream 层需要 `-lz`，已随 `REVENGE*_LIBS` 传递）
- `zlib/1.3.1`

## 验证结果（设备实机实测，2026-09-30）

见 PR 正文统计表（库级 10/10 + CLI 级 5/5，`conan create` 全绿）。

## 可复用要点（对同族 DLP 库适用）

1. **SourceForge 官方元数据 API**：`best_release.json` 直接给 url/sha256/md5/字节数——同类 SF 上游库的 conandata URL 与 sha256 应从这拿，别猜路径；
2. libwpd 的 OHOS 机器（三组 REVENGE 变量、干净 -L 目录、CC/CXX 导出、bash/umask/config.sub 四段名）对 libwps **全部原样成立**——同族库配方迁移成本主要在依赖面差异核查（boost 有无）与交付物盘点（库名/头路径/工具清单）；
3. Works v2 正例可程序化构造（`{byte0<6, 0xFE}` + ≥0x100 字节），无需样例文档即可对格式识别做正向断言。
