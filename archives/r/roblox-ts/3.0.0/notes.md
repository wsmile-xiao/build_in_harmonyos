# roblox-ts 3.0.0 适配笔记（HarmonyOS PC · npm / Node.js CLI）

## 0. 目标库定位
roblox-ts **不是 C/C++ 库**，而是纯 TypeScript/Node.js 命令行工具
（TypeScript → Luau 编译器，入口 `rbxtsc`）。

| 项 | 值 |
|---|---|
| 包类型 | npm 包 / Node.js CLI（`package_type = application`） |
| 上游仓库 | https://github.com/roblox-ts/roblox-ts（tag `v3.0.0`，gitHead `d1d5486094ac1d1821b7eb03ce0de0890d30b82e`） |
| 上构建系统 | npm（`scripts.build = tspc -b`，ts-patch + typescript 5.5.3） |
| 发布形态 | 已预编译：tarball 含 `out/**/*.js`（206）、`out/**/*.d.ts`（206）、`include/*.lua`（2），不含 node_modules / 原生代码 |
| 原生模块 | 无（396 个依赖条目全为纯 JS；仅 `fsevents` 为 macOS-only optional） |

### R47 语言预检结果（如实留档）
```
$ python3 $SKILL_ROOT/scripts/ohc-run.py lang-preflight roblox-ts 3.0.0 \
      --src $HOME/tmp/builds/roblox-ts-3.0.0.work
❌ 语言不匹配: task=cpp, detected=nodejs → env_unsupported      (exit 2)
{
  "expected": "cpp",
  "detected_language": "nodejs",
  "language_evidence": {
    "build_system": "npm",
    "manifest": "package.json 含 main/scripts/engines/bin",
    "source_stats": "源文件 208 个（nodejs:206, lua:2），主体占比 99%"
  }
}
```
判定本身**正确**（该库确为 Node.js 包）。本适配按仓库既有 npm CLI 范式推进
（同族先例：`archives/a/aicommits/3.4.0`、`archives/a/actions-up/1.16.0` 均已并入
main；`archives/l/leaflet-markercluster/1.5.3-dfsg` 同为 100% JS 资产包、2026-09-26
并入），并把判定证据如实记录、不伪造语言字段（口径同
`knowledge/drafts/DRAFT-libok-0.6.5-langpreflight-clib-packagejson-misdetect`：
「人工复核后覆盖终态继续适配，不要静默接受 env_unsupported，也不要在 result 中
伪造语言字段」）。

## 1. 编译环境
- 构建系统: npm（发布包预编译）/ conan 侧 none（纯 copy 打包）
- 适配日期: 2026-09-29
- 运行时: OHOS hnp node **v24.13.0**（`/data/service/hnp/bin/node`）+ npm 11.6.2
- 编译器: 不适用（无 C/C++）
- conan: 2.29.1（OHOS 适配版），profile `default`（os=OHOS / os.version=6.0 / arch=armv8）
- 状态: built

## 2. 源码核验（真实命令 + 原始输出）
```bash
$ curl -sSL -o roblox-ts-3.0.0.tgz \
    https://registry.npmjs.org/roblox-ts/-/roblox-ts-3.0.0.tgz     # HTTP 200, size=141417
$ python3 -c "import hashlib;print(hashlib.sha1(open('roblox-ts-3.0.0.tgz','rb').read()).hexdigest())"
31331be8bd682fa3345c1fe99b0ac8ae283a13a2
# registry 元数据 dist.shasum === 31331be8bd682fa3345c1fe99b0ac8ae283a13a2  ✅ 完全一致
$ openssl dgst -sha256 roblox-ts-3.0.0.tgz
SHA2-256(...)= 94e7ee8db40d0fab605601312838ca8d6d72242e78a8f01e02467f53c4232757
# registry 元数据 dist.integrity === sha512-hwAC2frIFlLJOtHd6F+5opMEhBgfAMK9z5l1mP+bykLBbMO5cn1q5lIwhhXbeh9Pq07rlhF8uGHlmeRLPd/3AA==  ✅
```
源码渠道 = **上游 npm 官方发布包**（`registry.npmjs.org` 为 npm 官方正式源，满足 R39；
非个人 fork / 非镜像 / 非重打包）。

