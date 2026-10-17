# DRAFT-roblox-ts-3.0.0-npm-prebuilt-runtime-closure

> Contributor: OpenDesk Agent | Status: Draft | Updated: 2026-09-29
> Source: roblox-ts 3.0.0 HarmonyOS PC 适配（npm / Node.js CLI）
> 领域：npm 打包范式 / conan recipe 结构

## 问题

roblox-ts 3.0.0 的 npm 官方发布包已含预编译 `out/**/*.js`（206 个 .js + 206 个 .d.ts）
与 `include/*.lua`，按 `archives/a/aicommits`「预编译资产包」范式直接打包后，
`bin/rbxtsc --version` 立即失败：

```text
Error: Cannot find module '...'
  code: 'MODULE_NOT_FOUND',
  requireStack: [
    '.../libexec/roblox-ts/out/Shared/classes/LogService.js',
    '.../out/Shared/errors/LoggableError.js',
    ...
  ]
```

## 根因

npm 发布包只包含 `package.json` 的 **`files` 字段**所列路径。roblox-ts 3.0.0 的
`files` = `["out", "include", "CHANGELOG.md", "!**/*.js.map", "!**/*.tsbuildinfo"]`
—— **不含 node_modules**。

其 9 个运行时依赖（`typescript@5.5.3`、`kleur`、`yargs`、`chokidar`、`fs-extra`、
`resolve`、`@roblox-ts/{luau-ast,path-translator,rojo-resolver}`）及 42 个传递依赖
（共 51 个包）必须在构建期安装，否则运行期 `require()` 失败。

对照：`archives/a/aicommits` 的 `dist/cli.mjs` 是**已 bundle 的零依赖**产物，所以
直接打包可行；`archives/a/actions-up` 有依赖，其 `build()` 就做了
`npm install --omit=dev` 并把 node_modules 一起打包 —— 两类必须区分。

## 解决方案

按 `archives/a/actions-up` 范式（配合 `--jitless`/`--no-bin-links`，见
`DRAFT-roblox-ts-3.0.0-ohos-node-jitless-npm-cli`）：

```python
# build()
self.run(<node> --jitless <npm-cli.js> install --omit=dev --ignore-scripts \
         --no-bin-links --no-audit --no-fund --no-save --no-package-lock, env=None)
# package()
copy(self, "out/*", src=self.source_folder, dst=libexec)          # 206 .js + 206 .d.ts
copy(self, "include/*", src=self.source_folder, dst=libexec)      # Promise.lua / RuntimeLib.lua
shutil.copytree(source_folder/"node_modules", libexec/"node_modules", symlinks=True)
# bin/rbxtsc 启动器：解析可用 node（RBXTSC_NODE > PATH > OHOS hnp node）后
#   exec "$node_bin" --jitless "$script_dir/../libexec/roblox-ts/out/CLI/cli.js" "$@"
```

打包结果（conan create 实测）：206 .js + 206 .ts(.d.ts) + 2 .lua + package.json +
LICENSE + node_modules（51 包，另含各包自带 json/md/js 等）。

## 验证

- `bin/rbxtsc --version` → `3.0.0`；`bin/rbxtsc --help` → 完整 yargs 选项表；
- `conan create ... --build=missing` → exit 0，test_package 断言
  「runtime dep packaged: <9 个运行时依赖>」全 ok，且
  `out/CLI/cli.js` / `out/CLI/index.js` / `include/RuntimeLib.lua` 的 sha256 与
  npm dist 逐字节一致；
- 另有从源码真实构建证据：`npm ci && npm run build`（tspc -b）exit 0，产出 206 个 .js。

## 适用边界

- 适用：npm 发布包为 source、且有运行时依赖的命令行/资产包。
- 反例：零依赖或已 bundle 的 npm CLI（aicommits 型）——无需安装依赖，直接打包更简洁。
- 注意：`--no-bin-links` 会使包内无 `node_modules/.bin`；若上游 CLI 运行期通过
  `npx`/`.bin` 调用自身或其他工具，需另作处理。

## 查重差异

- `exact_duplicate`：false（drafts/index.tsv 无 npm 运行时闭包条目）。
- `causal_duplicate`：false（与 E400 系知识触发点不同：本条是 source 选择与打包完整性）。
- `trigger_overlap`：partial（同为 npm CLI 适配，但本条触发于「启动即 MODULE_NOT_FOUND」）。
- `solution_overlap`：partial（复用 actions-up 的 --omit=dev 范式，并补充判据与打包细节）。
- `combination_novelty`：true。
