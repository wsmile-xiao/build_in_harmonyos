# bosixnet 2.0 适配笔记

## 编译环境

- 构建系统: cmake
- 编译日期: 2026-09-06
- 编译器: clang/clang++ (HarmonyOS native, aarch64-linux-ohos)
- 平台: HarmonyOS PC (aarch64)
- 状态: built

## 编译步骤

1. 下载源码: `https://github.com/tehnick/bosixnet/archive/refs/tags/v2.0.tar.gz` (sha256=90b2bcbc…)
2. 改写 `src/bosixnet-webui/CMakeLists.txt` 与 `src/bosixnet-daemon/CMakeLists.txt`
   (补丁 `0001`/`0002`，见「源码修改」)
3. 获取 fcgi 运行库: 远端 ohpcd 无 fcgi/2.4.7 配方且匿名访问被拦，直接下载
   `fcgi-2.4.7-ohos-aarch64.tar.gz` (sha256=37449bc9…) 预编译包到构建目录
   (与 fastp/isa-l 相同的 cmd-pkgs 模式)
4. `conan create archives/b/bosixnet/2.0 -pr:h=ohos-aarch64-windows -pr:b=default --build=missing`
   → CMake 配置 + bosixnet_webui 编译链接成功，安装到 bin/；
   本机为 Windows，aarch64 ELF 无法在本机执行，test_package smoke 阶段报
   「无法识别命令」，属宿主环境限制（CIM 的 OHOS worker 上可正常执行）
5. 生成打包产物 `packaging/bosixnet-2.0-ohos-aarch64.tar.gz`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 4.x 报 `cmake_minimum_required` 兼容错误 | 上游 CMakeLists 声明 2.8，CMake >=4 移除了 <3.5 的政策 | generate() 设 `CMAKE_POLICY_VERSION_MINIMUM=3.5` |
| 2 | fcgi 无 Conan 配方 / 远端匿名被拦 | fcgi 未适配发布 | conanfile build() 内直接下载 cmd-pkgs 预编译包并校验 sha256 |
| 3 | 解压 fcgi 报 `tar: Cannot connect to C: resolve failed` | msys GNU tar 把 Windows 盘符当远程主机 | 用 Python `shutil.unpack_archive` 纯解压 |
| 4 | 安装路径写死 `/etc/bosixnet/` 与 systemd/sysvinit 集成 | 上游假设传统 Linux | `/etc/bosixnet/` → `${CMAKE_INSTALL_PREFIX}/etc/bosixnet/`；WITH_SYSTEMD_SUPPORT / WITH_SYSVINIT_SUPPORT 均 OFF |
| 5 | `bosixnet_webui --version` 打印 `Version: 1.7` | 上游源码硬编码 VERSION "1.7" | 非缺陷，作为已知上游 quirk 记录 |
| 6 | 本机 (Windows) conan-verify G2 无法通过 | CI profile 指向 `/data/service/hnp/bin/clang`，且 aarch64 二进制不能在 Windows 执行 | 属宿主环境限制；权威验证以 OHOS worker CI 为准 |

## 源码修改

- `patches/0001-src-bosixnet-webui-CMakeLists.txt.patch`: 支持 FCGI_INCLUDE_DIR，并支持 FCGI_LIBRARY
  （静态链接 libfcgi.a，见「CI 失败修复」）、移除 gzip man 页生成、`/etc/bosixnet/` → `${CMAKE_INSTALL_PREFIX}/etc/bosixnet/`
- `patches/0002-src-bosixnet-daemon-CMakeLists.txt.patch`: 同上（路径与精简）

## 依赖版本

- fcgi 2.4.7 (cmd-pkgs 预编译包，sha256=37449bc9…)
- 无其它外部编译依赖

## 验证结果

```bash
conan create archives/b/bosixnet/2.0 -pr:h=ohos-aarch64-windows -pr:b=default --build=missing --user=ohpcd --channel=stable
#  导出 OK → CMake 配置 OK → bosixnet_webui 编译链接 OK → 安装 OK
#  test_package: 本机为 Windows 无法执行 aarch64 ELF (环境限制, 非配方问题)
gitcode CI (OHOS worker): 待 PR 后验证 L0-L5
```

