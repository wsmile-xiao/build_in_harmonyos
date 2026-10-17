# jaaa 0.9.2 适配笔记

## 编译环境
- 构建系统: makefile（上游只有 `source/Makefile`，无 configure / cmake / meson 入口）
- 编译日期: 2026-09-26
- 编译器: clang/clang++，取 profile 的 `tools.build:compiler_executables`（create1.log 第 27 行原文：`tools.build:compiler_executables={'c': '/data/service/hnp/bin/clang', 'cpp': '/data/service/hnp/bin/clang++'}`）；其余 settings/options 见 create1.log 的 `Input profiles` 段，profile 为仓内 `ci/conan/profiles/ohos-aarch64`（`-pr:h` 与 `-pr:b` 同给）
- 状态: built

## 编译步骤

1. `conan create archives/j/jaaa/0.9.2 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=jaaa --build=missing`
   （构建设备侧经 `~/tmp/uc2/build-slot.sh --kind short` 占机动槽，未绕闸）
2. `build()`：`apply_conandata_patches` → 收集全部声明依赖的 `includedirs`/`libdirs` →
   `make -C source -j1 PREFIX=/ CXX=<profile 编译器> PCONFCFL="<-I. -DCLTHREADS_NO_PTHREAD_CANCEL + 各依赖 -I>" LDFLAGS="<各依赖 -L>" jaaa`
   （实测命令行见 create1.log 第 157 行；编译行见第 159/168/178/187/188 行，其中 `-DVERSION=\"0.9.2\" -DPREFIX=\"/\"` 由上游 `CPPFLAGS` 生成）
3. `package()`：`make -C source install PREFIX=/ DESTDIR=<package_folder>`（create1.log 第 197 行）
   —— 上游 install 规则确实是 `$(DESTDIR)$(BINDIR)` 形式，但 `BINDIR` 派生自 `PREFIX ?= /usr/local`，
   而 `PREFIX` 同时被 `-DPREFIX` 烧进二进制；故用 `PREFIX=/` 让暂存布局落在 `DESTDIR/bin`，
   并使产物内的前缀是 `/` 而不是宿主默认的 `/usr/local`（由产物层断言 `artifact-no-host-prefix-leak` 全字节扫描兜底）
4. 上游**没有** check/test 目标可跑（见下节与 `test_package/MANIFEST.yml`），故 `build()` 内无测试步骤，消费者测试放在 `test_package/`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游 `CXXFLAGS += -march=native` | 交叉工具链下 `-march=native` 以构建机 ISA 为准，会把宿主特性烧进 OHOS 产物（且 OHOS clang 对该取值支持不稳） | 补丁摘掉该旗标（`patches/0001-source-Makefile.patch` 第 3 处删除行）。同处方既有条目：`DRAFT-genann-1.1.1-make-cflags-march-native-override` |
| 2 | 上游 `CPPFLAGS += $(shell pkgconf --cflags freetype2)` 恒为空/探测不可依赖 | 上游 Makefile 直接 shell 调用 `pkgconf` 取 FreeType 旗标；本环境不依赖它给出正确结果 ⇒ 头路径进不来。与 `E468`（PkgConfigDeps 写了 .pc 但没把目录加进 `PKG_CONFIG_PATH`，上游探测拿不到 Conan 元数据）同一症状族 | 补丁把该行替换为 `$(PCONFCFL)` 注入槽，由 `build()` 把 12 个依赖的 `includedirs` 逐个 `-I` 填进去。**用注入槽而不是覆写 `CPPFLAGS`**，是为了保住上游自己的 `-DVERSION` / `-DPREFIX` 定义不被清掉 |
| 3 | clthreads 在 OHOS 需要 `CLTHREADS_NO_PTHREAD_CANCEL`（musl/OHOS 无 `pthread_cancel`） | clthreads 的 `package_info()` 只对该宏走 CMakeDeps 消费者生效，本包是裸 make 构建，不消费 CMakeDeps 变量 | `build()` 内当 `settings.os == OHOS` 时把 `-DCLTHREADS_NO_PTHREAD_CANCEL` 拼进 `PCONFCFL`（create1.log 第 159 行编译命令可见该宏） |
| 4 | 上游 `install` 规则用裸 `install` 命令 | 裸命令依赖 PATH 且不可固定：本次探针所在的非登录 PATH 下 `command -v install` 无输出（仅覆盖该 PATH 组合，不声称设备上全局没有 install） ⇒ 打包步骤不可依赖 | 补丁引入 `INSTALL ?= /bin/install`，把安装器变成可覆写变量并给绝对路径默认值；`package()` 未覆写它，实测以默认值完成打包（产物 `bin/jaaa` 88576 字节存在且被 `test_package` 的产物断言读取） |
| 5 | 构建主机无 X server、无 JACK 服务、无采集设备：jaaa 是 X11 GUI + JACK/ALSA 音频分析器，"跑得起来看频谱"不是可达的通过条件 | 平台没有显示后端（既有条目 `E471`），X11 侧消费者契约见 `E530` | 消费者测试分三层并逐条打印机器可读判决：产物层 4 条（ELF 机器码 / DT_NEEDED 全是裸 soname / `.codesign` 段数 / 二进制内无宿主前缀）、装载＋进程层 3 条（真实执行 `jaaa -h` 断言版本横幅与上游自身的 `exit(1)`；无参运行断言失败落在 `Can't open display` 且退出码不是 127/126）、能力层 3 条逐用例 `JAAA_TEST_SKIP` 带原因（JACK 连接 / ALSA 采集 / GUI 渲染），**没有把不可执行记成通过** |
| 6 | `conan create` 跑测试时会把 `test_package/runtime-libs`、`staged-bin`、`smoke-work` 落在**归档树内**（无扩展名 ELF 与 .so 副本），而仓内 `.gitignore` 只挡 `*.so` | `test_package/conanfile.py` 以 `self.build_folder` 派生这三处，create 期间该路径解析到源码目录 | 出厂前 `rm -rf` 这三处（每次测试会重建，不丢东西），跑完 `run` 再回读 PR 文件表与 `git status` 二次确认归档内无二进制 |