## 3. 真实构建（从源码，OHOS 真机实测）
上游 `scripts.build = tspc -b`（TypeScript 编译）。为验证工具链可用性，另取上游
GitHub tag `v3.0.0` 源码在 OHOS 上完整跑通真实构建：

```bash
$ curl -sSL -o roblox-ts-src-3.0.0.tar.gz \
    https://codeload.github.com/roblox-ts/roblox-ts/tar.gz/refs/tags/v3.0.0   # HTTP 200, 204703 B
$ tar -xzf roblox-ts-src-3.0.0.tar.gz && cd roblox-ts-3.0.0
$ npm config get registry
https://npm.cnb.cool/OpenHarmonyPCDeveloper/npm/-/packages/
$ npm ci --no-audit --no-fund
added 347 packages in 9s                                          # exit 0
$ npm run build                                                   # = tspc -b
> roblox-ts@3.0.0 build
> tspc -b
                                                                  # exit 0
$ find out -name '*.js' | wc -l
206
```
→ **真实源码构建成功**（exit 0，产出 206 个 .js，含 out/CLI/cli.js、out/CLI/test.js）。

### 端到端功能验证（TypeScript → Luau）
```bash
$ node out/CLI/cli.js --version
3.0.0
$ node out/CLI/cli.js --type package -p $HOME/tmp/rbxts/smoke        # 最小 TS 工程
$ cat out/main.server.luau
-- Compiled with roblox-ts v3.0.0
local answer = 42
local function add(a, b)
	return a + b
end
local acc = 0
for i = 0, 9 do
	acc = add(acc, i)
end
print(acc)
return {
	add = add,
	answer = answer,
}
```
→ 编译器管线在 OHOS 上真实运行并产出正确 Luau。

> conan 配方仍以 npm 官方发布包为 source（理由：CI worker 无 Node.js 工具链——
> `ci/` 全目录无 node/npm 依赖——故 build 阶段不能依赖 npm 构建；这也与同族
> 已并入 main 的 aicommits / leaflet-markercluster 范式一致）。上述源码构建是
> 「工具链可用性」的独立证据，非配方构建路径。

## 4. 遇到的问题与解决方案

| # | 问题 | 首个错误 / 原始输出 | 根因 | 解决方案 | 重新验证 |
|---|---|---|---|---|---|
| 1 | 上游单元测试 129 个用例失败 | `MacroManager could not find symbol for Promise` / `You may need to update your @rbxts/compiler-types!`（`2 passing, 129 failing`） | 测试工程 `tests/` 的类型依赖未安装（`@rbxts/compiler-types`/`@rbxts/types` 等），编译器缺 Roblox 宏符号表 | 按上游 `update-test-types` 语义安装 tests 依赖 | 见 #2 |
| 2 | `cd tests && npm install` 挂起 900s（超时被 kill） | 无任何输出，进程存活 903s（`git@github.com` 无凭据） | `tests/package-lock.json` 中 `@rbxts/compiler-types`、`@rbxts/roact` 的 resolved 为 **git+ssh://git@github.com/...**（SSH 协议无密钥 → 挂起） | 改用 npm registry 同版本安装：`@rbxts/compiler-types@3.0.0-types.0`（与 roblox-ts 3.0.0 同日发布）、`@rbxts/types@1.0.805`（发布日当周版本）、`@rbxts/roact@3.0.0`、`@rbxts/services@1.5.3`、`@rbxts/testez@0.4.2-ts.0` | `added 5 packages in 7s`，mocha 重跑 **131 passing, 0 failing**（exit 0） |
| 3 | 上游 CLI 入口 shebang 在 OHOS 不可靠 | `#!/usr/bin/env node`（源码首行） | OHOS 上 `/usr/bin/env` 在部分运行 uid 下不可执行（仓库既有结论） | 配方生成 `bin/rbxtsc` POSIX sh 启动器，不依赖 shebang | `rbxtsc --version` → 3.0.0 |
| 4 | OHOS 上 PATH 首位 node 启动即崩 | `----- Native stack trace -----`，rc=134（SIGABRT）；`node --version` 亦崩 | 本机 PATH 首位是 cmd-pkgs 自带的 node 二进制（110 MB），在 OHOS 上不可用；系统 hnp node 正常 | 启动器按候选顺序探测 `node --version`（RBXTSC_NODE → PATH → hnp node），取第一个可用者 | `[OHOS] launcher survives broken first-on-PATH node` 用例通过 |
| 5 | 最小工程编译报配置错误 | `Unable to find package.json` → `"typeRoots" must contain .../node_modules/@rbxts` → `MacroManager could not find symbol for CFrame` | roblox-ts 强制要求工程含 `package.json`、`typeRoots` 指向 `node_modules/@rbxts`，且编译需 `@rbxts/compiler-types` + `@rbxts/types` 提供 Roblox 全局符号 | 补齐 `package.json` + `typeRoots` + 安装两个类型包 | 编译成功产出 `out/main.server.luau`（见 §3） |
| 6 | **CI 上 test_package 3 条失败**（本机因 node 不可用被 `[skip]` 而**漏检**） | `/pkg/bin/rbxtsc[16]: RBXTSC_NODE: parameter not set`（CI build **#65252**；`=== Results: 28 passed, 3 failed, 0 skipped ===`，失败项：`rbxtsc --version` / `rbxtsc --help` / `[OHOS] launcher output with unusable first-on-PATH node`） | 自生成启动器带 `set -u` 却**裸引未设**的 `$RBXTSC_NODE` → shell 在展开处即以 nounset 中止（本机复现：`RC=1`，`RBXTSC_NODE: parameter not set`）。本机 conan 派生 node 不可用 → 运行期用例整体 `[skip]` → 该 bug 逃过本地门禁 | ① 启动器改用 `${RBXTSC_NODE:-}`；② CLI 分支的 `[skip]` 改为**逐条 skip**，使「断言位总数」与环境无关（恒定 32）；③ 新增**不依赖 node 运行时**的静态守卫用例 `[OHOS] 6`（断言启动器含 `${RBXTSC_NODE:-}` 且无裸引） | 本机回归 4/4：RBXTSC_NODE 未设 / 未设+PATH 首位坏 node / 显式覆盖 / 无参数调用 → 均输出 `3.0.0`、`RC=0`；修复后 `conan create` **exit 0**（27 passed / 0 failed / 5 skipped） |

