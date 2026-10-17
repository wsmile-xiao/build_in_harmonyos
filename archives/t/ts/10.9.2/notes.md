# ts 10.9.2 适配笔记

> 上游项目：**ts-node**（任务名 `ts`，Debian 源码包 ts-node 10.9.2）
> https://github.com/TypeStrong/ts-node ｜ tag `v10.9.2`

## W0 依赖检查结论

- 依赖数量：运行时 npm 依赖 12 个，peer 依赖 1 个必需（typescript >=2.7）+ 2 个可选（@swc/core、@swc/wasm）
- 已满足依赖：
  - node（系统 /data/service/hnp/bin/node，v24.13.0，参考 codecov-cli/tailwindcss 记录）
  - 运行时依赖全部为**纯 JS 包**：@cspotcode/source-map-support、@tsconfig/node10/12/14/16、acorn、acorn-walk、arg、create-require、diff、make-error、v8-compile-cache-lib、yn —— 无 native addon，npm install 无平台二进制下载
  - typescript（peer）：npm >=7 会自动装入 node_modules，随包一起分发
- 缺失依赖：无阻塞项。注意（非阻塞）：
  - `@swc/core`（可选 peer）为 native 二进制，无 OpenHarmony 版本 → 不安装，ts-node 主体不依赖它（仅 transpiler 可选路径）
  - `dprint`（devDep，lint 用）为 native 二进制，无 OpenHarmony 版本 → 上游 `npm test` 中的 lint 步骤跳过
- 是否需要拆分依赖适配：否（无 C/C++/native 依赖，typescript 随包分发）
- 阻塞点：无
- 下一步：真机 shadow CI 执行 conan create + test_package + ava 子集

## W1 源码与构建系统分析

- 纯 TypeScript/JavaScript 项目，无 C/C++ 代码、无 native addon
- 构建系统：npm + tsc
  - `npm run build-tsc`：`tsc -b ./tsconfig.build-dist.json` 产出 `dist/`
  - `npm run build-configSchema`：typescript-json-schema 生成 `tsconfig.schema.json`（纯 JS，需 dist 先就绪）
  - `npm run build-pack`：仅用于上游自测打包 `tests/ts-node-packed.tgz`，本配方不需要
- 测试：ava（`npm run test-spec`）；完整 `npm test` = build + dprint lint + nyc ava
  - 上游 tests/ 目录包含大量 spec（执行真实 TypeScript 编译、子进程、symlink 等）
  - 降级说明：dprint（native）无法在 OpenHarmony 运行 → lint 步骤跳过；ava 套件在真机执行
