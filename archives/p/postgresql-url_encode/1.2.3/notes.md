# postgresql-url_encode 1.2.3 编译笔记

## 编译状态
**状态**: published ✅

## 编译日期
2026-06-04

## 背景
编译 PostgreSQL URL Encode 扩展，为 PostgreSQL 提供 URL 编码和解码功能。

## 软件信息
- 名称: postgresql-url_encode
- 版本: 1.2.3
- 状态: published
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

添加 varatt.h 头文件以解决 PostgreSQL 17 编译问题：

```diff
--- a/src/url_encode.c
+++ b/src/url_encode.c
@@ -1,6 +1,7 @@
 #include "postgres.h"
 #include "fmgr.h"
+#include "varatt.h"
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

---

**编译结束**: 2026-06-04
**最终状态**: published - postgresql-url_encode 1.2.3 已成功编译和归档