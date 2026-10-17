# libgig

Gigasampler / GigaStudio 采样文件库（C++）。

## 简介

libgig 由 LinuxSampler 项目维护，提供对下列采样器文件格式的读写访问：

- **Gigasampler / GigaStudio**（`.gig`）—— 主格式，含乐器、区域、维度、样本与校验和表
- **DLS**（Downloadable Sounds，Level 1/2）
- **SoundFont2**（`.sf2`）
- **KORG** 采样文件
- **Akai** 磁盘/镜像（`libakai`）

库分为两大部分：底层的 RIFF 容器访问（`RIFF::File`/`Chunk`/`List`）与上层的格式语义层
（`gig::File`、`DLS::File`、`sf2::File`、`Korg::File`、`Akai`），并提供
`Serialization` 反射框架（含按运行时类型创建实例的注册机制）。

本包同时交付上游 `make install` 的 **14 个命令行工具**：
`rifftree` `dlsdump` `gigdump` `gigextract` `gigmerge` `gig2mono` `gig2stereo`
`sf2dump` `sf2extract` `korgdump` `korg2gig` `akaidump` `akaiextract` `wav2gig`。

## 官网

https://www.linuxsampler.org/libgig/

## 许可证

LGPL-2.1-or-later（见 `4.5.2/` 包内 `licenses/COPYING`）。

## 依赖

| 依赖 | 用途 | 是否可省 |
|------|------|----------|
| `libsndfile/1.2.2` | `gigextract`/`sf2extract`/`akaiextract`/`wav2gig` 写音频文件 | 否，`configure` 缺则 `exit -1` |
| `libuuid/2.42.2` | DLSID / `.gig` 文件 UUID 生成 | 否，非 mac/win32 平台缺 `uuid_generate` 则 `exit -1` |

两者在本制品仓均为**静态**包，因此 libgig 亦按静态交付（`--enable-static --disable-shared`）。

## OHOS 适配要点

1. **静态链接下的静态初始化顺序缺陷**（本包真机实测）：库内 `static std::map
   DataType::m_nativeTypes`（`Serialization.cpp`）为动态初始化，而消费者 TU 的全局
   `NativeDataTypeRegistry<T>` 构造器会在自己的动态初始化阶段调用
   `DataType::registerNativeDataType<T>()`。静态链接时消费者对象排在库对象之前，
   构造器访问尚未构造的 map → 测试可执行文件在 `main()` 之前 SIGSEGV。
   补丁 0002/0003 把它改为**函数内 static 访问器**（首次使用即构造，与链接顺序无关）。
   shared 构建下 `.so` 的初始化先于可执行文件，该缺陷被掩盖。
2. **libtool 绝对 RUNPATH**：上游 `pkglib_LTLIBRARIES` 装在 `$(libdir)/libgig/`，
   `--prefix=/` 下 libtool 给 14 个工具写入 `RUNPATH=//lib/libgig`（不存在的路径），
   裸环境运行报 `Error loading shared library libgig.so.13`。改为静态后工具自包含
   （无 `DT_NEEDED`、无 `RUNPATH`），从结构上消除该面。
3. **CLI 长选项**（E503）：上游 14 个工具只支持短选项 `-v`；补丁 0004–0017 在 `main()`
   开头补 `--version`/`--help` 并 `return 0`，使打包 smoke 探针能真实覆盖每个交付二进制。
4. **HMDFS umask**（E011）：`configure` 内 `umask 077` 建出的临时目录在 HMDFS 上不可写，
   配方内联改为 `umask 022`。
5. **`config.guess` 不认 HarmonyOS**（E007）：`conan create` 不传 `--host/--build`，`configure`
   会走 `config.guess` 探测并在 HarmonyOS 上失败（其 `umask 077 && mktemp -d` 探测目录在
   HMDFS 上还不可写）；补丁 0001 加 `*:HarmonyOS:*:*` 分支短路该路径。
6. **libuuid 不走 pkg-config**（E007）：`configure.ac` 用
   `AC_CHECK_HEADERS`/`AC_SEARCH_LIBS`/`AC_CHECK_FUNCS`，需把依赖的 include/lib 目录
   注入 `CXXFLAGS`/`LDFLAGS`。

## 版本

| 版本 | 状态 | Conan 引用 | 说明 |
|------|------|-----------|------|
| 4.5.2 | built | `libgig/4.5.2` | 首次适配；上游测试 4 套 406 条断言全绿 |
