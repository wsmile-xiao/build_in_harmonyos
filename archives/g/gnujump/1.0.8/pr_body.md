- **三方库名称**：gnujump
- **上游版本**：1.0.8
- **上游仓库地址**：https://www.gnu.org/software/gnujump/ （官方 tarball https://ftp.gnu.org/gnu/gnujump/gnujump-1.0.8.tar.gz）
- **适配路径**：路径 B（贡献创新）——新增"无头 CI 运行 GL 链接程序：gl4es libGL 构造期 fb0 EACCES 段错误的对照程序归因 + 按崩溃层次定档断言集 + R34 留证跳过"三步法
- **使用知识库**：方案级复用 lgeneral/1.4.4 同构先例（sdl-config 包装、--disable-nls、umask、-j1）；知识图谱参考 E011（umask）、E386（CONFIG_SHELL/SHELL 路由）、E007（config.guess/sub 构建期替换）；新增 DRAFT-gnujump-1.0.8-gl4es-libgl-fb0-constructor-segfault-headless（同 stem .kv/.md 成对）
- **知识库扩展**：DRAFT-gnujump-1.0.8-gl4es-libgl-fb0-constructor-segfault-headless——无头 CI 上 gl4es libGL 构造期 open('/dev/graphics/fb0') EACCES 即段错误，任何链接 libGL 的进程未进 main 即 Signal 11；消费者测试三步处置：最小对照程序归因 → 按崩溃层次定档断言集（构造期即崩 ⇒ 启动期断言不可得，只能留 ELF/链接层断言）→ 未执行档 R34 逐字留证跳过并计入未执行分类
- **关联 Issue**：#3250（https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/3250）

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 0 | 来源：grep TESTS / check_PROGRAMS 于全部 Makefile.am（src/ skins/ sound/ doc/ po/）无命中 |
| 集成测试 | 0 | automake 生成空 check 目标，无可执行注册 |
| 其他测试 | 0 | 无 |
| **合计** | **0** | |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 消费者测试（test_package） | 1 | 新增 | test_gnujump.py：3 组断言，**本设备真实执行 2 组**——①ELF 结构（ELF64 AArch64 PIE、musl 解释器，已执行）②DT_NEEDED 白名单（SDL 兼容链/GL 转译层/图像编解码/musl libc，拒绝 libX11/libasound 桌面栈污染，已执行）③SDL dummy 驱动启动/运行断言（timeout 20 收口）——**未执行，R34 留证跳过**：gl4es libGL 构造函数在进程进 main 之前即 SIGSEGV，SDL 初始化/视频后端选择/主循环这些 main 之后的行为观察不到，dummy 驱动救不回来。N_consumer=1 |
| **合计** | **1** | **+1** | 上游 N_static=0，消费者测试补位（R51 口径） |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **是**，上游无测试用例，适配后补全了测试（请在下方说明）
- [ ] **否**，上游已有测试用例覆盖

> - **补全的测试范围**：新增 1 个消费者测试程序（3 组断言，本设备真实执行 2 组，第 3 组按 R34 逐字留证跳过并计入未执行分类）
> - **补全原因**：上游为纯游戏程序，无任何注册自动化测试（N_static=0），按 R51 以被测二进制真实运行断言补位
> - **新增测试文件清单**：
>   1. `test_package/test_gnujump.py` — ELF 结构 + DT_NEEDED 白名单（真实执行）+ SDL dummy 启动/运行断言（命中构造期崩溃三签 ⇒ R34 留证跳过）
>   2. `test_package/MANIFEST.yml` — 上游测试口径如实申报（N_static=0）

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：无上游测试（0/0，见统计表口径）
- 新增测试用例通过率：1/1 测试程序 PASS（其中 2/3 断言组真实执行，第 3 组 R34 留证跳过）
- 干净重建读数（2026-09-23 02:08–02:11，HEAD f8ecd53871，配方 cf8922a757）：G2 `conan create` 与 W3 `build_and_test.sh` 各**真实编译一次**（两份日志 `grep -c "Calling build"` 均 =1、`"Building from source"` 均 =1，包 ID `efcb9cd97e8fbece15be046d639a00edcbbb83df`，`.ci-result.json` exit_code=0 / log_sha256 `efbd7495224f7b21689cb7ed20d001866ebc4c6d41a5b799d761ddcf94f0c969`），memcap 峰值 196 MB / 预算 6000 MB / 用时 127.9 s，状态 built（未 upload）

## 补充说明

- **gl4es 运行时边界（R34 documented-skip）**：`gl4es libGL constructor segfaults without /dev/graphics permission (fb0 not accessible ([Errno 13] Permission denied: '/dev/graphics/fb0'))`——经最小对照程序（2026-09-23 本轮亲测：`clang --target=aarch64-linux-ohos control.c -lGL` 得 NEEDED=[libGL.so.1, libc.so]，运行读数 `LIBGL: Initialising gl4es` + `Signal 11`，rc=139，从未返回 42）归因为平台边界。**启动期行为证据在本包不可得**（同一 dummy 环境下 `usr/bin/gnujump` 无参数与 `--help` 均 rc=139、stdout 止于 `LIBGL: Initialising gl4es` ⇒ 未进 main），故消费者测试实际交付的是 ELF 结构 + DT_NEEDED 白名单两档断言，其余逐字留证跳过；全文读数见 `reports/control-program-attribution.log` 与 `notes.md`「消费者测试」。详见 #3250 与随 PR 草稿。
- **依赖链**：sdl12-compat/1.2.68（SDL1.2 API 兼容，run=True）+ sdl-image/1.2.12 + sdl-mixer/1.2.12 + gl4es/1.1.6（GL→GLES 转译）；GLU 上游全源码零调用，configure 检测失败置空即可。
- **已知限制**：NLS 以 --disable-nls 关闭（OHOS sysroot libintl.h 空壳，lgeneral 0003 同源根因）；-j1（HMDFS jobserver FIFO 先例）。
