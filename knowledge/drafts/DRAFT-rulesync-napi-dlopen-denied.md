# DRAFT: HMDFS 工作区下 Node N-API 原生扩展 dlopen 被拒

## 结论速览

在 **HMDFS 租户工作区**（`u:object_r:hmdfs:s0`）中，ELF **可以 execve（签名后）但不能 dlopen**：
原生 N-API 扩展（如 rolldown 的 `rolldown-binding.openharmony-arm64.node`）
即使已 `binary-sign-tool -selfSign 1` 签名（`.codesign` 段存在、mode 755），
`dlopen` 仍返回 `Permission denied`（`ERR_DLOPEN_FAILED`）。
任何依赖原生 addon 的 Node 工具链（vite 8 / vitest 4 → rolldown；napi-rs 加载器）
因此无法在该工作区启动。napi-rs 的 WASI 回退也不是逃生口：
`NAPI_RS_FORCE_WASI=true` 会走到 `node:wasi` 并在 `uvwasi_init` 处以 `UVWASI_EBADF`(errno 8) 失败。

## 复现与证据（全部实测）

```bash
# 1) dlopen 原生扩展（已签名）失败
$ node -e "require('@rolldown/binding-openharmony-arm64')"
ERR_DLOPEN_FAILED | Error loading shared library
  .../rolldown-binding.openharmony-arm64.node: Permission denied

# 2) 同一工作区内「签名后 execve」成功（对照组，证明不是签名/权限位问题）
$ cp /data/service/hnp/bin/bash ./bash.bin && chmod 755 ./bash.bin
$ ./bash.bin -c 'echo X'            → permission denied (126)
$ binary-sign-tool sign -inFile ./bash.bin -outFile ./bash.signed -selfSign 1
$ chmod 755 ./bash.signed && ./bash.signed -c 'echo EXEC_SIGNED_OK'   → EXEC_SIGNED_OK , EXIT=0

# 3) 签名确实写入（排除「没签上」）
$ readelf -S rolldown-binding.openharmony-arm64.node | grep codesign
  [26] .codesign   PROGBITS ...        # 存在

# 4) WASI 回退不可用
$ NAPI_RS_FORCE_WASI=true node -e "import('rolldown')"
ERR | UVWASI_EBADF, uvwasi_init

# 5) 上游测试运行器因此无法启动
$ node node_modules/vitest/vitest.mjs run
Startup Error: Cannot find native binding ... code: 'ERR_DLOPEN_FAILED'
```

已排除的方向：`LD`/`LD_LIBRARY_PATH` 污染（E131）、optional 依赖缺失（`@rolldown/binding-openharmony-arm64@1.1.5` 已装且符号链接正确）、
`env -i` 最小环境、cwd、chmod/执行位。

### 补充实验（第二轮针对性修复，全部为实测）

| 实验 | 命令 | 结果 |
|---|---|---|
| 对照：hnp_file 标签路径的普通 .so | `node -e "process.dlopen({exports:{}}, '/data/service/hnp/bind.org/bind_9.18.21/lib/libssl.so.3')"` | `ERR_DLOPEN_FAILED | Module did not self-register` → **文件被成功打开**（仅类型不符），说明该路径 dlopen 未被拒 |
| 对照：rootfs | `process.dlopen({exports:{}}, '/lib/ld-musl-aarch64.so.1')` | 同上 `Module did not self-register` → **可打开** |
| 目标：hmdfs 工作区（已签名） | `require('.../rolldown-binding.openharmony-arm64.node')` | `ERR_DLOPEN_FAILED | Permission denied` → 被拒 |
| 其它 tmpfs（`/dev/shm`，可写） | `cp …b.node /dev/shm/ && chmod 755` | `chmod: Permission denied`；`require` → `Permission denied` |
| 其它挂载点（`/storage/hmdfs`、`/storage/External`、`/storage/userExternal`、`$HOME/appdata`(sharefs)、`/data/*`） | `mkdir -p … && cp …` | 全部不可写（`/data/*` 属 root/installs，无写权限） |
| WASI 回退（禁用 preopen） | 将 `rolldown-binding.wasi.cjs` 的 `preopens` 改为 `{}` 后 `NAPI_RS_FORCE_WASI=true node -e "import('rolldown')"` | 仍 `UVWASI_EBADF, uvwasi_init` → **与 preopen 无关** |

