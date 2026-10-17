# DRAFT-libfastcommon-1.0.88-makesh-uname-probe-ohos — make.sh 系 uname 平台探测在 HarmonyOS 落空

> **Contributor**: pc2-15 | **Status**: DRAFT | **Updated**: 2026-09-22
> **Severity**: 🟡 medium | **Category**: ohos / make / platform-detection / raw-makefile / portability
> **对应 KV**: DRAFT-libfastcommon-1.0.88-makesh-uname-probe-ohos.kv

## 问题

FastDFS 家族（libfastcommon/libserverframe/fastdfs 等）用 `make.sh` 驱动 raw
Makefile 构建。`make.sh` 内部用 `uname -s` 判断平台并生成 `src/_os_define.h`：

- `uname -s = Linux` → `OS_LINUX` + `IOEVENT_USE_EPOLL`
- 其他平台分支（FreeBSD/Darwin/SunOS/AIX/HP-UX）各对应 kqueue/port 等
- **未匹配任何分支时落入 else** → `OS_NAME=OS_UNKOWN`、`IOEVENT_USE=IOEVENT_USE_NONE`

HarmonyOS PC 的 `uname -s` 返回 `HarmonyOS`（非 `Linux`），因此直接运行
`make.sh` 会静默生成 `OS_UNKOWN + IOEVENT_USE_NONE` 的 `_os_define.h`：
ioevent 网络事件后端退化为 NONE（无 epoll/io_uring/kqueue），功能降级但不报错。

## 根因

上游构建脚本用 `uname -s` 字符串做平台分支判断，只枚举了
Linux/FreeBSD/Darwin/SunOS/AIX/HP-UX；HarmonyOS 不在枚举内，落入 else 的
"未知平台 + 无事件后端" 分支。这是"uname -s = HarmonyOS 不被平台探测识别"族
问题在 raw make.sh 构建系统中的形态（E140/E267 覆盖 CMake 形态、E160 覆盖
config.guess 形态，本条覆盖 make.sh 探测 + _os_define.h 生成形态）。

## 方案（在 Conan 配方内复刻 make.sh 的 Makefile 渲染）

不直接运行 `make.sh`（它还硬编码 `gcc`，而 OHOS PC 工具链只有 clang），而是
在 `conanfile.py build()` 中：

1. **显式生成 `src/_os_define.h`**，按 OHOS 真实内核语义取值：
   `OS_LINUX 1` + `IOEVENT_USE_EPOLL 1`（OHOS 内核基于 Linux，epoll 可用），
   `OS_BITS/OFF_BITS 64`，dirent 字段按 OHOS sysroot 实际存在性
   （`d_type/d_reclen/d_off` 有，`d_namlen` 无）；
2. **复刻 make.sh 的 sed 替换**：读 `src/Makefile.in`，用配方内的
   `tools.build:compiler_executables` 字典中的 C 编译器替换 `$(CC)`，
   `$(CFLAGS)/$(INCS)/$(LIBS)/$(TARGET_PREFIX)/$(LIB_VERSION)` 全部由配方确定；
3. 在 `cwd=<source>/src` 下 `make -j1 all` + `make -j1 install` 到 staging。

## 验证

- `conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=...` → G2 通过；
- `readelf -d libfastcommon.so` 含 SONAME（配方 CFLAGS 追加
  `-Wl,-soname,libfastcommon.so`，满足 OHOS 链接门禁）；
- 上游测试套件 36 个程序全部编译成功并运行（见 test-report.md）。

## 适用边界

- 适用于"make.sh/自研 shell 脚本驱动 raw Makefile + uname 探测生成平台头"
  的 FastDFS 家族及同类项目；
- CMake 平台探测问题用 E140/E267；autotools config.guess 用 E160；
- 若上游 make.sh 有等价可参数化的编译器/平台覆盖开关（如环境变量 CC），
  优先用该开关而非复刻渲染。

## 反例与限制

- 不得把 uname 探测落空当作上游缺陷打补丁硬改 make.sh（保持上游文件零改动，
  改动集中在配方内，符合 R8 平台宏守卫精神）；
- 显式写死 `OS_LINUX + IOEVENT_USE_EPOLL` 的前提是目标确为 Linux 内核的
  OHOS；若未来 OHOS 内核形态变化需重新评估事件后端选择；
- 复刻 Makefile 渲染后，上游新增/调整 Makefile.in 变量时配方需同步，
  存在少量维护漂移风险（用注释标明对应 make.sh 行号缓解）。
