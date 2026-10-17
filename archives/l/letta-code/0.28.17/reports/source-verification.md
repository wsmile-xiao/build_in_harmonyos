# letta-code 0.28.17 — 源码校验信息

## 上游信息

| 项目 | 值 |
|------|-----|
| 软件 | letta-code（npm 包 `@letta-ai/letta-code`，有状态 AI 编码代理 CLI） |
| 版本 | 0.28.17 |
| 上游仓库 | https://github.com/letta-ai/letta-code |
| 上游 tag | `v0.28.17` |
| 上游 commit | `c9a66725b0cdc8386d2496cb373f08ca642feda0` |
| 形态 | npm 预构建 Node.js CLI（上游用 **bun** 打包为单文件 `letta.js`，无本地编译步骤） |
| 运行时前置 | 系统 Node.js `>= 22.19.0`（引擎约束 `engines`） |
| 许可证 | **Apache-2.0** |

## 发布物与校验和

本配方需要**两个** npm 发布物：主包 `letta-code`，以及未打平的静态 bare import 依赖 `ws`。

| 名称 | 版本 | 下载 URL | SHA256 | npm shasum（SHA1） |
|------|------|----------|--------|--------------------|
| letta-code | 0.28.17 | `https://registry.npmjs.org/@letta-ai/letta-code/-/letta-code-0.28.17.tgz` | `10deb90f108b766d20c0743878219a23a09e7bd409d1621e80df4c6e6088f0a3` | `b6f925f68264df2972861442333f2996a75df638` |
| ws | 8.19.0 | `https://registry.npmjs.org/ws/-/ws-8.19.0.tgz` | `7fb02dae000a91ccd9d2ae51cda3672ab6c1685ecd26e07c668996ce52e25609` | `ddc2bdfa5b9ad860204f5a72a4863a8895fd8c8b` |

> SHA256 与 `conandata.yml`、`manifest.yaml` 三处一致；
> 适配期不得改动既有实测哈希与提交号。

## npmjs 官方 metadata 交叉核对

以官方 registry 的版本元数据独立核对发布物身份（`dist.tarball` / `dist.shasum` / `dist.integrity`）：

| 名称 | `dist.tarball` | `dist.shasum`（SHA1） | `dist.integrity`（sha512） | `license` |
|------|----------------|-----------------------|----------------------------|-----------|
| `@letta-ai/letta-code@0.28.17` | `https://registry.npmjs.org/@letta-ai/letta-code/-/letta-code-0.28.17.tgz` | `b6f925f68264df2972861442333f2996a75df638` | `sha512-MizklVWWv9eGv/pTxO1PruFaeyRwnaBFHZRtQDxbe6MRIpBThKcRaEPxMhbu0NyvpIjYr5qSeK7du2xkVRs+WA==` | Apache-2.0 |
| `ws@8.19.0` | `https://registry.npmjs.org/ws/-/ws-8.19.0.tgz` | `ddc2bdfa5b9ad860204f5a72a4863a8895fd8c8b` | `sha512-blAT2mjOEIi0ZzruJfIhb3nps74PRWTCz1IjglWEEpQl5XS/UNama6u2/rjFkDDouqr4L67ry+1aGIALViWjDg==` | MIT |

交叉结论：两处独立来源（本地下载的 SHA256 计算 + registry 官方 metadata 的 tarball 指向与 SHA1/sha512 integrity）
指向同一发布物，未发现镜像/重打包迹象。

## 校验命令与实测结果

```sh
# 主包 SHA256（实测 = 10deb90f108b766d20c0743878219a23a09e7bd409d1621e80df4c6e6088f0a3）
curl -fsSL --retry 5 --retry-all-errors \
  https://registry.npmjs.org/@letta-ai/letta-code/-/letta-code-0.28.17.tgz | sha256sum

# vendor ws SHA256（实测 = 7fb02dae000a91ccd9d2ae51cda3672ab6c1685ecd26e07c668996ce52e25609）
curl -fsSL https://registry.npmjs.org/ws/-/ws-8.19.0.tgz | sha256sum

# npmjs 官方 metadata（核对 tarball / shasum / integrity / license）
curl -fsSL https://registry.npmjs.org/@letta-ai/letta-code/0.28.17
curl -fsSL https://registry.npmjs.org/ws/8.19.0

# 上游 tag → commit（实测 commit = c9a66725b0cdc8386d2496cb373f08ca642feda0）
curl -fsSL https://api.github.com/repos/letta-ai/letta-code/commits/v0.28.17
```