- 源码归档选择：GitHub tag v10.9.2 tar.gz（**含完整 tests/**）；npm tgz 含 dist/ 但无 tests/，故选 tag 归档
  - SHA256: `bc43e9d99293e81845c7362bfc6275bf0c486387bb01edb4bda7b95a713171d5`（849647 字节）
  - 注意：归档内 `tests/main-realpath/symlink/symlink.tsx` 与 `website/static/img/logo-icon.svg` 为符号链接（Windows 本机解压会失败，Linux/真机正常）
- 上游 bin：ts-node、ts-node-cwd、ts-node-esm、ts-node-script、ts-node-transpile-only（+ 已弃用 ts-script，未打包）

## 编译步骤（配方 build()）

```bash
npm ci --ignore-scripts --legacy-peer-deps   # 按 lock 安装；跳过 dprint/husky 等 native postinstall
npm run build-tsc                            # tsc 编译 dist/
npx typescript-json-schema ...               # 本地生成 tsconfig.schema.json（跳过外网 merge 步骤）
# 构建目录内动态调整 package.json：把 typescript 与 @types/node 从 devDependencies 移到 dependencies
npm prune --omit=dev --legacy-peer-deps      # 剔除 devDependencies（保留上述两个 peer 包）
```

## 打包（package()）

- `share/ts/`：dist/、dist-raw/、register/、esm/、node10..16/、transpilers/、esm.mjs、child-loader.mjs、package.json、tsconfig.schema*.json、LICENSE、node_modules/（运行时）
- `bin/`：5 个 shell wrapper（exec 系统 node 加载对应 dist 入口）

## 验证结果（本机 Windows 前置验证）

- 上游源码树（Windows node v24.9.0 / npm 11.17.0）完整走通配方 build 步骤：
  - `npm ci --ignore-scripts --legacy-peer-deps`：579 包安装成功
  - `npm run build-tsc`：dist/ 生成成功
  - `npx typescript-json-schema ...`：tsconfig.schema.json 生成成功
  - package.json 调整 + `npm prune --omit=dev`：node_modules 收敛至 25 个纯 JS 包（含 typescript 4.7.4、@types/node 13.13.5）
  - `node dist/bin.js --version` → `v10.9.2`
  - `node dist/bin.js smoke.ts`（含类型标注与模板字符串）→ 输出 `ts-node-ok:42:hello ohos`
  - `node dist/bin.js bad.ts`（类型错误）→ 正确报 TSError 并 exit 1
- **端到端 `conan create`（本机 Windows profile）成功**：build() + package() 全部通过，包入本地缓存（package id 522dcea5982a3f8a5b624c16477e47195da2f84f）
  - 缓存包 `share/ts/`：dist、dist-raw、esm、node10-16、register、transpilers、node_modules、package.json、tsconfig.schema.json、LICENSE 齐全
  - 缓存包 `bin/`：ts-node、ts-node-cwd、ts-node-esm、ts-node-script、ts-node-transpile-only 5 个 wrapper 齐全
  - Git Bash 下以 sh 执行 `bin/ts-node --version` → v10.9.2；`bin/ts-node smoke.ts` → `ts-node-ok:42:hello ohos`；`bin/ts-node-transpile-only --version` → v10.9.2（wrapper 逻辑端到端验证通过）
- test_package 的 conan 自动化测试在 Windows 本机无法运行（wrapper 为 #!/bin/sh，cmd 无法执行），已用上述 sh 手动等价验证；真机 Linux 上由 CI 执行
- 配方静态检查：py_compile 通过；manifest.yaml/conandata.yml/MANIFEST.yml YAML 解析通过；git diff --check 通过
- 真机/shadow CI 结果：待补（见下方命令）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 库名歧义：任务名 `ts` 10.9.2 | npm 的 `ts` 包仅 0.2.x；10.9.2 对应 Debian 源码包 ts-node | 按 Conan 包名 `ts` 建目录/分支，notes/manifest 注明上游为 ts-node |
| 2 | worktree 检出失败 | 主仓库存在文件名含 `\r` 的 gama patch，Windows 无法创建 | `worktree add --no-checkout` + `checkout -f HEAD`，该文件缺失与主仓库状态一致，不影响本库 |
| 3 | `npm install`/`npm ci` ERESOLVE 失败 | devDep typedoc@0.22.10 声明 peer typescript<=4.5，项目固定 4.7.4 | `--legacy-peer-deps`（typedoc 仅文档工具，不参与构建） |
| 4 | `npm run build-configSchema` 失败 | create-merged-schema 用 axios 下载 json.schemastore.org（远端 403） | 拆分：本地 `npx typescript-json-schema` 生成 tsconfig.schema.json；跳过外网 merge 步骤（记录降级，核心功能不依赖） |
| 5 | `npm prune --omit=dev` 后 ts-node 报 Cannot find module 'typescript'；补装后 smoke 又报 TS2591 Cannot find name 'process' | typescript 与 @types/node 在根项目仅声明为 devDep+peer，prune 视作 dev 删除；而 `npm install typescript` 在干净树会把全部 devDeps 装回并触发 native postinstall（dprint 下载失败） | 构建目录内把这两个包从 devDependencies 移到 dependencies 再 prune（已实测：25 包自洽、全部验证通过） |
| 8 | wrapper 生成静默失败 | Python `str.format()` 把 shell `${TS_HOME:-...}` 当作 format 占位符（KeyError） | wrapper 内容改用字符串拼接，禁用 format（适用于所有含 `${...}` 的配方） |
| 6 | tag 归档无 dist/ | 上游 dist 为构建产物 | 配方内 tsc 编译生成 |
| 7 | 上游 npm test 无法完整运行 | dprint lint 为 native 二进制，无 OHOS 版本 | build 阶段跳过 lint；ava 测试在真机阶段单独执行 |

## 真机 / shadow CI 结果（2026-10-03，已完成 ✅）

job：`ts-10.9.2-20261003`（隔离 job，--repo-source）
run 目录：`~/ohos-test-runs/codex-10.9.2-ts-10.9.2-20261003-conan-20261003-030548-9513`

```text
G0_RESULT=pass
KC_RESULT=pass
JC_RESULT=pass: empty
L0_RESULT=pass: all checks passed
L1_RESULT=pass: test_package executed
L2_RESULT=skip: ts-node version/help failed, ts-node-cwd failed, ts-node-esm failed, ts-node-script failed, ts-node-transpile-only failed
L4_RESULT=pass: no patches
L5_RESULT=pass: bin/ has content
L1e: Negative test confirmed — test genuinely depends on ts
exit-code=0, Pass rate 100.0% (1/1)
```

L2=skip 说明：CI 直接 exec bin/ 下 wrapper，HMDFS 无执行位（E087）必 126 ——
所有脚本型 bin 包的稳定终态（vips PR #4619 同形态 merged 先例）；消费者路径
已由 test_package（sh 显式调用 wrapper）覆盖。

迭代记录（r1-r10）：

| 轮 | 报错原文 | 根因 | 解法 |
|---|---|---|---|
| r1 | L0p: settings 缺少 compiler/build_type | OHOS profile 要求四项 settings | settings = os/compiler/build_type/arch |
| r2 | npm ci → Signal 5 core dump (Check failed: 12 == (*__errno_location())) | hnp npm wrapper V8 DCHECK（DRAFT-npm-ohos-nodejs-toolchain 坑1） | _npm() 直调 npm-cli.js + NODE_OPTIONS=--jitless |
| r3 | EACCES: permission denied, symlink node_modules/.bin/parser | HMDFS 禁 symlink（E018/E080） | npm ci/prune 加 --no-bin-links；tsc 直调 node node_modules/typescript/bin/tsc |
| r4 | tsc → Signal 5 | node 跑重负载 JS 同样触发 V5（不止 npm） | 全部 node 调用统一 --jitless（含 wrapper 内 NODE_OPTIONS 默认值） |
| r5 | bin/ts-node: Permission denied (126) | HMDFS 脚本无执行位（E087） | test_package 经 self.dependencies 取 wrapper 路径，sh 显式执行 |
| r6 | command -v 找不到无执行位文件 (127) | command -v 不见 noexec 文件 | 改用 package_folder 拼绝对路径 |
| r7 | AttributeError: rootpath | Conan 2 API | dependencies[...].package_folder |
| r8 | wrapper 内 node: inaccessible or not found (127) | conanrun PATH 无 hnp bin | wrapper 内 PATH 前置 /data/service/hnp/bin |
| r9 | **exit 0 全过**（L2 skip: node_modules 内 tsc/tsserver 被探测） | CI find -name bin 误探嵌套 bin（alexjs 坑4） | package() 清理 node_modules 内 bin/.bin |
| r10 | exit 0 全过（终态） | — | — |

上游 ava 套件（真机实测归因，最终 133/287）：
- 上游 N=287（src/test 10 spec 编译至 dist/test；需临时放开 tsconfig.build-dist.json 的 exclude）
- 无 --jitless：node V8 Signal 5 core dump（exit 133），无法运行 —— 平台强制 jitless
- 真机验证环境修正（仅设备端运行时调整，未改上游测试语义）：
  1. harness 的 `npm install`/`npm pack` 改为 `node <npm-cli.js>` 直调（hnp npm wrapper Signal 5）+ `--no-bin-links`（HMDFS 禁 symlink）
  2. **typescript@latest（5.9+）新包结构不含 lib/typescript.js**（需 postinstall 补全，全程 --ignore-scripts 被跳过）→ require('typescript') 返回 2-key 残缺对象、ts.sys undefined → pin typescript@4.7.4（与上游 devDep 一致）后修复
  3. harness 的 `node_modules/.bin/ts-node*` 直调改为 `node <dist/bin*.js>`（HMDFS noexec）
- 最终：**133 通过 / 152 失败 / 3 skip**（21 → 67 → 133 三轮递进）
- 152 失败三类归因（附报错定位）：
  1. **module-node/esm-loader 类（~60）**：`ReferenceError: WebAssembly is not defined` @ node 内置 amaro（node 24 strip-types loader，lib/wasm.js）—— **--jitless 同时禁用 JIT 与 WebAssembly**，node 内置 TS loader 无法初始化；不用 jitless 则 Signal 5。平台二选一硬限制
  2. REPL 类（21）：交互 pty 场景在非交互 CI 环境失败
  3. resolver/register 级联（~50）：node 24 ESM 解析行为差异 + tmp 测试文件级联缺失（`Cannot find module .../tests/tmp/...`）
- 结论：非缺依赖（requirements 为空，npm ci 579 包全部安装成功）；ts-node 本体功能由真机 test_package 三断言 + L1e 破坏性验证确认

## 真机 CI 自检记录（第一部分，2026-10-03）

- [x] G0e 根目录白名单：通过（杂项均为主干已跟踪目录；工具生成的 feedback 文件已清理）
- [x] JC 垃圾文件：通过（__pycache__/reports/conanbuild.bat 等已清除；reports/ 在 .gitignore 内）
- [x] KC 知识草稿：DRAFT-ts-10.9.2-npm-peer-deps-pruned.md/.kv 成对、非空壳
- [x] L0 逐条：conanfile 语法/manifest/test_package/MANIFEST/真实 test()/commands.json（含 bin/ 工具包）/目录结构/分支名 feat/ts-10.9.2-codex/无硬编码 remote/无外部 curl/self.run 无 ${} 变量/版本未占用
- [x] L1e 自测：Git Bash 下 round1 intact=PASS（version+smoke+类型拒绝），round2 破坏 dist/ 后 FAIL —— 真测试确认
- [x] conan-verify：G1 PASS（补 export_sources + apply_conandata_patches 后）；G2 包装器在 Windows 报 WinError 2（环境限制），已用 `conan create -pr:h ci/conan/profiles/ohos-aarch64` 手动等价验证：build+package 全过，test 阶段仅因 Windows 无法执行 sh wrapper 失败（真机 Linux 预期通过）
- [x] lang-preflight：task=cpp vs detected=nodejs（env_unsupported）—— ts-node 本就是 npm 项目，任务大厅批量导入默认标 cpp；仓库已有 tailwindcss/codecov-cli 等 nodejs 库先例；**需平台侧按 detected_language 迁移任务语言，或确认接受**，存在任务被平台迁移/取消的风险
- [x] 真机 SSH：恢复后已完成全部 shadow CI（见下方结果）

## 依赖版本

- Node.js: v24.13.0 (真机 /data/service/hnp/bin/node)；本机验证用 Windows node v24.9.0
- typescript: 5.x（npm 自动安装的 peer，node_modules 内自带）

## 注意事项

1. ts-node 是纯 JS 项目：无 ELF 产物，无需 binary-sign-tool
2. wrapper 为 #!/bin/sh 脚本，依赖系统 node 在 PATH 中
3. 真机执行 ava 时注意 E046/E011（HMDFS 权限/临时目录）与 E055（subprocess 差异）类问题，参考知识图谱
4. 不要把 `tests/ts-node-packed.tgz`、`tests/node_modules/`、`tests/tmp/` 等构建副产物提交到 Git

---

**前置适配完成**: 2026-10-03
**最终状态**: built（本机前置验证通过；真机 shadow CI 待执行）
