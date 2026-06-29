# 旧归档软件迁移指南 (MIGRATION_GUIDE)

本文档覆盖将旧版本/归档软件迁移到 OHOS 平台时的特殊问题。
对于全新库的适配，请先阅读 [ADAPTATION_GUIDE.md](ADAPTATION_GUIDE.md)。

## 1. 适用场景

- 已有旧版本的 conan 配方需要升级到新版本
- 上游已归档/停止维护的软件需要适配
- 从其他平台 (Linux/Android) 移植到 OHOS
- 依赖版本冲突需要解决

## 2. 版本升级流程

```
旧版本: archives/z/zlib/1.2.13/
新版本: archives/z/zlib/1.3.1/
```

### Step 1: 复制旧配方

```bash
cp -r archives/z/zlib/1.2.13/ archives/z/zlib/1.3.1/
```

### Step 2: 更新版本号和源码地址

```yaml
# conandata.yml
sources:
  - url: "https://zlib.net/zlib-1.3.1.tar.gz"   # ← 改为新版本 URL
    sha256: "<新版本的 SHA256>"                    # ← 必须重新计算
```

```python
# conanfile.py
version = "1.3.1"  # ← 更新版本号
```

### Step 3: 检查补丁兼容性

旧版本的补丁**可能不适用于新版本**:

```bash
cd archives/z/zlib/1.3.1/
# 尝试应用补丁, 观察是否冲突
patch -p1 --dry-run < patches/0001-fix-ohos-compat.patch
```

如果冲突:
1. 手动重新适配补丁
2. 更新 `conandata.yml` 中的 patch 描述

### Step 4: 重新提取上游测试

新版本可能新增了测试用例:

```bash
bash ci/tools/extract_upstream_tests.sh zlib-1.3.1.tar.gz
```

更新 `test_package/MANIFEST.yml`。

### Step 5: 验证

```bash
conan create . --user=ohpcd --channel=stable -pr:h=$HOME/.conan2/profiles/ohos --build=missing
```

## 3. 已归档软件适配

上游已停止维护的软件 (如老旧的工具库) 迁移到 OHOS 时的注意事项:

### 3.1 源码获取

| 情况 | 方案 |
|------|------|
| 官方下载仍可用 | 正常使用 |
| 官方下载已失效 | 使用 archive.org / GitHub mirror / fossies.org 归档 |
| 只有 SVN/CVS 仓库 | 导出为 tar.gz, 计算固定 SHA256 |

在 `conandata.yml` 中注明来源:

```yaml
sources:
  - url: "https://web.archive.org/web/2020/.../package-1.0.tar.gz"
    sha256: "abc123..."
    # NOTE: 原始站点已下线, 使用 web.archive.org 归档
```

### 3.2 废弃 API 替换

旧软件可能使用了 OHOS/bionic 不支持的 API:

| 废弃/缺失的 API | OHOS 替代方案 |
|----------------|--------------|
| `getpwnam()` / `getpwuid()` | OHOS 有简化版实现, 部分字段为空 |
| `sys/auxv.h` / `getauxval()` | OHOS 不提供, 需要条件编译绕过 |
| `backtrace()` / `backtrace_symbols()` | OHOS 不提供, 用 `#ifdef __OHOS__` 跳过 |
| `fts_open()` / `fts_read()` | OHOS 不提供, 用 `opendir()`/`readdir()` 替代 |
| `wordexp()` / `wordfree()` | OHOS 不提供, 需要补丁移除调用或简化 |
| `gettext()` / 国际化库 | OHOS 不提供 libintl, 用桩函数替代 |

补丁示例:

```c
// patches/0001-fix-ohos-missing-api.patch
+#ifdef __OHOS__
+/* OHOS bionic 不提供 backtrace */
+static int backtrace(void **buffer, int size) { return 0; }
+static char **backtrace_symbols(void *const *buffer, int size) { return NULL; }
+#else
 #include <execinfo.h>
+#endif
```

### 3.3 已知 OHOS 不兼容项

以下功能在 OHOS 上**确定不可用**，适配时必须处理:

| 不兼容项 | 说明 | 处理方式 |
|---------|------|---------|
| `/proc/self/maps` 格式差异 | OHOS 的 maps 格式与 Linux 不同 | 解析代码需要适配 |
| `ptrace()` 限制 | OHOS 安全策略限制 ptrace | 调试相关功能需条件编译跳过 |
| `LD_PRELOAD` 行为差异 | OHOS 动态链接器行为不同 | 避免 preload 方案 |
| System V IPC (`shmget` 等) | OHOS 可能不支持 | 使用 POSIX shm 替代 |
| `futex()` 系统调用号不同 | 直接调用 futex 的代码会失败 | 使用 pthread 封装 |

## 4. 依赖版本冲突

### 4.1 场景

```
包 A 依赖 openssl/1.1.1
包 B 依赖 openssl/3.0.0
→ Conan 的 DAG 解析会冲突
```

### 4.2 解决策略

**优先策略**: 统一到高版本

```
1. 检查包 A 是否兼容 openssl/3.0.0
   - 多数情况下向后兼容
   - 修改 A 的 conanfile.py: self.requires("openssl/3.0.0")
2. 如果 A 确实不兼容 3.0.0
   - 考虑升级 A 到新版本
   - 或使用 Conan 的 override 机制 (最后手段)
```

**override 机制** (最后手段):

```python
# 顶层调用时
conan install . --requires=packageA/1.0 --requires=packageB/2.0 \
  --build=* -c tools.system:enable_mode=latest
```

### 4.3 版本选择原则

| 原则 | 说明 |
|------|------|
| 优先用上游最新稳定版 | 新版本通常修复了移植问题 |
| 同一个大版本内就高不就低 | 如 openssl 3.0.x 系列用最新 |
| 避免使用 EOL 版本 | 除非有硬性兼容要求 |

## 5. 迁移记录模板

每个迁移的包建议在 conandata.yml 中保留迁移记录:

```yaml
sources:
  - url: "https://example.com/package-1.0.tar.gz"
    sha256: "abc123..."

# OHOS 迁移记录
migration:
  from_version: "0.9.5"           # 原平台版本
  to_version: "1.0"               # OHOS 版本
  patches_applied:
    - "0001-fix-ohos-bionic.patch"    # bionic API 差异
    - "0002-skip-broken-tests.patch"  # 跳过 OHOS 不支持的测试
  known_limitations:
    - "backtrace 功能不可用 (OHOS 限制)"
  migration_date: "2026-06-29"
```

## 6. 参考

- [AI 适配操作手册](ADAPTATION_GUIDE.md) — 新库适配的完整流程
- [测试质量规范](TEST_QUALITY_SPEC.md) — CI 门禁要求
- `ci/tools/extract_upstream_tests.sh` — 上游测试分析工具
