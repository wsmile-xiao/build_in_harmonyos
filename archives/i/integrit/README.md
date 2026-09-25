# integrit

**integrit** 是一个文件完整性校验系统：它把文件树的校验和存进 CDB 数据库，之后每次运行都可以报告哪些文件被**改动**、**新增**或**删除**，常用于系统被入侵后的取证与日常防篡改巡检。

## 功能概述

- **基线生成**：`integrit -C <conf> -u` 扫描配置里的根目录，生成当前状态数据库
- **完整性检查**：`integrit -C <conf> -c` 把当前状态与已知数据库比对，输出 `changed:` / `new:` / `missing:` 三类报告行
- **三态退出码**：`0` = 无变化，`1` = 检出变化，`2` = 运行失败（供脚本化调用判断）
- **报告格式**：人类可读文本，或 `-x` 输出 XML（仓库自带 `integrit.xsd` schema）
- **数据库格式**：CDB（constant database），配合自带的 `i-viewdb` / `i-ls` 工具可查看

## OHOS 适配要点

纯 C、**零外部依赖**（RMD160 摘要、CDB、哈希表全部内置于源码树），构建面干净，适配集中在打包阶段：

| # | 要点 | 处置 |
|---|---|---|
| 1 | **安装后的可执行文件 `Operation not permitted`** | 上游 `install` 规则是 `$(INSTALL) $(STRIP) -m 755 …`；hnp clang 写入的 `.codesign` 签名随 strip 后布局失配，加载器校验失败。`package()` 改为 `copy` 直接收 **make 原始产物**（不走 `make install` ⇒ 根本不经过 `$(STRIP)`，`.codesign` 保持有效；实测 67968B、`-V` rc=0）。若某包必须走 install，则在 install 调用上传 `STRIP=`（make 命令行变量优先级最高） |
| 2 | **Conan autotools 走 `--prefix=/` + `DESTDIR`** | 目录参数必须是根起绝对路径：`--sbindir=/bin` 才会落到 `<DESTDIR>/bin`。从 `self.folders.package` 推导会得到相对值 `bin`，configure 报 `expected an absolute directory name` |
| 3 | **上游装 `sbin/` 而门禁只认 `bin/`** | autoconf 默认 `sbindir=${prefix}/sbin`；用 `--sbindir=/bin` 归位到 Conan 标准 `bin/`，与 `package_info().bindirs`、CI L5/G4 对齐 |
| 4 | **`config.status` 假绿** | autoconf 2.59 生成物用 `umask 077 && mktemp -d ./confstatXXXXXX` 建临时目录，HMDFS 落盘 2700 后写不进去 —— `configure` 返回 0 但 `config.h` 未生成。对**生成物** `configure`/`hashtbl/configure`/`config.status` 做 `umask 022` + `mkdir -p` 归一（E011/E114 同族，不进 git） |
| 5 | **上游测试对权限位敏感** | `test/test` 是 fail-fast shell 驱动器，自建 4×4 文件树、**31 条断言**；其中依赖 `chmod 000` 的一条在 HMDFS 上必然失败（权限位不生效）⇒ 31 = 30 PASS + 1 FAIL，按平台限制归因，不改上游断言 |

与 Linux 的差异集中在**权限位语义**（`chmod` 只加不减、`umask 000` 新建文件仍是 `-rw-rw----`）与 **ELF 签名**（strip 破坏 `.codesign`），其余为标准 POSIX autotools 流程。

## 依赖关系

- **编译依赖**：无（`requirements()` 为空；`readelf -d` 的 `NEEDED` 仅 `libc.so`）
- **可选依赖**：`libgc`（Boehm GC）只在 `./configure --with-leakfind=DIR`（开发者查泄漏开关）下才会被探测，且相关 `#include` 全部在 `#ifdef ELC_FIND_LEAKS` 内 —— 本适配不启用该开关
- **运行依赖**：无
- **工具链**：clang / make（autotools）

## 参考资料

- 上游仓库：https://github.com/integrit/integrit
- 发行渠道：https://sourceforge.net/projects/integrit/
- 发行版打包记录：https://deb.debian.org/debian/pool/main/i/integrit/
- 本仓库适配：`archives/i/integrit/4.1/`（版本级细节见该目录 `notes.md`）
