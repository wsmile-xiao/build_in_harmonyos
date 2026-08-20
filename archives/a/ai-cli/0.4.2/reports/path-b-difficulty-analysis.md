# ai-cli 0.4.2 路径 B 困难库适配分析报告

## 1. 申报边界

- 关联 Issue：`#2284`
- 关联 PR：`#5837`
- 适配路径：路径 A（基础适配）+ 路径 B（困难库适配分析报告候选）
- 不申报路径 C（高难度挑战）
- 不将本报告声明为已获评审认可的正式知识条目

本报告的路径 B 申报依据不是“新增一个仅对 ai-cli 生效的补丁”，而是记录
Node.js CLI 在 HarmonyOS PC 上遇到的运行时启动失败、JITless 与 WebAssembly
能力冲突，以及 Shadow CI 跨 UID 缓存执行权限问题。最终路径 B 资格和分值以
评审委员会结论为准。

## 2. 软件与适配对象

| 项目 | 内容 |
|---|---|
| 上游项目 | `vercel-labs/ai-cli` |
| 上游版本 | `v0.4.2` |
| 上游提交 | `2a72d32793e21839439e96adc8429453f17500f1` |
| 发布物 | npm release `ai-cli-0.4.2.tgz` |
| 发布物 SHA256 | `1552fe238facb166cb09dcd626e31e53925458196e74bdbd876a2c97369c4f80` |
| 运行时要求 | Node.js 22 或更高版本 |
| 真机运行时 | Node.js `v24.13.0` / OHOS armv8 |
| 构建方式 | 校验并打包上游预构建 JavaScript bundle 与 OpenH264 WASM |

npm release 已将 `ai@7.0.3`、`@ai-sdk/gateway@4.0.3` 和
`commander@^14.0.3` 打包进 `dist/index.js`。因此 W0 未发现需要拆分到独立 PR
的 Conan 依赖库，困难点集中在目标系统的运行时与制品执行边界，而不是依赖
源码编译。

## 3. 真实失败链

### 3.1 Node.js 在业务 JavaScript 执行前以 Signal 5 退出

在 OHOS 真机上，普通 Node.js 启动路径执行 ai-cli 的 `--version` 或 `--help`
时稳定失败：

```text
Check failed: 12 == (*__errno_location())
Signal 5
```

该失败发生在可观察的业务 JavaScript 输出之前。为排除环境变量和 ai-cli
参数解析的偶然影响，诊断覆盖了以下组合：

| 诊断项 | 结果 |
|---|---|
| 继承 Shadow CI 环境运行 | Signal 5 |
| 最小环境运行 | Signal 5 |
| `--v8-pool-size=1` | Signal 5 |
| `--max-opt=0` | Signal 5 |
| `--no-sparkplug` | Signal 5 |
| `--no-maglev` | Signal 5 |
| `--no-turbofan` | Signal 5 |
| `--single-threaded` | Signal 5 |
| `--jitless` | `--version`、`--help` 和消费者断言通过 |

证据能够把故障边界收敛到当前 OHOS Node/V8 的 JIT 初始化路径，但不足以把
根因进一步归结为某一个内核接口或 V8 源码缺陷。因此配方只采用经过验证的
平台条件分支，不在报告中虚构未经证实的底层根因。

### 3.2 JITless 可运行，但同时关闭 WebAssembly

`--jitless` 能使 CLI 的确定性文本入口运行，但真机执行：

```sh
node --jitless -e 'console.log(typeof WebAssembly)'
```

得到：

```text
undefined
```

ai-cli 发布物包含 `dist/openh264-d6yed0d8.wasm`。因此 `--jitless` 不是对所有
Node.js CLI 都无损的通用修复：它适用于本轮验证的版本、帮助和文本命令入口，
但不能证明依赖 OpenH264 WASM 的多媒体路径可用。这一能力冲突必须在配方、
测试报告和 PR 限制中同时披露。

### 3.3 Shadow CI 缓存改变 launcher 的直接执行条件

第三次 Shadow CI 已完成源码获取、build 和 package，但 test_package 直接执行
`bin/ai` 时退出码为 126。设备缓存中的 launcher 表现为：

| 属性 | 观测值 |
|---|---|
| 文件模式 | `0750` |
| 缓存属主 UID | `20001006` |
| SSH/测试运行 UID | `20020083` |
| 直接执行 | `Permission denied` / exit 126 |

配方显式设置 `0755` 仍不能改变已经物化到跨 UID 缓存后的直接执行条件。最终
test_package 在 OHOS 上使用 `/system/bin/sh` 执行同一 Conan package folder
中的真实 launcher；Linux 仍按正常方式直接执行。负向测试移走 package 的
`bin/`、`lib/` 和 `include/` 后必须失败，从而排除了测试误用源码树或系统同名
命令的可能。

## 4. 可复用的诊断结论

