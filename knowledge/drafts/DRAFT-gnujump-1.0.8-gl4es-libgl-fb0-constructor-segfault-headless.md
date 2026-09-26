# DRAFT-gnujump-1.0.8-gl4es-libgl-fb0-constructor-segfault-headless — 无头环境 GL 链接程序加载即段错误：对照程序归因 + 按崩溃层次定档断言集 + R34 留证跳过

> **对应结构化数据**：`knowledge/drafts/DRAFT-gnujump-1.0.8-gl4es-libgl-fb0-constructor-segfault-headless.kv`
> **验证实例**：gnujump 1.0.8（OHOS PC aarch64，gl4es 桌面 GL 转译层，SDL12-compat）
> **关联 Issue**：#3250（https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/3250）
> **Status**: DRAFT ｜ **Severity**: 🔴 high ｜ **Updated**: 2026-09-23

## 1. 一句话

OHOS 无头 CI 上，链接了 gl4es `libGL.so` 的程序在**库加载（构造）阶段**就段错误——
gl4es 探测 framebuffer 时 `open('/dev/graphics/fb0')` 拿到 `EACCES`。这与被测程序自身
逻辑无关，而且**进程从未进入 `main`**；消费者测试必须用**最小对照程序**归因，然后
“降级断言、不降透明度”：先按退出码判崩在哪一层，再决定能留哪一档断言——构造期即崩
（rc=139、stdout 只有 `LIBGL: Initialising gl4es`）时，`SDL_VIDEODRIVER=dummy` 这类
运行期开关一个都救不回来，只能退到 ELF/链接层断言 + 逐字留证跳过。

## 2. 症状（逐字，gnujump test_package 读数）

```
[run] SKIP runtime assertions: gl4es libGL constructor segfaults without
/dev/graphics permission (fb0 not accessible ([Errno 13] Permission denied:
'/dev/graphics/fb0')); verified against minimal `int main(){return 42;}` GL-linked
control program (platform boundary, R34 documented-skip).
ELF/NEEDED assertions fully executed.
```

表象是“被测程序崩了”，实际进程**尚未进入 main**——崩在 libGL 的库构造阶段。

## 3. 根因

- OHOS 无头 CI 无 framebuffer 访问授权（`/dev/graphics/fb0` 权限拒绝；
  设备能力矩阵亦确认 `/dev/fb0`、`/dev/dri/card0` 缺失）。
- gl4es 的 libGL 构造/初始化路径探测 framebuffer，`EACCES` 后未降级 → 段错误。
- 因此**任何**链接 libGL 的进程（哪怕 `int main(){return 42;}`）都在加载阶段死亡。

## 4. 归因与处置（本条核心增量）

**归因**——最小对照程序实验：

```c
int main(){return 42;}   /* 链与被测程序相同的 libGL/GL 链路 */
```

对照程序同崩 ⇒ 崩因是平台边界而非上游代码（若不崩，则是上游真 bug，**不得**套用本条的
skip 处置，必须继续修）。

**处置**——先判层次、再按能拿到的档位取断言集（档位由高到低，命中哪档写哪档，不许越档上报）：

1. **ELF/链接层断言**（总能拿到）：PIE AArch64、musl 解释器、`DT_NEEDED` 白名单
   （SDL 兼容链/GL 转译层/图像编解码/musl libc，拒绝 libX11/libasound 等桌面栈污染）；
2. **启动期运行断言**（**仅当进程能进 `main`** 才可主张）：`SDL_VIDEODRIVER=dummy
   SDL_AUDIODRIVER=dummy` 真实启动被测程序（timeout 收口），rc=124/正常退出且日志推进到
   视频后端选择之后，才谈得上“DSO 全链加载 + SDL 初始化 + 到达视频初始化/主循环”。
   ⚠ 构造期即崩（rc=139，stdout 止于 `LIBGL: Initialising gl4es`）时**本档不可得**——
   dummy 驱动改的是 `main` 里的后端选择，改不动加载期构造函数，硬写“已取得启动期断言”
   就是虚报；