实测结果：

| 校验项 | 实测值 | 判定 |
|--------|--------|------|
| 主包 tarball SHA256 | `10deb90f108b766d20c0743878219a23a09e7bd409d1621e80df4c6e6088f0a3` | ✅ 与 conandata.yml / manifest.yaml 一致 |
| vendor ws tarball SHA256 | `7fb02dae000a91ccd9d2ae51cda3672ab6c1685ecd26e07c668996ce52e25609` | ✅ 一致 |
| 主包 registry `dist.shasum` | `b6f925f68264df2972861442333f2996a75df638` | ✅ 与官方 metadata 一致 |
| vendor ws registry `dist.shasum` | `ddc2bdfa5b9ad860204f5a72a4863a8895fd8c8b` | ✅ 一致 |
| 上游 tag `v0.28.17` | `refs/tags/v0.28.17` → commit `c9a66725b0cdc8386d2496cb373f08ca642feda0` | ✅ 与 manifest/README 一致 |

> 备注：主包 tarball 体积较大，首次无重试下载被 registry 断开（`Recv failure: Connection reset by peer`），
> 加 `--retry 5 --retry-all-errors` 后下载完整并得到上述稳定 SHA256。

## 许可证

| 项目 | 值 |
|------|-----|
| 主包 license | **Apache-2.0**（npm metadata `license=Apache-2.0`；发布物内含 `LICENSE`，随包安装到 `licenses/`） |
| vendor ws license | MIT（`ws@8.19.0` npm metadata `license=MIT`；仅作为未打平 bare import 的运行时而随包 vendoring，非本配方主体） |

## 本机构建与运行验证（启动缺陷修复）

本配方对本机的 node 启动缺陷做了两处修复，均已用 `conan create` 实测（本机 OHOS musl aarch64，node v24.13.0）：

- **真剥离 `LD_LIBRARY_PATH`**：launcher 的 `unset LD_LIBRARY_PATH` 在 `/system/bin/sh` 下并未把变量从交给
  子进程的环境里摘掉（`unset` 后跑真实 JS 仍崩），`LD_LIBRARY_PATH=` 置空同样致命；只有 `env -u` 才是真剥离。
  launcher 现在解析一个支持 `-u` 的 `env`，解析不到或不支持 `-u` 时**显式失败**，绝不静默继承污染值。
- **启动 trampoline `bin/letta-exec`**：仅真剥离并不能让 node 启动——V8 的 CodeRange 虚拟内存预留会失败，
  以非 `ENOMEM` 的 errno 命中 `Check failed: 12 == (*__errno_location())`（Signal 5 / exit 133）。
  node 直连系统 shell 稳定触发；先经一个装在用户文件系统上的可执行文件再 exec node 即正常。trampoline 即
  这一次重执行（并 `unsetenv("LD_LIBRARY_PATH")` 兜底）。JIT 保持开启（`--jitless` 会使 yoga-layout 的 WASM 失效）。

验证结论（本机 `conan create`，退出码 0）：

| 项目 | 结果 |
|------|------|
| source() 双 tarball 下载 + SHA256 校验 | ✅ pass（哈希见上表，未改动） |
| trampoline 编译（目标 clang，优先 `-static`） | ✅ pass |
| `build()` **真实 launcher** 冒烟（继承污染 `LD_LIBRARY_PATH`、多一层 `/bin/sh -c`、正常 JIT） | ✅ pass（`--version` 精确 `0.28.17 (Letta Code)`；`--help` 含 `USAGE`/`headless`） |
| `package()`（不含任何构建缓存：无 build 目录 / `letta-exec.c` / `conaninfo.txt` / `conan*.sh`） | ✅ pass |
| `test_package`（`test.sh` **53 条断言**：1 版本横幅 + 3 帮助段头 + 21 条 USAGE 命令行 + 27 条 SUBCOMMANDS 条目 + 1 断言数自检） | ✅ pass（`letta-code 0.28.17 consumer checks: PASS (assertions=53)`） |
| 反向验证：旧 `unset` launcher / 仅 `env -u`（无 trampoline） | ✅ 如预期在 `build()` 冒烟阶段失败（Exit 133 / Signal 5），证明新冒烟可拦回归 |

## 相关文件

- 配方与数据源：`archives/l/letta-code/0.28.17/conanfile.py`、`archives/l/letta-code/0.28.17/conandata.yml`
- 适配笔记：`archives/l/letta-code/0.28.17/notes.md`
- 元数据：`archives/l/letta-code/0.28.17/manifest.yaml`
