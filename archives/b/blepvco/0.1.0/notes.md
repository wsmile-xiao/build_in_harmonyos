# blepvco 0.1.0 适配笔记

## 上游识别

- blepvco 是 Sean Bolton 的 LADSPA 插件集（3 个 minBLEP hard-sync 振荡器），GPL-2+。
- 上游无公开 git 仓库，唯一发行物为官方 tarball：https://www.smbolton.com/linux/blepvco-0.1.0.tar.gz
  SHA256 `b4db27128f5d622a611136f7595202b479d0c9210bdb735be84a42af37c1ef5f`（94235 字节；
  本地与设备分别下载核验一致，设备经 https 跟随 301 重定向到 https://smbolton.com 同样一致）。
- 0.1.0 为唯一历史版本（Debian 打包史 0.1.0-1 → 0.1.0-5 印证）。

## 构建系统与适配

- 纯 GNU Makefile（无 configure/meson/cmake/pkg-config）：
  - 目标文件经 make 内建规则编译，吃 `$(CC)/$(CXX)` 与上游 `CPPFLAGS += -I. -fPIC -D_REENTRANT -Wall -O3`；
  - 链接规则硬编码 `g++ -shared ...`，是唯一不可注入点。
- 补丁 `0001-make-cxx-overridable.patch`（portability，1 行）：链接规则 `g++` → `$(CXX)`。
  配方经 `make -C <src> -j1 CC=... CXX=...` 注入工具链（R9/R33），上游 CPPFLAGS 原样保留。
- 依赖闭包仅 `ladspa.h`：以 `requires("ladspa-sdk/1.17")` 供给（制品仓已发布，R36 满足），
  未采用"头文件随配方"方式——仓库已有完整 ladspa-sdk conan 包（含 include/ladspa.h 导出），
  require 是 R27/R36 的标准路径，也避免向 GPL-2+ 源码树混入 LGPL 头文件副本。
- 无 GUI/无 X11/GTK/cairo/OpenGL/JACK，无内联汇编、无字节序依赖、不触及 musl 兼容面。
- 产物：`blepvco.so`（AArch64 OHOS ELF，NEEDED 仅 libc++_shared.so/libc.so，BIND_NOW），
  安装至包内 `lib/ladspa/`（LADSPA 目录惯例），插件由宿主 dlopen，`package_info` 不导出 include/lib。

## 上游测试

上游**无测试套件**，穷尽核验记录：

1. tarball 内容共 14 个文件（顶层 11 个：Makefile、7 个源码/头文件、README、AUTHORS、COPYING；extras/ 内 3 个：2 个 .ams 示例 + minblep.c 表生成器）——其中源码/构建文件 9 个、文档/许可 3 个、示例 2 个，无 test/ 目录、无任何 *test* 文件。
2. Makefile 目标仅 `blepvco.so`、`install`、`archive`、`clean`——无 test/check 目标。
3. README/AUTHORS 无任何测试相关说明（grep test/check 零命中）。
4. `extras/minblep.c` 含 `main()`，但它是当年生成 `minblep_tables.c` 的开发用**表生成器**（无断言、无 pass/fail、不在任何构建路径内），不构成测试入口；此前 Scout 报告称其"无 main"不准确，特此纠正。
5. 仓库辅助工具 `ci/tools/extract_upstream_tests.sh` 因硬编码 /tmp 无法在 OHOS（只读 /tmp）运行，改用上列人工穷尽核验；结论一致。
6. 替代验证：test_package 自带 dlopen 冒烟宿主（`src/test_ladspa_host.c`），加载 blepvco.so、
   遍历 `ladspa_descriptor()` 期望 3 个描述符（Sync-Saw/Rect/Tri-VCO，id 2184/2185/2186），
   逐个 instantiate → 全端口 connect_port → activate → run(64 帧) → deactivate → cleanup，
   全部成功且 exit 0 才 PASS。设备真机（ohos-aarch64，clang 15）实测通过。

## 构建链坑

- **上游服务器 x-gzip 与 conan 下载器不兼容**：smbolton.com（Apache `AddEncoding x-gzip .gz`）
  对 .tar.gz 响应带 `Content-Encoding: x-gzip`。urllib3 按该声明透明解压，conan 下载器把
  "读到的解压后字节数（296960）"与 "Content-Length（压缩尺寸 94235）"做比较且只豁免
  `content-encoding == "gzip"`（file_downloader.py），x-gzip 不在豁免之列 → 恒定报
  `Transfer interrupted before complete: 296960 < 94235`。296960 恰为 tarball 解压后尺寸，
  已实测坐实。配方 source() 增加只在此路径生效的 urllib 回退（不做 Content-Encoding 解码，
  原始字节落地与 Content-Length/sha256 一致），回退后仍有 SHA256 校验兜底。
  CI 的 curl 预下载步骤在本机也会失效（见下条），因此该回退是本包在设备 CI 上的必要路径。
- **CI 预下载的 curl 探测在本机失效（CI 基础设施缺陷，未修改 ci/\*\*）**：设备 Python
  （musl 构建）subprocess 走 `os.posix_spawn`，不做 PATH 搜索，CI 预下载
  `subprocess.run(["curl", ...])` 恒报 `FileNotFoundError: 'curl'`（/usr/bin/curl 实际存在，
  shell 与 shutil.which 均可找到）。此缺陷使所有包的预下载步骤在本机退化为 conan 直连下载，
  对普通服务器无影响，但与上一条叠加使本包首跑 CI 失败。已如实报告，由 Coordinator 决策。
- Conan 2.29 `self.run(env="conanbuild")` 在 env 脚本不存在时**静默跳过**（源码核验：
  `environment_wrap_command` 只对存在的文件包装）——配方必须显式
  `VirtualBuildEnv(self).generate()`，否则 profile `[buildenv]` 的 PATH/LD_LIBRARY_PATH
  （OHOS lld 依赖 libxml2.so.16）不会生效。
- profile conf 提供的编译器绝对路径在构建环境可能是死符号链接：沿用 ladspa-sdk 的防护——
  仅在目标为真实可执行文件时使用，否则回退 PATH 解析（`shutil.which`）再回退 HNP 常见位置。
- 设备 shell PATH 上的 `g++` 实为用户级 .harmonybrew 的 clang 别名，CI worker 不保证存在；
  这正是链接规则必须补丁为 `$(CXX)` 的原因。

## 配方结构

- `conanfile.py`：source() 从 conandata.yml 下载官方 tarball；build() 应用补丁 + make（-j1）；
  package() 拷贝 blepvco.so → lib/ladspa/、COPYING → licenses/；package_info() 空导出 +
  resdirs=lib/ladspa。
- `test_package/`：消费者视角 L1 冒烟（见上）。