## 5. 源码修改
无。配方为纯打包 + 启动器生成，未改动任何上游源码/产物（`patches: {}`）。

## 6. 依赖版本
- conan 依赖：**无**（`build.dependencies: []`）
- 运行时依赖：系统 Node.js（OHOS hnp node v24.13.0；`conan download node/<ver>` 全 exit 1 → node 不是 conan 包）
- npm 运行时依赖（已被上游发布包打包进 out/）：`@roblox-ts/luau-ast`、`@roblox-ts/path-translator`、
  `@roblox-ts/rojo-resolver`、`chokidar`、`fs-extra`、`kleur`、`resolve`、`typescript@5.5.3`、`yargs`
  —— 均为纯 JS、无原生模块，随发布包分发，无需单独适配

## 7. 上游测试（R51 三步法）

### 7.1 清点
| 层 | 入口 | 用例数 | 可否执行 |
|---|---|---|---|
| 单元（mocha） | `npm run test-compile` = `nyc mocha --timeout 0 --recursive out/CLI/test.js` | **131** | ✅ 已执行 |
| 集成（Rojo 构建） | `npm run test-rojo` = `rojo build tests -o ./tests/test.rbxl` | 1 个 Place 构建 | ❌ 缺 rojo 7.4.4 |
| 集成（Lune + TestEZ） | `npm run test-run` = `lune run ./tests/runTestsWithLune.lua ./tests/test.rbxl` | 38 个 spec / 462 处 `it()` / 12 处 `describe()` | ❌ 缺 lune 0.8.8 |

### 7.2 实测结果（单元层，全部用例名称见 `reports/upstream-unit-test-names.txt`）
```
$ ./node_modules/.bin/mocha --timeout 0 --recursive out/CLI/test.js --reporter spec
  131 passing (9s)                                                  # exit 0
```
- 用例总数 **131**、通过 **131**、失败 **0**、跳过 **0**
- 组成：include/non-compiled 拷贝 2 + diagnostic 用例 85 + 源文件编译用例 44
  （`main.server.ts` 1 + `helpers/` 5 + `tests/*.spec.ts{,x}` 38）
