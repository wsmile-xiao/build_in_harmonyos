# Pazpar2

Pazpar2 是 Index Data 的元搜索（metasearch）引擎，纯 C 实现，autoconf/automake 构建（无 libtool）。它并发检索多个目标（Z39.50、SRU/SRW、Solr 等），合并去重结果集，并通过 HTTP 协议 `/search.pz2` 对外提供有状态的检索会话（`init` / `search` / `show` / `record` / `termlist` / `bytarget` / `stat` / `ping` 等）。记录归一化由 libxslt 完成，Z39.50/SRU 协议栈由 YAZ 提供。

- `pazpar2`：守护进程（上游装在 `sbin/`，本归档归集到 `bin/`）
- `pazpar2_play`：上游附带的命令行播放/调试工具

## 版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 1.14.1 | built | HarmonyOS PC（aarch64-linux-ohos）适配，yaz/5.37.3 + libxslt/1.1.45.2 + libxml2/2.15.3 |

## 依赖

- yaz/5.37.3（硬依赖，Z39.50/SRU 协议栈；ohpcd 制品仓已发布，构建时 `--with-xslt=no`、`--with-icu=no`）
- libxslt/1.1.45.2（硬依赖，记录归一化；源码直接 `#include <libxslt/*.h>`）
- libxml2/2.15.3（硬依赖，XML 解析；制品仓为共享库 `libxml2.so.16`）

## 关键适配点

- 源码补丁 3 个：config.guess/config.sub 的 HarmonyOS 识别、configure 的 HMDFS umask、YAZ 的 XSLT 硬检查降级为警告
- `--with-yaz=<yaz package_folder>/bin`（yaz 包不导出 bin/ 到 PATH）
- `extra_ldflags` 注入 `-Wl,-rpath,<dep>/lib`（libxml2 为共享库，configure conftest 需可运行）
- 详见 `1.14.1/notes.md` 与 `1.14.1/manifest.yaml`

## 已知限制

- ICU 不可用（制品仓 yaz 为 `--with-icu=no`，`pazpar2 -V` 显示 `icu:disabled`），6 个 `--icu` 上游用例自动跳过
- 上游 `make install` 不安装 `etc/`（服务/设置模板）与 `etc/xsl/*.xsl`（归一化样式表），部署需自备

上游：https://github.com/indexdata/pazpar2
