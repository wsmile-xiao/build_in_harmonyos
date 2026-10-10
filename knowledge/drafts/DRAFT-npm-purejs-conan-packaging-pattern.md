# DRAFT：npm 纯 JS 项目 Conan 适配通用模式（W0–W4 决策树）

> 覆盖「无 native addon 的 npm 包」在 OHOS PC 的完整适配路径。
> 姊妹条目（细节不在此重复）：
> `DRAFT-npm-ohos-nodejs-toolchain`（hnp npm 崩溃 / prune 误删传递依赖 / DEP 警告 / L1e bin 探测）
> `DRAFT-ts-10.9.2-npm-peer-deps-pruned`（peer 依赖被 prune + no-save 装回 devDeps 陷阱）
> `DRAFT-conan-recipe-shell-text-python-format-conflict`（wrapper 生成禁用 format()）

## 使用说明

**何时用**：接到一个 npm/Node.js 生态的三方库适配任务（任务大厅大量此类任务以
`lang=cpp` 登记，实际检测为 nodejs），按本决策树从 W0 走到 W4，可直接套用命令骨架与
文件布局，避免每个库重新踩坑。

**流程总览**：

```
W0 判定「纯 JS」→ W1 选源码归档 → W2 配方骨架（本条 §示例B）→ W3 test_package
→ W4 本机 Windows 等价验证（本条 §示例D）→ 真机 shadow CI（走通用模板）
```

**W0 纯 JS 判定**（满足全部才是本模式，否则走 native/混合路径）：

| 检查 | 命令/位置 | 判定 |
|---|---|---|
| 无 native addon | `grep -r 'node-gyp\|binding.gyp' package.json src/` | 无命中 |
| 依赖全纯 JS | `package.json` 的 `dependencies` 逐个查（无 `@swc/core`、`esbuild`、`bun`、`dprint` 等 native） | 是 |
| 有 node 即可跑 | `bin` 字段指向 `.js` 入口 | 是 |

native devDep（lint/打包工具）**不算阻塞**——`--ignore-scripts` 跳过其 postinstall。

## 适用范围

- ✅ 纯 JavaScript/TypeScript npm 包（CLI 工具或库），运行时只需系统 node
- ✅ 构建 = `npm ci` + `tsc`（TypeScript 项目）或无构建步骤
- ✅ 交叉编译无所谓：`settings = "os", "arch"`，无编译器
- ❌ 含 native addon（node-gyp/napi-rs）→ 需 ELF 签名与平台二进制检查，另立草稿
- ❌ 构建/运行强依赖 esbuild/bun 等「无 OHOS 二进制且无法源码编」的工具（tailwindcss v4 教训：只能部分编译或 npx wrapper）

## 输入输出定义