**推论**：dlopen 的可加载性由**挂载点/标签**决定（hnp_file、rootfs 可加载；`hmmac=use_task` 的 tmpfs/HMDFS 被拒），
而本环境中所有**可写**目录都属于后者 → 在该工作区内无法加载任何自备原生扩展（无 root 无法把文件放入白名单路径）。

## 处置

### 已验证的可行路径：替换原生绑定为 WASM 运行器组合（推荐）

当必须在该工作区内真实执行 JS/TS 上游测试时，用"**降级运行器 + WASM 替代原生绑定**"：
上游默认 `vitest 4 + vite 8`（rolldown 原生绑定）→ 改为 **`vitest 3` + `vite 7`**（esbuild 以**子进程**执行，不受 dlopen 限制），
并把 **`rollup` 整体替换为官方 WASM 实现**（vite 7 仍依赖 rollup）：

```bash
pnpm add -D vitest@3 vite@7
# pnpm-workspace.yaml
#   overrides:
#     rollup: npm:@rollup/wasm-node@4.59.0      # 官方纯 WASM 构建；无需 dlopen
pnpm install --ignore-scripts --no-frozen-lockfile

# 单元（329 文件 / 7456 用例，实测 7448 pass）
node node_modules/vitest/vitest.mjs run --silent=true --reporter=json --outputFile=unit-results.json

# E2E：RULESYNC_CMD 必须是 dist-bun/rulesync-<platform>-<arch> 形式；用 wrapper 执行真实构建产物
mkdir -p dist-bun
printf '#!/bin/sh\nset -eu\nexec node "%s/dist/cli/index.js" "$@"\n' "$PWD" > dist-bun/rulesync-ohos-arm64
chmod 755 dist-bun/rulesync-ohos-arm64
RULESYNC_CMD=dist-bun/rulesync-ohos-arm64 node node_modules/vitest/vitest.mjs run --config vitest.e2e.config.ts
```

实测结果（rulesync 14.2.0）：单元 7456 用例 **7448 pass / 8 fail**；E2E 720 用例 **719 pass / 1 fail**；
**测试用例零改动**，失败项均属平台矩阵（上游自更新二进制无 openharmony 资产）、HMDFS 文件系统语义、
缺 Bun 运行时或输出捕获等**环境因素**。

配套要点：
- `esbuild` 在 OHOS 上是**子进程二进制**（`@esbuild/openharmony-arm64` 自 0.25.6 起提供）→ 可执行、不受 dlopen 限制；
  故**不要**选 esbuild < 0.25 的 vite（vite 5 依赖 esbuild 0.21，无 OHOS 构建）。
- **tsx 在本工作区不可用**（`listen EPERM`：其 IPC 命名管道创建于 `$TMPDIR`，HMDFS 不允许）；
  E2E 因此必须走 `RULESYNC_CMD` wrapper 路径而非默认 `tsx src/cli/index.ts`。
- `node:wasi` 亦不可用（最小 `new WASI(...)` 即 `uvwasi_init` → `UVWASI_EBADF`），故 rolldown 的 wasm 回退无效。
- 若目标包**必须**用原生 addon，则该包的上游测试只能移出本工作区执行。


1. **不要把签名+execve 通过当作「已修复」**：判据必须是目标动作本身（dlopen）成功。
2. 把 addon 依赖步骤（`pnpm test` / `pnpm test:e2e` 等）放到 **checkout 位于可 dlopen 文件系统的 worker/CI** 执行。
3. 本工作区内仍可产出**真实交付证据**：`npm install --ignore-scripts --omit=dev` 物化运行时依赖树，
   再执行打包后的 launcher 端到端（`--version` / `init` / `generate`）与配方 `test_package`。
4. 上游套件**未执行就如实报告未执行**（附阻塞证据），严禁标记为通过或吞掉退出码。

## 相关观察（未定论，勿据此推理）

同批次任务中曾稳定复现「凡由 Python 启动器（conan `self.run`）拉起的 Node 子进程 SIGABRT(134)」
（`python3 -c "subprocess.run(['/data/service/hnp/bin/node','--version'])"` → rc=-6，同 shell 直接执行 EXIT=0），
并导致 `conan create` 在 `build()` 阶段中止；**该现象在同一会话后续自行消失**（两个 python 均恢复正常），
无法归因到配方或上游代码，故仅记录为**环境态异常**。与之相对，**dlopen 被拒是可稳定复现的平台边界**。
