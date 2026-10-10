# DRAFT: npm 纯 JS 包打包时 peer 依赖被 prune 删除（ts-node 10.9.2 实证）

## 现象

对 ts-node（Conan 包名 ts）这类「peer 依赖同时出现在 devDependencies」的纯 JS npm 项目，
`npm prune --omit=dev` 之后包无法运行：

1. `Cannot find module 'typescript'`（TS2304/模块解析失败）
2. 补装后又出现 `TS2591: Cannot find name 'process'`（@types/node 也被删）

而“prune 后再 `npm install typescript@x.y.z --no-save`”的直觉修法在干净环境会触发更严重的
问题：npm 重新评估整棵依赖树，把**全部 devDependencies 装回来**并运行其 native postinstall
（dprint 下载平台二进制失败 → 构建失败，OpenHarmony 上必现）。

## 根因

- npm 把根项目里仅声明为 `devDependencies` + `peerDependencies` 的包视为 dev 依赖，
  `prune --omit=dev` 会将其移除；ts-node 运行时必须能 resolve 到 typescript 编译器。
- `@types/node` 是 peer（`"*"`），TypeScript 默认从 `node_modules/@types` 自动加载环境类型，
  删除后所有使用 `process`/`Buffer` 等全局的消费者代码报 TS2591。
- `npm install <pkg> --no-save` 在 node_modules 不完整时会按 package.json 重建整棵树
  （含 devDeps），并非“只装这一个包”。

## 解法（实测通过，ts/10.9.2）

构建目录内**动态修改 package.json**：把 `typescript` 与 `@types/node` 从 `devDependencies`
移动到 `dependencies`，再执行 `npm prune --omit=dev --legacy-peer-deps`：

```python
import json
pkg = json.load(open("package.json", encoding="utf-8"))
for peer in ("typescript", "@types/node"):
    pkg.setdefault("dependencies", {})[peer] = pkg["devDependencies"].pop(peer)
json.dump(pkg, open("package.json", "w", encoding="utf-8"), indent=2)
```

prune 只删不装、不跑 postinstall，node_modules 收敛为纯运行时集合（实测 25 个纯 JS 包），
无需二次安装。该修改只发生在构建目录，不作为源码补丁提交。

## 关联坑（同一次适配实证）

- npm>=7 安装 ts-node devDeps 时 ERESOLVE：devDep typedoc@0.22.10 声明 peer
  typescript<=4.5 与项目固定的 4.7.4 冲突 → `--legacy-peer-deps`。
- 生成 shell wrapper 禁用 Python `str.format()`：shell 的 `${TS_HOME:-...}` 会被当作
  format 占位符抛 KeyError（bin 目录静默为空）→ 用字符串拼接。

## 适用范围

所有“npm 纯 JS 项目 + peer 依赖在根项目仅声明为 devDep”的打包场景（ts-node、
codecov-cli 等同模式）。

## 真机回退路径（交叉引用）

若真机上 prune 后出现**传递依赖缺失**（`ERR_MODULE_NOT_FOUND`，如 supports-color 类），
则是 OHOS npm 的 prune 误删 bug（见 `DRAFT-npm-ohos-nodejs-toolchain`，alexjs 11.0.1
实证）——此时放弃 prune 方案，回退为完整安装整树打包（不 `--omit=dev`），并清理
node_modules 内嵌套 `bin`/`.bin` 目录规避 L1e 探测误判。
