# OHOS 上 node 必须 --jitless，而 --jitless 关闭 WebAssembly 会连带击穿 TS transform 与 undici fetch

- **草稿 ID**: DRAFT-zx-8.8.5-ohos-node-jitless-wasm-chain
- **来源**: zx 8.8.5 HarmonyOS PC 适配（上游 node:test 套件在 OHOS 上实跑，4 个 `.ts` 文件需 tsc 预编译）
- **分类**: runtime / node / testing / ohos
- **状态**: 本地草稿（待随 PR 提交）

## 问题 / 错误签名

- **不带 `--jitless` 直接崩溃**：
  ```
  # Fatal error in , line 0
  # Check failed: 12 == (*__errno_location()).
  ----- Native stack trace -----
  ```
  进程收到 `Signal 5`（core dumped）。node v24.13.0 在 OHOS 上即使用 `node -e "console.log(1)"` 也会触发。
- **`--jitless` 的连带后果**：`node --jitless -e "console.log(typeof WebAssembly)"` → `undefined`
  - `.ts` 文件：`ReferenceError: WebAssembly is not defined`（node 自带 TS transform = amaro = wasm）
  - `fetch()`：`TypeError: fetch failed [cause]: ReferenceError: WebAssembly is not defined`
    （undici 的 llhttp HTTP 解析器也是 wasm 实现）
- **npm wrapper 同样崩溃**：hnp 的 `npm`/`npx` 是真 JS 脚本，直接执行同样 Signal 5。

## 根因

1. **node 在 OHOS 上必须先 `--jitless`**：JIT 路径触发 `errno` 断言失败，这是本机 node 构建/内核配合的缺陷，
   与脚本内容无关；`NODE_OPTIONS=--jitless --no-deprecation`（后者把 `--no-deprecation` 一并固定，
   避免 deprecation 警告污染被断言的 stdout）必须在配方中显式注入（R33：不依赖未定义 shell 变量）。

2. **`--jitless` 关闭 WebAssembly 是有代价的**：node 24 把多个子系统实现为 wasm，最典型的是
   **TypeScript 类型擦除/转换（amaro）** 与 **undici 的 HTTP 解析器（llhttp）**。
   一旦关闭，`--experimental-strip-types` / `--experimental-transform-types` 与 `fetch()` 全部失效。

3. **两个症状必须一次性识别**：`.ts 不能跑` 与 `fetch 失败` 表面无关，实际同一根因。
   若只看到 `fetch failed` 就判断"网络不通"，会漏判；若为修 `.ts` 而尝试去掉 `--jitless`，
   进程直接 core dump，把"跑不了"掩盖成"跳过测试"。

4. **npm 必须绕过 wrapper**：用 `node --jitless <node 前缀>/lib/node_modules/npm/bin/npm-cli.js`
   （`node 前缀` 可由 `realpath(which node)` 的祖父目录推出），同 alexjs / acorn 先例。

## 最小修复方案

以 `archives/z/zx/8.8.5/` 为例：

```python
# conanfile.py build()
env = Environment()
env.define("NODE_OPTIONS", "--jitless --no-deprecation")   # 关键
env.define("TMPDIR", tmpdir)                                # /tmp 只读，必须改指可写目录
with env.vars(self).apply():
    self.run(f'node "{npm_cli}" install --ignore-scripts '
             '--no-audit --no-fund --no-package-lock --no-save '
             'get-port@7.1.0 typescript@5.9.3', cwd=self.source_folder)
```

`.ts` 测试改用包内 tsc 预编译（`tsc` 是 devDependency，用 node 直接执行其 `lib/tsc.js` 以免 shebang 崩溃）：

```sh
node --jitless node_modules/typescript/lib/tsc.js \
    --allowImportingTsExtensions --rewriteRelativeImportExtensions \
    --module nodenext --target es2022 --moduleResolution nodenext \
    --skipLibCheck --outDir <outdir> test/{error,log,md,goods}.test.ts
```

注意两点：
- tsc 会报告项目既有的类型诊断，但仍会输出 JS——判定标准应是"`<outdir>/test/*.js` 与 `<outdir>/src/*.js` 是否生成"，
  而不是 tsc 的退出码。
- 编译后的测试若用 `resolve(__dirname, '..')` 推根目录并读 `package.json`，需把 `package.json` 复制进 `<outdir>`。

依赖 `fetch()` 的断言（本机无出网路由，且 llhttp 是 wasm）按平台豁免**显式登记技术原因**，
不删改上游断言；清单之外的失败让构建失败。

## 实测效果（zx 8.8.5 + node v24.13.0）

- 4 个 `.ts` 文件经 tsc 预编译后实跑：error 10/10、log 11/11、md 1/1、goods 28/29 通过（共 51 例）
- 完整套件 12 文件 259 用例：235 pass / 23 平台豁免 / 1 skip，`unexpected=0`

## 关联经验

- 同族平台陷阱（`/tmp` 只读 erofs、OHOS toybox `ps -lx` 无列边界导致 `@webpod/ps` 解析失败、
  `whoami` 对本应用 uid 报 `bad uid`）见 zx 8.8.5 `notes.md` 与 `manifest.yaml` 的 `knowledge_gained`。