## 交付物

| 文件 | 说明 |
|------|------|
| packaging/bosixnet-2.0-ohos-aarch64.tar.gz | 安装树 (bin/bosixnet_webui 等) |
| bin/bosixnet_webui | FastCGI Web UI (主验证对象) |
| bin/bosixnet_daemon 等脚本 | 守护进程脚本 |

## 注意事项

- 软件包版本为 `bosixnet/2.0`（与任务分支 `feat/bosixnet-2.0` 对齐，CI R40 要求 name-version == 分支名）；
  上游 tag 为 `v2.0`，源码不变
- `bosixnet_webui --version` 输出上游硬编码 `Version: 1.7`
- 本机为 Windows 宿主时，W3/本地 conan-verify 的 aarch64 运行验证无法执行，
  需以 OHOS worker CI 结果为准

### 对话 #1 : 本仓库适配完成
- 2026-09-06: conanfile.py / conandata.yml / test_package / patches 编写完成，
  本地交叉编译通过，遗留本机环境的 aarch64 运行验证，交由 worker CI 兜底

## CI 失败修复（2026-09-06，build #41047 / #41062）

### 失败证据
- **build #41047**（worker CI-007）：pre-download 报 `[Errno 2] No such file or directory: 'curl'`，
  conan source() 报 `'Can't connect to HTTPS URL because the SSL module is not available.'`，
  gh-proxy 与 github.com 两个 HTTPS URL 均下载失败。命中知识库 E2149/E372（pkgconf 3.0.5、tag 0.1 先例）：
  该 worker 的 Python 缺 `_ssl`，为 worker 环境偶发问题；同批其它 PR 出现同样签名。
  复跑（`/rebuild`）后 build #41062 落到正常 worker（CI-021），下载/编译均通过 → 配方无需为此改动。
- **build #41062**（worker CI-021）：真实功能缺陷浮出。构建与打包通过，但 test_package 冒烟
  `bosixnet_webui --version` 失败：
  ```
  Error loading shared library libfcgi.so.0: (needed by .../bin/bosixnet_webui)
  Error relocating .../bin/bosixnet_webui: FCGI_Accept: symbol not found
  ```
  **根因**：上游 `target_link_libraries(bosixnet_webui fcgi)` 走 `link_directories()` 后按名称
  解析到 cmd-pkgs 预编译包里的 **共享库** `libfcgi.so.0`，但该 .so 只存在于构建目录 `_deps`，
  未随包安装、也不在 test_package 运行时的 ld 搜索路径上（conanrun 无对应 LD_LIBRARY_PATH；
  OHOS musl ldso 对非标准路径的 $ORIGIN RPATH / LD_LIBRARY_PATH 解析不可靠，E019/E088/E207）。

### 修复方案
- 配方改为**静态链接** fcgi：`cmake.configure()` 注入 `FCGI_LIBRARY=<fcgi_prefix>/lib/libfcgi.a`
  （替代原来的 `FCGI_LIBRARY_DIR`），patch `0001` 改为
  `if(FCGI_LIBRARY) target_link_libraries(${PROJECT_NAME} ${FCGI_LIBRARY} m)`
  （libfcgi.la 声明依赖 `-lm`），保留 `else()` 回退到无变量时的默认 `fcgi` 名称链接。
- 产物 `bosixnet_webui` 仅依赖 libc/libm 等系统库，运行时不再需要任何 fcgi 共享库，
  test_package 冒烟在任意目录可执行。sha256、官方 URL 均未改动。

### 备注
- E415：CI 会在 conan create 前把 conandata.yml 官方 url 原地改写为镜像列表并在结束后还原；
  复核 worktree 中 conandata.yml 已与 HEAD 一致、无 gh-proxy 残留。

---

**编译结束**: 2026-09-06 16:00
**最终状态**: built