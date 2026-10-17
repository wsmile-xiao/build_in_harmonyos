# wmget 0.6.1 适配笔记

## 编译环境
- 构建系统: custom（上游仅 configure.ac/Makefile.am、无预生成 configure，13 个 .c 直编等价替代 automake 链路）
- 编译日期: 2026-09-27
- 编译器: clang 15.0.4（OHOS SDK 26.0.0.18，/data/service/hnp/bin/clang）
- 状态: built

## 编译步骤

1. W0 依赖预检：`bash ci/scripts/preflight_check.sh wmget/0.6.1 --deps "libx11/6.4.0 libxext/6.4.0.1 libxpm/3.5.17 curl/8.15.0.1"` → 全部已发布（RC=0）；
   并以精确 `conan install --requires=… --build=never` 实测四依赖 binary 全部可下载（R35 口径，未用通配 conan list）。
2. 货源核验：官方 `https://www.dockapps.net/download/wmget-0.6.1.tar.gz` 3 次采样 GET，均 35538 字节、
   sha256=`cd3ed1106acfdc3857fc84eb385aa0c0706117e6e3e0abf38d8104d11b3e1189`；与 Debian pool
   `wmget_0.6.1.orig.tar.gz` 字节一致（同 sha256）。conandata.yml 采用官方 URL（PF7）。
3. R47 语言预检：`ohc-run.py lang-preflight wmget 0.6.1` → detected=c，任务 cpp，c↔cpp 兼容族，通过。
4. 依赖确认（读源码，非 SCT 转述）：configure.ac 声明 x11/xext/xpm/libcurl；源码实际使用
   Xlib（dockapp/da_x.c、server.c）、XShape（X11/extensions/shape.h）、XPM（X11/xpm.h）、
   curl（retrieve.c）；libdockapp 为 vendor 副本（dockapp/ 目录 3 个 .c），无需外部 dockapp 依赖。
5. 构建（conanfile.py build() 直编）：`clang $CFLAGS -O2 -Wall -o wmget <13 个 .c> <依赖 -I/-L/-l>`，
   编译器与标志均来自 conanbuild 环境（AutotoolsToolchain 生成，含 OHOS triplet/sysroot），
   并带「CFLAGS 为空即 exit 9」守卫（R33）。
6. test_package：编译 test_wmget.c，断言产物 ELF（magic + e_machine=EM_AARCH64），
   fork/exec 真跑 `wmget --version` 与 `wmget --help`（均退出码 0，CLI 契约无头可验）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 全新 CONAN_HOME 下 preflight 把全部依赖误报"未发布" | 新 home 只配了 conancenter，缺 ohpcd remote | `conan remote add ohpcd https://conan.cnb.cool/…` + disable conancenter，并从同任务族 home 对齐 ohos-aarch64 profile |
| 2 | `conan install` 报 Version conflict: libx11/6.4.0 vs libx11/1.8.13 | 已发布的 libxext/6.4.0.1 要求配套版本 libx11/6.4.0（同一套 X11 栈版本方案） | 改用配套版本组合 libx11/6.4.0 + libxext/6.4.0.1（1.8.13 与 6.4.0 不可同图） |
| 3 | init-build 解包只落了 dockapp/ 子目录（源文件统计 c:3） | 提取逻辑对该 tarball 目录结构处理不全 | 不影响正式构建：conan create 由 source() 的 get(strip_root=True) 自行完整解压 |
| 4 | 探针：`shmget()` 编译链接通过，运行即 Signal 31（SIGSYS）core dump，rc=159 | OHOS PC 内核对 SysV IPC 运行期拦截（seccomp 面）；对照 POSIX `shm_open` 同机正常（rc=0） | 编译不受影响，配方无需补丁；机制已沉淀知识草稿 DRAFT-wmget-0.6.1-sysv-shm-sigsys-seccomp（kv+md） |

## 源码修改

无补丁（上游源码原样编译通过，无一处修改）。

## 依赖版本

- libx11/6.4.0（Xlib；注意：制品仓已发布的 X11 栈为 6.4.0 方案，libxext/6.4.0.1 强依赖它）
- libxext/6.4.0.1（XShape；1.3.7 尚未发布、归档目录有他人适配在途脏件，本包未使用该版本）
- libxpm/3.5.17（libXpm.so，X11/xpm.h）
- curl/8.15.0.1（libcurl）

## 验证结果

```bash
# W0（精确依赖 binary 实测）
$ conan install --requires=libx11/6.4.0 --requires=libxext/6.4.0.1 \
    --requires=libxpm/3.5.17 --requires=curl/8.15.0.1 --build=never …
Install finished successfully   # 四依赖 binary 全部从 ohpcd 下载

# W3 conan create（conan-verify 内嵌）
Verdict: PASS   # 详见 conan-verify 日志

# test_package（消费者冒烟）
wmget test_package: ELF OK (aarch64); --version/--help rc=0

# K0 CLI 契约（K0 要求 --help/--version rc=0，实测真机运行）
$ wmget --version ; echo rc=$?
wmget 0.6.1 … ; rc=0
$ wmget --help ; echo rc=$?
usage 输出; rc=0
```

## 上游测试申报（R51 三步法）

- 上游测试清点：源码树仅 `wmget-test.pl`（手工联调脚本：起 dock 服务器 + 真实 HTTP 下载，
  依赖 X11 显示与外网），`Makefile.am` 无 `check` 目标，无 ctest/pytest 注册 → 上游无成体系
  自动化测试。
- 实测：X11 显示环境在本机不可用（无头），`wmget-test.pl` 无法运行；test_package 以
  test_wmget.c 补位（3 项断言：ELF 产物 + `--version` rc=0 + `--help` rc=0，全部通过）。

## 平台事实（真机探针证据）

- `shmget(IPC_PRIVATE, 4096, IPC_CREAT|0600)` 探针：**编译链接通过，运行即
  Signal 31 (SIGSYS) core dumped，退出码 159**，可稳定复现。
- 对照组 `shm_open("/wmget_probe", O_CREAT|O_RDWR, 0600)`：正常（fd 分配成功，rc=0）。
- 影响：wmget 的 dock 服务器模式（server.c `init_shmem()`，shmget+shmat）在该平台启动即崩；
  CLI 子命令不受影响。dock 模式本就需 X 显示，属无头环境不可测面。

## 注意事项

- **dock 服务器模式为 UI/运行期受限面**：`wmget dock` 需 X11 显示且 SysV shm 运行期被
  SIGSYS 拦截；本包验证口径为 CLI 契约 + 产物 ELF/链接层（消费者视角）。
- 制品仓 X11 栈用 6.4.0 版本方案：libxext/6.4.0.1 与 libx11/1.8.13 不可共存同一依赖图。
- `wmget list`/`cancel`/`request` 在无服务器时以套接字连接失败报错退出（属预期行为），
  不触碰 X 与 shm。
---

**编译结束**: 2026-09-27 03:59
**最终状态**: built