3. **运行时 GL 断言**（无头拿不到）：R34 逐字留证跳过（errno + 对照程序读数），
   计入未执行分类，不伪装成通过。

gnujump 1.0.8 实测命中第 2 档的**反例**，因此本包实际交付的是 1+3 两档（见 §7）。

## 5. 适用范围 / 反例 / 解除条件

- **适用**：消费者测试/smoke 要真实**运行** GL 链接程序的包——游戏、可视化工具、
  模拟器、任何 gl4es shim 链路的 test_package。
- **反例**：只做编译/链接断言的包；运行路径不加载 libGL 的包；对照程序不崩的场景
  （那是上游问题，继续修，不 skip）。
- **解除条件**：CI worker 授权 fb0/DRY 设备节点，或 gl4es 修复无 fb0 退化路径后，
  运行时断言应恢复真实执行。

## 6. 查重与新增价值

- `DRAFT-ohos-syscall-capability-matrix-fork-probe`：把 `/dev/fb0`、`/dev/dri/card0`
  列入缺失设备矩阵——**同一底层事实，但那条是能力矩阵探测**，不含 GL 库构造期段错误的
  归因方法与测试处置。
- `DRAFT-logstalgia-desktop-gl-shim-gl4es`：覆盖**构建期**引入 gl4es shim
  （GL 头/lib/pc 探测命中），不覆盖**运行期**行为。
- `DRAFT-ohos-gl-symbols-are-dispatcher-stubs`：GL 符号是调度空桩（静默错误、全黑画面），
  与本条“加载即崩”症状不同。
- 新增价值：把“GL 消费者测试在无头 CI 上怎么归因、怎么留证地降级”固化为可复用三步法。
  判 create。

## 7. 触发实例与证据（2026-09-23 02:09 干净重建，HEAD f8ecd53871 / 配方 cf8922a757）

- **对照程序归因**（本轮亲测，非转述）：`int main(){return 42;}` 用
  `clang --target=aarch64-linux-ohos` 链 gl4es 的 `libGL.so.1`（`readelf -d` 确认
  `NEEDED=[libGL.so.1, libc.so]`），运行读数 `LIBGL: Initialising gl4es` +
  `Signal 11 (core dumped)`，**退出码 139**，从未返回 42；同机
  `/dev/graphics/fb0` → `Permission denied`（`[Errno 13]`）。
- **被测程序同档读数**：打包后的 `usr/bin/gnujump` 在
  `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy` 下，无参数与 `--help` 两次启动均
  **rc=139**、stdout 只有 `LIBGL: Initialising gl4es` ⇒ 未进 `main` ⇒
  **第 2 档（启动期断言）在本包不可得**。
- **test_package 逐字读数**（`reports/conan-create.log` 2124–2126 行，同一次运行）：
  `[elf] gnujump: PIE AArch64 OK, NEEDED=[...]` →
  `[run] SKIP runtime assertions: gl4es libGL constructor segfaults without
  /dev/graphics permission (fb0 not accessible ([Errno 13] Permission denied:
  '/dev/graphics/fb0')); verified against minimal `int main(){return 42;}` GL-linked
  control program (platform boundary, R34 documented-skip). ELF/NEEDED assertions
  fully executed.` → `test_package: PASS`。
- ⇒ 本包走的是 §4 的 1+3 两档，第 2 档如实标“不可得”。全文读数见
  `archives/g/gnujump/1.0.8/reports/control-program-attribution.log` 与
  `notes.md`「验证记录」。
- 实现位置：`test_package/test_gnujump.py` 内置的是“崩溃三签 + fb0 可访问性探针”分支
  （不是对照程序本体）；最小对照程序是构建会话内的一次性手工实验，读数已按上面记档。
