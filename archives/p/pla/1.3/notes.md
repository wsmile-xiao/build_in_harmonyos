# pla 1.3 适配笔记

## 编译环境
- 构建系统: makefile（普通 Makefile，无 configure；通过 pkg-config 发现 cairo）
- 编译日期: 2026-09-02
- 编译器: clang 15.0.4（aarch64-unknown-linux-ohos，native OHOS 构建）
- 状态: built

## 编译步骤

pla 为普通 Makefile 工程，没有 configure。其 Makefile 通过
`pkg-config --cflags/--libs cairo` 取得 cairo 的头文件路径与链接库，因此关键是
在 make 前提供 cairo 的 pkg-config 环境：

```bash
# 1) 用 conan 拉取 cairo 依赖并生成 .pc（PkgConfigDeps）
conan install . -pr:h=ci/conan/profiles/ohos-aarch64 \
                -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
#    → 生成 cairo.pc / pixman-1.pc / libpng.pc / fontconfig.pc / freetype2.pc / expat.pc

# 2) make（显式给出 CC 与 PKG_CONFIG，PKG_CONFIG_PATH 指向 .pc 目录）
make pla CC=<clang> PKG_CONFIG=<pkg-config> PKG_CONFIG_PATH=$PWD -j1
```

正式配方将上述固化到 `generate()`（PkgConfigDeps + PKG_CONFIG_PATH + 清空
LD_LIBRARY_PATH）与 `build()`（`make pla CC=$(conf cc) PKG_CONFIG=$(which pkg-config)`）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `conan create`/链接期 clang 无法启动 lld（lld 报 libxml2.so.16 符号错误） | 宿主 shell 的 `LD_LIBRARY_PATH` 含 `/usr/local/lib`，其 libxml2.so.16 遮蔽 OHOS SDK lld 自带依赖（知识 E132） | 配方 generate() 将 `LD_LIBRARY_PATH` 置空，构建与链接与宿主污染隔离 |
| 2 | pla 运行时 "Error loading shared library libpixman-1.so.0 ..." 且所有 .so 都加载失败 | HarmonyOS HMDFS 动态加载器无法跟随 .so 符号链接（知识 E073）：conan 缓存中 pixman/libpng/fontconfig/freetype/expat 的 .so 是符号链接，唯 cairo 实体文件能加载 | test_package test.sh 对 conanrun 给出的各库目录做"实体文件 staging"（cp 真实文件到临时目录）后再执行 pla；实体文件全部可正常加载 |
| 3 | `make` 依赖 `$(shell which pkg-config)` 时偶发 `make: --cflags: No such file or directory` | Makefile 递归展开 `which pkg-config` 的不确定性 | 配方在 make 命令行显式传 `PKG_CONFIG=<绝对路径>`（GNU make 命令行变量覆盖 Makefile 内赋值），消除对 which 的依赖 |
| 4 | Fontconfig error: Cannot load default config file | OHOS 无 /etc/fonts/fonts.conf | 非致命：pla 仍成功输出 PNG/SVG/PDF/EPS（SVG 内含字形轮廓），仅 stderr 提示 |
| 5 | 交付态复验：本沙箱 github.com 直连被禁，直接 `conan create`（官方 URL conandata）无法联网下载 | 沙箱出网限制（github.com/ghfast.top 超时；gitcode.com/cnb.cool/curl.se 可达） | 启用 conan `core.sources:download_cache`（global.conf 配置），把官方归档（sha256=966ff0de…，内容已按 sha 校验）预置为缓存种子；conan 以内容 sha256 键控命中缓存，日志显示 `Source https://github.com/... retrieved from local download cache`，等价于官方 URL 下载并完成 sha 校验。CI 侧另有 predl/file 镜像改写仅用于本机构建提速，交付 conandata.yml 始终保持官方单一 URL（R39） |

## 源码修改

无。pla 1.3 源码无需修改即可在 OHOS PC 编译运行（零补丁）。

## 依赖版本

- cairo/1.18.4（唯一直接三方依赖）
- 传递依赖：pixman/0.46.4、libpng/1.6.58、fontconfig/2.18.1.1、freetype/2.14.3、
  expat/2.8.2.1、zlib/1.3.1.1（均已发布于 ohpcd 制品仓，R36 满足）
- 系统基础库：libc/libm/libpthread

## 验证结果

```bash
# 探索性编译 + 功能验证（R40 深度适配验证：图形输出工具需真实产出图形文件）
pla -i sample.pla -o out.png -f png -l en   # rc=0, out.png: PNG 374x97 (7KB)
pla -i sample.pla -o out.svg -f svg -l en   # rc=0, out.svg: SVG 文本 53KB
pla -i sample.pla -o out.pdf -f pdf -l en   # rc=0, out.pdf: PDF 1.7
pla -i sample.pla -o out.eps -f eps -l en   # rc=0, out.eps: EPS 文本
# PNG/SVG/PDF/EPS 四类后端均真实产出图形文件，确认 cairo 适配完整（R40）

# 配方级验证
# （交付态复验，官方 URL conandata；经 core.sources:download_cache 命中 sha=966ff0de 的官方归档）
conan create archives/p/pla/1.3 -pr:h=ci/conan/profiles/ohos-aarch64 \
         -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing \
         --user=ohpcd --channel=stable   # test_package 真实执行 pla 渲染 PNG
# Exported: pla/1.3@ohpcd/stable#7a35b1ca2185cfa6b3d77179c78f51e0
# Created package revision fe87c90b7a08edd4dde2764e260ff7fa
# (同配方 conan-verify / W3 亦通过，reports/conan-create.log 为上述官方-URL 复验日志)
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Makefile 型应用配方（application，bindirs=bin） |
| conandata.yml | 官方归档 URL + sha256 |
| test_package/ | conanfile.py + test.sh（真实渲染 PNG）+ MANIFEST.yml |
| commands.json（软件级） | R38 命令行工具声明 |

## 注意事项

- 本机为 HMDFS 文件系统：动态加载器无法加载 .so 符号链接（E073），这是平台限制，
  运行/验证工具类共享库程序时必须先把依赖库落成实体文件（test_package 已内置该逻辑）。
- 本机宿主 shell 的 `LD_LIBRARY_PATH` 含冲突 libxml2（E132），凡本机手动运行需依赖
  lld 的链接前应 `env -u LD_LIBRARY_PATH` 或由配方 generate() 置空。
- pla 对未知参数打印 usage 且返回 0（`pla --version`/`--help` 亦可作为 CLI 冒烟入口）。
---

**编译结束**: 2026-09-02 21:28
**最终状态**: built