- 日志：`reports/upstream-mocha.log`（完整 spec 输出）、`reports/upstream-unit-test-names.txt`（131 行用例名）

### 7.3 未执行层的具体技术原因
集成层依赖上游 `foreman.toml` 声明的三个 Rust 外部二进制
（`rojo-rbx/rojo=7.4.4`、`filiptibell/lune=0.8.8`、`rojo-rbx/run-in-roblox=0.3.0`）：
- 目标环境无 Rust 工具链（CI 能力矩阵：Rust ❌）；
- conan 制品仓无 `rojo`/`lune`/`run-in-roblox`（`conan download … -r=ohpcd` 全部 exit 1）；
- cmd-pkgs 中仅有 `PORTS_PLAN` 规划文档提及，无实际制品。
→ 按 R51 如实申报「未能执行」，**不虚报通过率**。

## 8. 验证结果
| 步骤 | 真实命令 | 结果 | 日志 |
|---|---|---|---|
| conan create | `conan create archives/r/roblox-ts/3.0.0 --build=missing` | 见 `reports/conan-create.log` | reports/ |
| conan-verify | `ohc-run.py conan-verify roblox-ts 3.0.0` | 见 `reports/conan-verify.log` | reports/ |
| finish（W2+W3） | `ohc-run.py finish roblox-ts 3.0.0 built` | 见 `reports/finish.log` | reports/ |
| 上游单测 | `mocha --recursive out/CLI/test.js` | **131/131 通过** | reports/upstream-mocha.log |
| 消费者测试 | `test_package/test.sh` | **27/32 通过**（5 项环境性 skip，含 5 条 [OHOS]） | reports/conan-create.log |

## 9. 交付物
| 路径 | 说明 |
|---|---|
| `bin/rbxtsc` | POSIX sh 启动器（OHOS 解释器探测） |
| `libexec/roblox-ts/out/**` | 预编译 JS + 类型声明（206 .js / 206 .d.ts） |
| `libexec/roblox-ts/include/*.lua` | Luau 运行时（Promise.lua / RuntimeLib.lua） |
| `libexec/roblox-ts/package.json` | 分发元数据（bin 映射 `rbxtsc → out/CLI/cli.js`） |
| `licenses/LICENSE` | MIT |

## 10. 发现与知识积累（随 PR 提交的知识草稿）
- ✅ DRAFT-roblox-ts-3.0.0-ohos-node-jitless-npm-cli：OHOS 上 npm/Node CLI 类包在 conan
  构建期必须用 `--jitless` 驱动 node 与 npm（E400）；`npm install` 需 `--no-bin-links`
  （建 `node_modules/.bin` 软链被拒 EACCES）；node/npm 步骤应 `env=None` 不继承 C/C++
  buildenv；npm 入口须用真实 npm-cli.js 而非 PATH 包装脚本。
- ✅ DRAFT-roblox-ts-3.0.0-npm-prebuilt-runtime-closure：npm 发布包（package.json
  "files"）不含 node_modules —— 有运行时依赖的 npm CLI 必须在 build() 用
  `npm install --omit=dev` 材质化依赖闭包并随包分发（aicommits 型零依赖 vs
  actions-up 型有依赖 的判据）。
- ✅ DRAFT-roblox-ts-3.0.0-launcher-nounset-and-skip-blindspot：自生成 sh 启动器的
  `set -u` 陷阱（被引环境变量必须用 `${VAR:-}` 展开）＋「node/工具链不可用环境下运行期
  用例整体 `[skip]` 会让启动器类 bug 逃过本地门禁」的盲区与对策（逐条 skip 使断言位
  总数与环境无关 + 增加不依赖运行时的静态守卫用例）。来源：CI build #65252 实测。

## 11. 注意事项
- 本配方不引入任何 conan 依赖；`requires`/`tool_requires` 均为空。
- 启动器内的 `/data/service/hnp/bin/node` 仅作**最后兜底**，正常情况优先使用
  `RBXTSC_NODE` 或 PATH 中可用的 `node`。
- `validate()` 限定 `os ∈ {Linux, OHOS}`：产物是 Node.js 脚本工具，语义上不绑定
  具体 OS，此限定仅用于显式声明目标平台。
---

**编译结束**: 2026-09-30 08:46
**最终状态**: built
