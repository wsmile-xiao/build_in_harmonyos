# DRAFT-postgresql-18.3-install-shim-separate-args

> 草稿知识项 — OHOS 本机 install shim 分离参数不兼容与 use_install_sh 规避
> 来源：postgresql 18.3 Conan 配方化（feat/postgresql-18.3，2026-09-03）
> 同 stem 配对：`knowledge/drafts/DRAFT-postgresql-18.3-install-shim-separate-args.kv`

## 问题（现象 / error_signature）

- `make install`（conan create 的 package 阶段）在安装第一个目标时中断，报
  `cp: bad '755': No such file or directory`，随后 `Error 1`。
- 失败行来自 INSTALL 类规则（`install -c -m 755 src dst` 分离参数形式）。
- 仅在 OHOS PC 本机 / CI profile（buildenv PATH 前置 `$HOME/usr/local/bin`）出现；
  标准 Linux 发行版构建无此问题。

## 根因（root_cause）

1. OHOS PC 工具环境的 `$HOME/usr/local/bin` 内有一个 install 包装脚本（shim），
   它只识别合并参数语义，把 `-m` 的值（如 `755`）当作源文件传给底层 `cp`。
2. autotools 生成的安装规则标准写法是分离参数形式 `install -c -m 755 src dst`，
   与该 shim 不兼容。
3. 构建机 PATH 前置 `$HOME/usr/local/bin`（本机与 CI profile 一致），`make install`
   解析到的 `install` 即该 shim。

## 可复用方案（rec_approach: switch-to-bundled-install-sh）

1. **优先使用软件自带的安装器开关**：PostgreSQL 原生支持
   `make install use_install_sh=yes`，切换到自带 `config/install-sh`
   （正确处理分离参数与所有安装模式）。Conan 配方写法：
   ```python
   autotools.install(args=["use_install_sh=yes"])
   ```
2. **无原生开关的 autotools 项目**：在 `generate()` 中用 Environment 将
   `INSTALL` 指向源码树自带的 `install-sh`，或 recipe 的 `package()`
   手动 `copy()` 产物。
3. **禁止修改 shim 本身**——它属于整机工具链，改动影响面不可控。

## 适用条件

- OHOS PC 上以 autotools 打包、安装规则使用分离参数形式的软件；
- 本机/CI 的 buildenv PATH 前置 `$HOME/usr/local/bin` 的所有环境。

## 反例（不适用场景）

- CMake 项目（install 由 cmake -P 脚本完成，不经过 PATH 上的 install）；
- 纯手工 copy 产物的 recipe（不执行 make install）。

## 验证证据（真实命令 + 结果）

- 复现：`which install` → `$HOME/usr/local/bin/install`；
  `install -c -m 755 <src> <dst>` → `cp: bad '755': No such file or directory`。
- 修复后：`make install use_install_sh=yes`（DESTDIR 打包）全量成功，
  `bin/` 35 个可执行 + `lib/` 21 个库文件齐全，`stat -c %a bin/postgres` = 755。
- W3 本地 CI 全绿（Build Summary 100%），conan-verify G2 PASS。

## 限制与恢复条件

- `use_install_sh=yes` 是 PostgreSQL 构建系统特有开关，其他软件需寻找等价物
  （automake 的 `INSTALL` 变量、INSTALL_SCRIPT 等）；
- 若未来 OHOS 工具链修复该 shim（支持分离参数），此规避仍是无害的显式化选择，
  无需回退。
