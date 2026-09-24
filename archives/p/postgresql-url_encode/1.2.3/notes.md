# postgresql-url_encode 1.2.3 编译笔记

## 编译状态
**状态**: built ✅（2026-06-04 手工构建时代为 published；2026-09-17 Conan 重适配后当前状态为 built，权威状态以 manifest.yaml 为准）

## 编译日期
2026-06-04（手工构建） / 2026-09-17（Conan 配方化）

## 背景
编译 PostgreSQL URL Encode 扩展，为 PostgreSQL 提供 URL 编码和解码功能。

## 软件信息
- 名称: postgresql-url_encode
- 版本: 1.2.3
- 状态: built（Conan 配方化）
- 构建系统: PGXS
- PGXN: https://api.pgxn.org/dist/url_encode/

## 编译过程

### 1. 下载源码
从 PGXN 下载 url_encode-1.2.3 源码包。

### 2. PostgreSQL 17 API 变更问题
在 PostgreSQL 17 中，某些内部头文件结构发生了变化，需要显式包含 varatt.h。

**错误表现**:
编译时出现 varlena 相关函数未定义的错误。

**解决方案**:
在 src/url_encode.c 中添加 `#include "varatt.h"` 头文件。

### 3. 编译步骤

使用 PGXS 构建系统：

```bash
# 设置 PostgreSQL 路径
export PATH=/path/to/postgresql/bin:$PATH

# 编译
make USE_PGXS=1
make USE_PGXS=1 install
```

### 4. 安装验证

```sql
-- 创建扩展
CREATE EXTENSION url_encode;

-- 测试功能
SELECT url_encode('Hello World!');
SELECT url_decode('Hello%20World%21');
```

## OHOS 适配要点

### PostgreSQL 17 API 变更
- **问题**: PostgreSQL 17 重构了 varlena 相关头文件
- **表现**: 编译时缺少 varlena 函数定义
- **解决**: 添加 `#include "varatt.h"` 头文件
- **补丁**: 0001-src-url_encode.c.patch

### 关键知识
PostgreSQL 17 内部 API 变更可能导致扩展编译失败，需要检查：
1. 是否需要显式包含新的头文件
2. 是否有 API 函数签名变化
3. 是否需要调整扩展代码以适应新版本

## 补丁文件

### 0001-src-url_encode.c.patch

添加 varatt.h 头文件以解决 PostgreSQL 17+ 编译问题（实际补丁内容，以 patches/ 文件为准）：

```diff
--- a/src/url_encode.c
+++ b/src/url_encode.c
@@ -15,6 +15,7 @@
 #include "postgres.h"

 #include "fmgr.h"
+#include "varatt.h"
 #include "mb/pg_wchar.h"
 #include "utils/builtins.h"
```

## 最终结果

- ✅ 编译成功
- ✅ 安装成功
- ✅ 功能验证成功
- ✅ 归档已创建

## 参考

- PGXN: https://api.pgxn.org/dist/url_encode/
- PostgreSQL 17 Release Notes: https://www.postgresql.org/docs/17/release-17.html
## Conan Adaptation (2026-09-17, v3)

### 历史演进
- 2026-08-08~08-27（第 1-2 次尝试）：build() 内下载并编译整个 PostgreSQL 18.1 源码树以获取
  server 头文件（configure + fmgr-stamp + errcodes.h/nodetags.h 生成），CI 上因
  api.pgxn.org/ftp.postgresql.org 不可达、构建超时（3894s）反复失败；期间曾引入
  ghfast.top/gh-proxy.com 镜像前缀（违反 R39）与 packaging/ 源码包 tarball（违反 JC3，
  且二进制 diff 无 payload 导致 CI checkout-pr `git apply` 永久失败）。
- 2026-09-17（本次）：改用制品仓已有的 postgresql/18.3 conan 包作为依赖，彻底删除
  PG 源码构建路径。

### 方案（当前）
1. `requirements()` 声明 `postgresql/18.3` —— server 头文件、PGXS makefile、可重定位的
   pg_config 全部来自该包，build() 不再下载/编译 PostgreSQL。
2. build() 用上游 Makefile 走标准 PGXS：`make USE_PGXS=1 PG_CONFIG=<dep>/bin/pg_config`。
   PGXS 在 make 时通过 pg_config 解析全部路径；pg_config（PG 18）经 /proc/self/exe
   重定位，conan 缓存位置任意。
3. 补丁走 conandata.yml 声明 + apply_conandata_patches（修复此前 toybox patch 对
   畸形 hunk 静默不生效的问题，补丁已按真实源码上下文重新生成）。
4. 源码 URL 用 github.com archive（conandata sha256 已与该 URL 重新对齐；
   api.pgxn.org 与 api.github.com tarball 均为 CI 不可达或无镜像回退，R39：镜像由
   CI 自动注入，配方内禁止手写）。
5. package 布局：`lib/url_encode.so`（保留 PG 模块名，module_pathname=$libdir/url_encode）
   + `share/extension/url_encode.control` + `share/extension/url_encode--1.2.sql`。
6. test_package 为真功能测试：initdb 一个 PostgreSQL 18.3 集群 → 安装包内扩展文件 →
   pg_ctl 起服务（非默认端口）→ CREATE EXTENSION → 逐条执行上游 test/sql/url_encode.sql
   的 5 条语句并断言 test/expected/url_encode.out 的精确输出（含 5 行 unnest 结果与
   md5 摘要）。此前 dlopen 方案因扩展 .so 含未定义 server 符号（pg_detoast_datum 等）
  必然失败，ELF 符号解析方案又无法验证功能（R34），真机起服务是唯一可信验证方式。

### 验证（2026-09-17，本机 OHOS PC aarch64）
- conan create（ohos-aarch64 profile）通过
- 功能测试 6/6 断言通过：CREATE EXTENSION + 上游 5 条 SQL 语句全部输出精确匹配

### 平台要点
- OHOS /tmp 只读：测试脚本使用 $TMPDIR 或 ~/tmp
- PostgreSQL 18.3 服务端（initdb/pg_ctl/postgres）在 OHOS PC 原生可用，
  自编译扩展 .so 可正常 LOAD（无 ELF 签名阻断）
---

**编译结束**: 2026-09-17 15:43
**最终状态**: built