本报告不把 `--jitless` 本身申报为新知识。已有适配记录已经使用过该参数，
通用脚本权限问题也已有说明。本报告作为困难库分析材料，新增的可复核边界是：

1. 对 Node.js CLI，应先用最小 JavaScript/版本入口区分“业务代码失败”和
   “运行时在业务代码前失败”，不能把 Signal 5 误报为上游 CLI 缺陷。
2. 缩小 V8 优化范围的参数仍失败时，`--jitless` 只能作为受限降级路径；必须
   额外检查 `typeof WebAssembly`，不能只凭 `--help` 通过宣称功能完整。
3. 对同时打包 WASM 的 Node.js CLI，JITless 与 WASM 能力之间存在明确冲突；
   文本入口通过不能替代多媒体、编解码或其他 WASM 路径验证。
4. Shadow CI 的 package cache 可能改变脚本的属主和直接执行权限。消费者测试
   可以通过目标系统 shell 执行真实 package launcher，但必须同时使用 package
   folder 约束和破坏性负向测试证明没有绕开被测制品。
5. 配方应仅在 OHOS 条件分支使用运行时降级参数，避免把目标平台限制传播到
   Linux 等本来可以使用正常 JIT 的平台。

这些结论适用于“Node.js CLI + 预构建 bundle + 可选或必需 WASM + Conan
package cache”这一类适配，不依赖 ai-cli 的命令名称或单一业务逻辑。

## 5. 与现有材料的差异

- `archives/u/uglifycss/0.0.29/notes.md` 已记录 Node/V8 Signal 5 和
  `--jitless`，所以本报告不重复申报“使用 JITless”本身。
- 共性避坑指南已记录脚本执行权限与 shebang 问题，所以本报告不重复申报
  “使用 shell 执行脚本”本身。
- 本报告的困难库分析重点是 JITless 与发布物 WASM 能力冲突、Shadow CI
  package cache 的跨 UID 实证，以及如何用消费者断言和负向测试保持验证闭包。

## 6. 验证证据

最终单包 Shadow CI：

```text
run_id=codex-ai-cli-shadow-ci-r5-2284-20260819-182455-17982
input_sha256=53383b4ea19264386c0ff403656d208ba98ec5a3605643e76e2f82d55a00ad49
snapshot_commit=31f44bbb5605d10daa0e34821c0e062be3f8aabd
L0_RESULT=pass
KC_ERRORS=0
JC_ERRORS=0
L1_RESULT=pass
L4_RESULT=pass
L5_RESULT=pass
negative_test=pass
Build Summary: Total 1, Success 1, Failed 0
consumer_assertions=7/7
```

L2 因直接执行缓存 launcher 的跨 UID 权限限制而非阻塞跳过；L1 已通过
`/system/bin/sh` 运行同一 package folder 中的 launcher，并验证版本、顶层命令
和帮助输出。

报告是在 r5 通过后增加的文档文件。r5 的配方、launcher 和 test_package 内容
未因路径 B 申报而修改；上述 input SHA256 对应报告加入前的可执行适配快照。

## 7. 测试完整性与未解决项

- 上游标签中发现 15 个 TypeScript 测试文件和 135 个 `test(...)` 声明。
- 已从上游源码提交 `2a72d32793e21839439e96adc8429453f17500f1` 创建干净检出，按
  `packageManager: bun@1.3.9` 安装锁定依赖并执行原生 `bun test`；结果为
  `135 pass, 0 fail`，覆盖 15 个文件。初次隔离运行仅因测试子进程找不到 `bun`
  而失败，修正运行器 PATH 后未修改测试源码即全部通过。
- 该 135/135 是上游源码检出的主机验证结果；它不替代 OHOS 真机运行时验证，
  也不把 npm release tarball 中不存在的测试文件误报为制品内测试。
- AI 生成需要 Gateway 凭据和网络，本轮未使用生产凭据进行在线调用。
- 多媒体/OpenH264 路径受 JITless 下 WebAssembly 不可用影响，尚未验证并可能
  不可用。
- 当前证据证明离线 CLI 入口与 package launcher 可用，不宣称 ai-cli 全部业务
  能力已在 OHOS 上闭环。

## 8. 评审请求

申请评审委员会按“路径 B：困难库适配分析报告”审阅本材料，重点复核：

1. Signal 5 诊断矩阵是否足以证明运行时启动边界；
2. JITless/WASM 能力冲突是否被完整、保守地披露；
3. 跨 UID package cache 的消费者验证与负向测试是否形成有效证据链；
4. 上游 Bun 1.3.9 的 135/135 源码测试结果是否满足路径 B 审查的测试完整性要求；
5. 上述分析是否达到路径 B 的可复用性要求。

若评审认为其与既有材料重复或难度不足，则本 PR 仅按路径 A 计分，不将候选
申报表述为既成的路径 B 结论。