## 源码修改

`patches/0001-source-Makefile.patch`（`patch_type: portability`），只动 `source/Makefile` 一个文件的 4 处：

1. 新增 `INSTALL ?= /bin/install`
2. `CPPFLAGS += $(shell pkgconf --cflags freetype2)` → `CPPFLAGS += $(PCONFCFL)`
3. 删除 `CXXFLAGS += -march=native`
4. `install` 规则的 `install -d` / `install -m 755` → `$(INSTALL) -d` / `$(INSTALL) -m 755`

未改动任何 `.c/.cc/.h`；未做与移植无关的重排或格式化。

## 依赖版本

`conanfile.py` 的 `requirements()` 精确钉版（全部经 `preflight`/`conan-verify` 取到已发布二进制）：

- GUI/X11（**1.8.13 轨**，与 libdockapp 系所在的 6.4.0 轨不是同一条轨，混轨会在同一依赖图里 fork 出两套 X11 闭包）：
  `clxclient/3.9.2`、`clthreads/2.4.0`（clxclient 钉的是 2.4.0，不是制品仓里也有的 2.4.2）、`libxft/2.3.8`、
  `libx11/1.8.13`、`xorgproto/2025.1`、`fontconfig/2.18.3`、`libxrender/0.9.12`、`freetype/2.14.3`
- 音频后端（jaaa 同时直链 `-ljack` 与 `-lasound`）：`jack/1.9.22`、`zita-alsa-pcmi/0.6.1`、`alsa-lib/1.2.16`
- DSP：`fftw3f/3.3.10` —— 单精度 FFTW 在制品仓里是**独立包名** `fftw3f`（`conan list "fftw3f/3.3.10" -r=ohpcd` 实测
  `Found 1 pkg/version recipes matching fftw3f/3.3.10 in ohpcd`），不是 `fftw` 包的一个组件；上游链接旗标是 `-lfftw3f`

## 验证结果

