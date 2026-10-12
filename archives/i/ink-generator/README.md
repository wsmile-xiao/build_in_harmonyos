# ink-generator

## 软件描述
`ink-generator` 是 **ink!（Rust 智能合约框架）代码生成器**：输入合约标准（PSP22/PSP34 等）、元数据、源码与许可，输出生成的合约文件（主文件 / 数据 / traits / 错误 / Cargo 配置）。以 **wasm-bindgen npm 模块**形式发布 —— 核心逻辑编译为 wasm，JS 侧提供 `start()` 等 API。Apache-2.0（包内另附 MIT）。

## 功能概述
| API | 作用 |
|---|---|
| `start(input: Contract): Promise<ParserResponse>` | 生成合约代码（异步）；返回生成结果 |
| `class Contract` | 输入载体：`standard`、`metadata`、`extensions`、`source`、`license_name`、`use_external_crate`、`files` |
| `enum Standard` | 合约标准（`PSP22` / `PSP34`） |
| `enum OutputFile` | 输出类别（`Main` / `Data` / `Traits` / `Errors` / `Cargo`） |

## OHOS 适配

### 打包方式
- **npm 发布 tarball**（含**上游预构建的 `ink_generator_bg.wasm`**）：`build()` 无编译步骤，只做自检（必需文件齐备 + wasm magic）
- 模块文件装到 `res/ink-generator/`（`resdirs=["res"]` 暴露），许可另放包根
- **零依赖**：`dependencies` 为空、无 `bin`/`scripts` → 不存在依赖缺口

### 关键攻坚点
1. **版本如实披露**：比赛列表写 0.4，但 npm 上无 0.4（最高 0.3.8）→ 用最新可获取版本并在三处披露
2. **可行性判据**：同为 Rust 系的 `install-mimic` 必须 cargo 编译（本机无 Rust → 放弃），而本包因**发布物已含构建产物**而完全可行 —— 看"发布物是否含构建产物"，不看实现语言
3. **Node 端到端校验**：`ink_generator.js` 是 ESM 且 `import * as wasm from "./ink_generator_bg.wasm"`（Node 直接 import `.wasm` 受限）→ 消费者脚本改为**手动实例化**：`WebAssembly.instantiate(bytes, {"./ink_generator_bg.js": bg})` + `bg.__wbg_set_wasm(instance.exports)`，再构造 `Contract` 调 `start()`
4. **上游测试在 Rust 侧**：本环境无 Rust 工具链 → 上游通过率记 N/A 并披露；验证由消费者侧端到端承担

### 与 Linux 的差异
- wasm 字节码 + JS，跨平台无差异；差异集中在**打包形态**（无编译、装 res/）与**校验方式**（Node 手动实例化 wasm）

## 依赖关系
- **Conan requires**：无
- **npm 运行期依赖**：**无**（`dependencies: {}`）
- **工具链**：打包无需任何工具链；消费者校验需 `node`（本机 v24.13.0）

## 版本记录
| 版本 | 状态 | 打包日期 | 备注 |
|------|------|---------|------|
| 0.3.8 | built | 2026-10-08 | npm 预构建 wasm-bindgen 模块；零依赖、无需工具链；Node 端到端校验（比赛列表的 0.4 在 npm 不存在，已披露） |

## 参考资料
- npm: https://www.npmjs.com/package/ink-generator
- 上游仓库: https://github.com/Smart-Beaver/ink-generator-wasm
