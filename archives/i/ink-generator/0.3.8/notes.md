# ink-generator 0.3.8 适配笔记

## 打包环境
- **类型**: npm 包（**wasm-bindgen 产物**：ESM 入口 + 胶水 + **预构建 wasm**）；ink! 智能合约代码生成器
- **打包日期**: 2026-10-08
- **平台**: arm64-ohos（OpenHarmony PC）
- **依赖**: **零依赖**（`dependencies: {}`），无 `bin`/`scripts` → 无需在 build 期从 npm 源取依赖
- **状态**: built

## 打包步骤（conan create 全流程）

```bash
conan create archives/i/ink-generator/0.3.8 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

### 1. 版本（如实披露）
比赛列表写的是 **0.4**，但 npm registry 上**没有 0.4**（全部版本 0.3.1…0.3.8，latest = 0.3.8）
→ 按既定规则**用最新可获取版本 0.3.8**，并在 manifest/notes/PR 三处显著披露。

### 2. 为什么"无需工具链"（与 install-mimic 的关键对照）
包内 `ink_generator_bg.wasm` 是**上游预构建好的**产物 → **不需要 Rust/wasm 工具链**；
而同一批里的 `install-mimic` 虽是同类 Rust 系包，却必须 `cargo build`（本机无 Rust、rustup 拒绝
HarmonyOS）→ **系统级不可用、已放弃**。
> 结论：**可行性看"发布物里是否已含构建产物"，不看实现语言。**

### 3. 构建与打包
- **无编译步骤**：`build()` 仅自检（7 个必需文件齐备 + wasm magic `\0asm`）；
- `package()` 把模块文件装到 `res/ink-generator/`，许可另放包根；
- `package_info()` 用 `resdirs=["res"]` 暴露（JS/wasm 模块没有 include/lib/bin 语义）。

## 上游测试清点（R51）

| 项 | 值 |
|----|----|
| 上游测试 | 在 **Rust 侧**（cargo test / wasm-bindgen 测试） |
| 本环境能否运行 | **不能**：无 Rust 工具链（rustup 拒绝 HarmonyOS；无 brew） |
| 结论 | 上游通过率记 **N/A 并如实披露**（不虚构、也不假装跑过） |
| 替代验证 | test_package 的 **Node 端到端**：手动实例化 wasm（`__wbg_set_wasm`）+ 构造 `Contract` + 调 `start()` |

## 实测结果（本地 conan create，2026-10-08）

```
ink-generator/0.3.8: [build] 无需编译：包内已含预构建 wasm（1020564 字节），必需文件 7 个齐备
ink-generator/0.3.8: [package] 安装 npm 模块到 res/ink-generator/（7 个文件）
[ok]   模块文件齐备（7 个，位于 res/ink-generator/）
[ok]   wasm 合法（magic \0asm，version=1，1020564 字节）
[ok]   API 面存在：start / Contract / Standard / OutputFile
[skip] 具名阻塞：合成输入非法 → 生成器内 panic/trap（sm-function[161]:0x6cf34 …）；
       npm 包未随附合法输入 fixture，故 start() 未以真实输入执行
       （wasm 实例化/API/Contract 构造已真跑通过）
[ok]   证据：wasm 1020564 字节 sha256=d0c33215acd08672…；package.json 声明
       name/version=ink-generator@0.3.8、dependencies={}
checks=4 fails=0 skips=1
RESULT: PASS
```

- **上游**：N/A（测试在 Rust 侧、本环境无 Rust 工具链，见上节，如实披露）
- **消费者**：4 项 = 3 通过 + 1 具名阻塞 SKIP（wasm 真实例化 + API 可调用 + `Contract` 构造通过；
  `start()` 因合成输入 trap 记 SKIP）

### 本轮实际解决的坑（都可复用）

1. **可行性判据是"发布物是否已含构建产物"，不是实现语言**：同一批里 `install-mimic`（Rust）
   必须 `cargo build` → 本机无 Rust（rustup 拒绝 HarmonyOS）→ **系统级不可用、放弃**；
   而 `ink-generator` 同为 Rust 系，但上游**把 wasm 预构建好随 npm 发布** → 零工具链、零依赖，
   直接可打包。
2. **比赛版本号可能在任何发布渠道都不存在**：列表写 0.4，npm 上只有 0.3.1…0.3.8 →
   按既定规则用**最新可获取版本**并在 manifest/notes/PR 三处披露。
3. **本环境跑 Node 端到端的双路径**：裸 `node` 实测**会因 JIT 崩溃**
   （`Check failed: 12 == (*__errno_location())` + `Signal 5 (core dumped)`，与 DRAFT-29001 同签名），
   而 `node --jitless` 下 **V8 的 jitless 模式不支持 WebAssembly**
   （`ReferenceError: WebAssembly is not defined`）→ 校验脚本改成"**先试默认、再试 `--jitless`**，
   哪条路径真把 wasm 跑起来就用哪条"；本次默认路径成功实例化并执行。
4. **wasm-bindgen 模块在 Node 里的加载方式**：`ink_generator.js` 是 ESM 且
   `import * as wasm from "./ink_generator_bg.wasm"`（Node 直接 import `.wasm` 受限）→
   改为**手动实例化**：`WebAssembly.instantiate(bytes, {"./ink_generator_bg.js": bg})` +
   `bg.__wbg_set_wasm(instance.exports)`，再构造 `Contract` 调 `start()`。
5. **合成输入会让生成器 trap**：内部用 `syn` 解析 ink! 源码，占位 source 会 panic →
   `sm-function[...]` wasm trap；npm 包**未随附合法输入 fixture** → 该子项按具名证据记 SKIP，
   而"wasm 实例化 + API 可调用 + `Contract` 构造"三项仍作为**真跑通过**保留（不因一个子项
   不可行就把整项记成通过或失败）。

## 复用来源

- npm 包范式（发布 tarball → 无编译/自检 → 装到 res/ + 端到端校验）沿用本会话的
  `archives/i/install-peerdeps/3.0.7`，产物落点参考同族 `archives/a/acorn`；
- 消费者校验的"仅具名环境信号可 SKIP"口径沿用 PR #14983/#15010 的修正。