```bash
# 构建与打包（真实执行过 make 的那一轮）
~/tmp/uc2/z63-jaaa/create1.log:157  RUN: make -C ".../b/source" -j1 PREFIX=/ CXX="/data/service/hnp/bin/clang++" PCONFCFL=" -I. -DCLTHREADS_NO_PTHREAD_CANCEL ..." jaaa
~/tmp/uc2/z63-jaaa/create1.log:197  RUN: make -C ".../b/source" install PREFIX=/ DESTDIR=".../p"

# W3 阻塞门禁（conan-verify）
~/tmp/uc2/z63-jaaa/verify2.log:  G1 PASS / G2 PASS / G3 PASS ⇒ ✅ 配方验证通过: jaaa 0.9.2

# 消费者测试（断言脚本定稿后重跑的那一轮）
~/tmp/uc2/z63-jaaa/create5.log:203-205,458  JAAA_ARTIFACT_PASS machine=AArch64 / needed=... / host_prefix_leak=none / codesign_sections=1
~/tmp/uc2/z63-jaaa/create5.log:460-462      JAAA_TEST_PASS load banner=Jaaa-0.9.2 / load exit_code=1 / process exit_code=1 signature=Cant-open-display
~/tmp/uc2/z63-jaaa/create5.log:463-465      JAAA_TEST_SKIP case=jack-client-connect|alsa-capture-open|gui-render
~/tmp/uc2/z63-jaaa/create5.log:466          JAAA_SMOKE_PASS load=2 process=1 skipped=3 failed=0
CREATE5_RC=0
```

- 编译状态：通过
- 上游测试用例通过率：0/0（上游静态测试数为 0，属清点结论而非环境结论；三条实测证据见 `test_package/MANIFEST.yml` 的 `upstream_zero_evidence`）
- 新增测试用例通过率：7/10（其余 3 条为能力层用例，构建主机无 X server / 无 JACK 服务 / 无采集设备，逐条声明 skipped 并带原因，未计入通过；分母保持真实申报数 10，未为凑 100% 缩小）
- 账本五维：`static_upstream_test_files=0` / `executable_test_cases=7` / `measured_passed=7` / `measured_skipped=3` / `measured_failed=0`；`test_case_count=10` / `assertion_count=8`

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| `bin/jaaa` | 88576 字节 | 打包后的可执行文件（本轮实测位于 `~/tmp/ch/home-jaaa/p/b/jaaabf3f475e0af0f/p/bin/jaaa`，`readelf -h` 回 `Type: DYN (Position-Independent Executable file)` + `Machine: AArch64`。⚠ 该目录名随配方修订变化，早前测到的 `jaaa93e0b80c8a7a8` 已被 Conan 缓存回收而不存在 ⇒ 复核时一律取当轮 create 日志的 Package folder，不要拿笔记里的旧绝对路径当事实） |
| `archives/j/jaaa/commands.json` | — | 软件级命令声明（R38/L0k：`package_type=application` 的包靠它声明可执行命令，`package_info()` 不导出 `cpp_info.libs`） |
| `archives/j/jaaa/manifest.yaml` | — | 软件级清单：OHOS 适配要点（含 X11 轨道、`$(CXX)` 是变量可覆写、`-lfftw3f` 需单精度组件）与版本索引 |
| `archives/j/jaaa/0.9.2/manifest.yaml` | — | 版本级清单：源码 sha256、构建系统、已应用补丁、本包知识条目 |
| `archives/j/jaaa/0.9.2/patches/0001-source-Makefile.patch` | — | 唯一上游补丁（4 处，全部为移植必需） |
| `archives/j/jaaa/0.9.2/test_package/{conanfile.py,test_jaaa.sh,MANIFEST.yml}` | — | 分层消费者测试与测试账本 |

## 注意事项

1. **X11 轨道**：本包走 1.8.13 轨（`libx11/1.8.13` + `libxft/2.3.8`）。要改成 6.4.0 轨必须先重新组图验证，不能只换版本号——同一依赖图里混轨会 fork 出两套 X11 闭包。
2. **编译器可覆写性**：jaaa 的规则里编译器是变量 `$(CXX)`，所以 `make CXX=...` 覆得到，不必像同作者姊妹包 jnoise 那样给"规则命令位置写死编译器名"打补丁。
3. **无头面**：GUI 渲染、JACK 连接、ALSA 采集三条在本设备上是**不可执行**而非"通过"。真正接上显示与音频后端的运行期验证未做，属已知限制。
4. `test_package` 的三个暂存目录（`runtime-libs`/`staged-bin`/`smoke-work`）会落在归档树内且不被 `.gitignore` 全挡（`staged-bin/jaaa` 是无扩展名 ELF），提交/建 PR 前必须清掉。
5. `create2`–`create5` 的 jaaa 包体都来自缓存（日志内 `make` 出现 0 次、无 Building 段），**build() 的真实执行证据只在 create1.log**；改动配方或补丁后必须确认新一轮日志里重新出现 `RUN: make`。
---

**编译结束**: 2026-09-26 05:32
**最终状态**: built