- **输入**：
  - `name`（任务库名，Conan 包名与目录/分支名）、`version`
  - 上游归档 URL + SHA256（优先 GitHub tag 归档——**含完整 tests/**；npm tgz 含 dist/ 但无 tests/，仅当无需跑上游测试时用）
  - `package.json`（依赖清单、bin 入口、files 字段）
- **输出**（`archives/<首字母>/<库>/<版本>/`）：
  - `conanfile.py`（build: npm ci → 构建 → prune；package: share 布局 + bin wrapper）
  - `conandata.yml`（URL/SHA256/patches）、`manifest.yaml`、`notes.md`
  - `commands.json`（**含 bin/ 的工具包必填**，软件级目录）
  - `test_package/`（conanfile.py + test_<库>.sh + MANIFEST.yml）
  - 包产物布局：`share/<库>/{dist,node_modules,package.json,...}` + `bin/<入口们>`（sh wrapper）

## 示例

### A. build() 命令骨架（ts/10.9.2 实证）

```python
def build(self):
    apply_conandata_patches(self)                     # G1 门禁要求调用（patches 可为空）
    self.run("npm ci --ignore-scripts --legacy-peer-deps", cwd=self.source_folder)
    self.run("npm run build-tsc", cwd=self.source_folder)       # 纯 JS 包可无此步
    # peer 依赖分组移动（typescript/@types/node 等 devDep+peer 双声明包）：
    #   devDependencies -> dependencies（json 读写，构建期-only）
    self.run("npm prune --omit=dev --legacy-peer-deps", cwd=self.source_folder)
```

- `--ignore-scripts`：跳过 dprint/husky/esbuild 等 native postinstall（无 OHOS 二进制）
- `--legacy-peer-deps`：绕过 devDep peer 声明冲突（如 typedoc 要 typescript<=4.5）
- **真机注意**：若 prune 后报缺**传递依赖**（ERR_MODULE_NOT_FOUND），是 OHOS npm 的
  prune bug——回退 alexjs 方案：完整安装不 prune，整树打包（见姊妹条目）

### B. package()/wrapper 骨架

```python
share = os.path.join(self.package_folder, "share", self.name)
for path in ("dist", "node_modules", ...):           # 对照 package.json "files"
    copy(self, "*", src=os.path.join(src, path), dst=os.path.join(share, path))
wrapper = "#!/bin/sh\n" \
    'X_HOME="${X_HOME:-$(dirname "$(dirname "$0")")/share/<库>}"\n' \
    'exec node "$X_HOME/dist/bin.js" "$@"\n'          # 字符串拼接，禁用 format()
```

### C. test_package 三断言模式（sh，真机执行）

```sh
"$TS_NODE_BIN" --version | grep -q "<版本>"                    # 1 版本
"$TS_NODE_BIN" smoke.ts          # 2 真实功能（含类型/核心 API 断言）
"$TS_NODE_BIN" bad.ts && FAIL    # 3 错误路径必须被拒绝（防 transpile-only 假通过）
```

### D. W4 本机 Windows 等价验证（无真机时的最大验证面）

```powershell
# ① 源码树走通 build 步骤（npm ci/tsc/prune + 移动 peer 分组）
# ② conan create --skip-test 或 -tm（build+package 全验；test 因 sh 不可执行预期失败）
# ③ Git Bash 等价验证 wrapper + L1e 破坏性自测：
& 'C:\Program Files\Git\usr\bin\sh.exe' '/c/.../run-wrapper-test.sh' '<pkg POSIX路径>' '<smoke.ts>'
#   round1 完整包全过；round2 mv dist dist.bak 后必须 FAIL → 真测试确认
```

### E. 门禁适配清单（nodejs 任务特有）

- `commands.json`：含 bin/ 必填（L0 `commands_json_r`）
- `conanfile.py`：`export_sources()` + build 内补丁调用（G1 硬性）
- `lang-preflight` 会报 `task=cpp, detected=nodejs` → **平台侧数据问题**，提前在
  PR/任务侧确认迁移，勿硬凑 cpp
- manifest `build.dependencies` 写 `node/<版本>`（记录性质，conanfile 无 requires）

### E. 上游测试在真机的执行要点（nodejs 库通用）

1. **typescript@latest（5.9+）包结构变化**：npm 包默认**不含 lib/typescript.js**
   （仅 getExePath.js/tsc.js/version.cjs，需 postinstall 补全）——全链
   `--ignore-scripts` 时 require('typescript') 得到 2-key 残缺对象
   （`ts.sys undefined` → `Cannot read properties of undefined (reading 'fileExists')`）。
   解法：pin 与上游 devDep 一致的完整分发版本（如 typescript@4.7.4）。
2. **--jitless 双刃**：OHOS node 重负载必须 jitless（否则 V8 Signal 5），但
   jitless 同时禁用 **WebAssembly** —— node 24 内置 amaro（strip-types loader，
   lib/wasm.js）报 `ReferenceError: WebAssembly is not defined`，凡依赖 node
   内置 TS 剥离的测试路径必挂。二选一平台硬限制，如实归因。
3. harness 调 `node_modules/.bin/<tool>` 直调（HMDFS noexec）→ 改
   `node <package>/dist/bin.js`；harness 内 `npm install`/`npm pack` →
   `node <npm-cli.js>` 直调 + `--no-bin-links`。

## 验证证据

ts/10.9.2（上游 ts-node）：本机 Windows 端到端 conan create（默认与
ohos-aarch64 profile）build+package 全过；Git Bash wrapper 三断言 + L1e 自测通过；
G0e/JC/KC/L0 清零；G1 修复后 PASS。codecov-cli 0.8.0、alexjs 11.0.1 为同模式先例。

**真机 shadow CI 终态（2026-10-03，r1-r10 迭代后）**：
G0/KC/JC/L0/L1/L4/L5 全 pass、exit 0、Pass rate 100%；L1e 破坏性验证确认。
真机必踩坑（按命中顺序）：settings 四项门禁（L0p）→ hnp npm wrapper Signal 5
（直调 npm-cli.js + --jitless）→ HMDFS 禁 symlink（--no-bin-links + 直调 tsc 入口）
→ node 重负载同样 Signal 5（全链 jitless）→ HMDFS 脚本无执行位（sh 显式执行
wrapper）→ conanrun PATH 缺 hnp bin（wrapper 内补 PATH）→ CI L2 误探
node_modules 嵌套 bin（package() 清理）。上游 ava 全量矩阵与 jitless 强制构成
平台二选一（无 jitless 即 Signal 5；jitless 下上游 ESM test-loader 链异常），
按「具体报错定位 + 排除缺依赖」口径申报。
