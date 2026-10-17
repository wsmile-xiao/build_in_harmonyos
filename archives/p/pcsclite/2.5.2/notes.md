# pcsclite 2.5.2 适配笔记（HarmonyOS PC / arm64）

> 适配人：j669539 | 任务卡 #14889 | 日期：2026-10-05
> 上游：https://github.com/LudovicRousseau/PCSC（tag 2.5.2）

## 1. 软件定位

pcsc-lite（pcsclite）是 PC/SC 智能卡中间件的参考实现：`SCard*` 客户端 API
（winscard.h）+ pcscd 资源管理守护进程。本次交付**客户端库 + 头文件**，
守护进程按 OHOS 可得性裁剪（见 §3）。

## 2. 源码与校验（双源实测）

- URL：`https://github.com/LudovicRousseau/PCSC/archive/refs/tags/2.5.2.tar.gz`（官方正主仓 tag tarball）
- SHA-256：`ca52f420194cef335114a10ca3b6369b64046f3d61d5b621595e0d487df18ce1`
- 双源一致性实测：GitHub archive tarball 与 salsa.debian.org/rousseau/PCSC
  （上游作者维护的同名镜像仓）tag tarball 逐字节一致（同 sha256）
- 官方发布站 `https://pcsc-lite.apdu.fr/files/` 从本环境不可达（网络出口限制），
  故采用 GitHub 官方仓 tag tarball（R39 单条官方 URL）
- `git ls-remote` 实测：2.5.2 为最新 tag

## 3. 构建系统与裁剪面（与任务情报的关键差异）

**上游 2.5.2 已从 autotools 迁移到 Meson**：tarball 内只有
`meson.build`/`meson.options`/`meson_options.txt`，无 configure.ac/Makefile.am。
任务卡中"autotools（configure.ac/Makefile.am）"为过期情报，本适配按实际源码
走 `MesonToolchain`（仓内先例：archives/a/aml/1.0.0）。

OHOS 裁剪决策（全部经交叉编译实测验证）：

| 上游面 | OHOS 可得性 | 决策 | 依据 |
|---|---|---|---|
| pcscd daemon | musl 无 `pthread_cancel(3)`（eventhandler.c:196 引用，ld.lld undefined symbol 实测） | `-Dpcscd=false` + 补丁选项化 | 任务预授权"daemon 可裁剪" |
| libudev 热插拔 | OHOS 无 systemd/udev | `-Dlibudev=false` | 平台无组件 |
| libusb 热插拔 | 未启用（上游默认也关） | `-Dlibusb=false` | 保持默认 |
| libsystemd/polkit | OHOS 无 systemd/polkit | `-Dlibsystemd=false -Dpolkit=false` | 平台无组件 |
| usb/serial 读卡器 | 无热插拔框架支撑 | `-Dusb=false -Dserial=false` | 裁剪面收敛 |
| flex（构建期） | /data/service/hnp/bin/flex 2.6.4 | 直接可用（生成 configfile.c/tokenparser.c） | CI PATH 已含 |
| pod2man（构建期） | /data/service/hnp/bin/pod2man | 直接可用（生成 pcsc-spy.1） | CI PATH 已含 |
| secure_getenv | OHOS sysroot 无 | **零补丁**：上游 meson.build `compiler.has_function('secure_getenv')` 失败后走 `issetugid()` fallback，而 OHOS 有 issetugid | sysroot 实测 |

### 交付产物

- `lib/libpcsclite.so.1` + `lib/libpcsclite_real.so.1` + `lib/libpcscspy.so.0`（shared）
  或 `lib/libpcsclite.a`（static，直接含真实客户端实现，无 dlopen facade）
- `include/PCSC/{winscard,pcsclite,ifdhandler,reader,wintypes,debuglog}.h`（7 头文件）
- `lib/pkgconfig/libpcsclite.pc`（pkg_config_name=libpcsclite，includedirs=include/PCSC）

### 库结构说明（消费者视角）

- **shared**：`libpcsclite.so` 为 facade，`SCard*` 经 `dlopen("libpcsclite_real.so.1")`
  委托到 `libpcsclite_real.so`（真实客户端实现，负责与 pcscd 的 unix socket IPC）；
  两库须同装。`libpcscspy.so` 为 API spy 垫片（dlopen PCSCSPY_DELEGATE）。
- **static**：`libpcsclite.a` 直接编入 winscard_clnt.c 真实实现，无 dlopen。

## 4. 无 daemon 环境的 API 契约（本机 OHOS aarch64 直跑实测）

交叉产物在 OHOS PC 本机直跑（LD_LIBRARY_PATH 指向构建目录）：

- `SCardEstablishContext(SCARD_SCOPE_SYSTEM)` → `SCARD_E_NO_SERVICE (0x8010001D)`，ctx 保持 0
- `SCardReleaseContext(bogus)` / `SCardIsValidContext(bogus)` → `SCARD_E_INVALID_HANDLE (0x80100003)`（本地参数校验，不依赖 daemon）
- `pcsc_stringify_error`：SUCCESS→"Command successful."；NO_SERVICE→"Service not available."；INTERNAL_ERROR→"Internal error."（error.c 精确串）
- `SCARD_PCI_T0/T1/RAW` 全局导出正常（g_defines.c），`MAX_ATR_SIZE=33`

以上即 test_package 11 断言的依据：**无读卡器/无 daemon 环境返回错误码也是有效断言
（验证库可链接、可调用、错误路径正确）**。

## 5. 测试策略（上游 N=43，CI 环境不可执行）

上游测试清点（UnitaryTests/，find 实测 48 文件）：
- 6 个 `.c` 单测（SConfigTest、ControlSysEx etc.）+ 40 个 `.py` 集成测试
  （含子目录 SCardGetStatusChange/ 5 个 .py）+ Makefile + 编号目录
- **meson.build 无任何 test() 注册**（meson test --list → "No tests defined"）
- 运行前置：已运行的 pcscd + 实体读卡器（多数 .py 以 `SCardEstablishContext`
  成功 + `SCardConnect` 真实读卡器为先决），CI 无卡环境不可执行

适配后补全消费者测试 `test_package/test.c`：**11 项编号 CHECK**（daemon-less 路径实测全 PASS，见
test_package/MANIFEST.yml），由 `conan create` 在 CI L1 实跑；
其中 bogus-handle/错误字符串/PCI 全局/ABI 常量 8 项为 daemon 无关断言，
Establish/Release 往返按 daemon 有无走双路径精确断言。

## 6. 补丁清单

| 补丁 | 内容 | 类型 |
|---|---|---|
| 0001-meson.options-add-pcscd-option.patch | 新增 meson 选项 `pcscd`（默认 true，上游行为不变） | portability |
| 0002-meson.build-guard-pcscd-targets.patch | pcscd executable 及其 sysconf/systemd 单元/manpage 安装全部用该选项守卫 | portability |

补丁已在干净源码副本上 `patch -p1 --dry-run` + 实际应用 + 全量构建验证
（static/shared 两变体全绿，安装布局仅 3 库+7 头+.pc）。

## 7. 本地预验证记录

- 裸 meson 交叉构建（shared/static）：库目标全绿，pcscd 裁剪前链接失败（pthread_cancel）
  → 裁剪后全绿
- `conan create -pr:h=/storage/Users/currentUser/.conan2/profiles/ohos-aarch64
  --build=missing -c tools.build:jobs=2`：通过（日志见提交记录/回告）
- test_package 12 断言全过（本机 can_run=True，OHOS aarch64 直跑）

## 8. 已知限制（如实申报）

- pcscd 守护进程未交付：OHOS 上运行 SCard 服务需系统级 daemon 移植
  （musl 无 pthread_cancel 需上游改造轮询线程退出机制）+ unix socket
  路径（默认 /run/pcscd/pcscd.comm，OHOS 期望 PCSCLITE_CSOCK_NAME 环境变量重定向）
- 读卡器驱动（ifdhandler 消费者，如 ccid）不在本包范围
- 静态变体无 facade/spy 语义（上游设计如此）
