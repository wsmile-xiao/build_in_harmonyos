# postgresql-hll 2.19 适配笔记

## 编译环境
- 构建系统: PGXS (PostgreSQL Extension Building Infrastructure)
- 编译日期: 2026-06-09
- 编译器: clang/clang++ (OpenHarmony NDK)
- 状态: built

## 编译步骤

### 步骤1：编译 PostgreSQL 16.4（获取 pg_config 和 PGXS 构建基础设施）

postgresql-hll 是 PostgreSQL 扩展，其构建依赖 PostgreSQL 的 pg_config 工具和 PGXS（PostgreSQL Extension Building Infrastructure）。OHOS 平台无 PostgreSQL 预编译包，需从源码编译。

```bash
# 下载 PostgreSQL 16.4 源码
curl -kL https://github.com/postgres/postgres/archive/refs/tags/REL_16_4.tar.gz -o ~/tmp/postgresql-16.4.tar.gz
tar xzf ~/tmp/postgresql-16.4.tar.gz -C ~/tmp/

# 补丁 config.guess/config.sub 支持 ohos triplet
cd ~/tmp/postgres-REL_16_4
perl $SKILL_ROOT/scripts/patch-autotools-ohos.pl config/config.guess config/config.sub
# 手动在 kernel-os 验证列表中添加 linux-ohos* 模式（第1787行）

# 配置 PostgreSQL
export TMPDIR=$HOME/tmp/cs_tmp  # 避免 /tmp 只读问题
sed -i 's|/tmp|$TMPDIR|g' configure  # 修复硬编码 /tmp
./configure --prefix=$HOME/usr/local

# 编译 PostgreSQL（仅需要 pg_config 和 PGXS）
make -j1
# 手动安装关键文件到 ~/usr/local
mkdir -p $HOME/usr/local/bin
cp src/bin/pg_config/pg_config $HOME/usr/local/bin/
mkdir -p $HOME/usr/local/lib/postgresql/pgxs/src/makefiles
cp src/makefiles/pgxs.mk $HOME/usr/local/lib/postgresql/pgxs/src/makefiles/
cp src/Makefile.global $HOME/usr/local/lib/postgresql/pgxs/src/
cp src/Makefile.port $HOME/usr/local/lib/postgresql/pgxs/src/
cp src/Makefile.shlib $HOME/usr/local/lib/postgresql/pgxs/src/
mkdir -p $HOME/usr/local/include/postgresql/server
cp -r src/include/* $HOME/usr/local/include/postgresql/server/
# 复制 pg_config_os.h（软链接指向 linux.h）
cat src/include/port/linux.h > $HOME/usr/local/include/postgresql/server/linux.h
cd $HOME/usr/local/include/postgresql/server && rm pg_config_os.h && ln -s linux.h pg_config_os.h
```

### 步骤2：编译 postgresql-hll v2.19

```bash
cd ~/tmp/builds/postgresql-hll-2.19.work
export PATH=$HOME/usr/local/bin:$PATH
export SQLPP=clang-cpp  # 使用 clang-cpp 而不是 cpp
make USE_PGXS=1
make install DESTDIR=$TEST_PREFIX USE_PGXS=1
```

### 步骤3：打包

```bash
python3 $SKILL_ROOT/scripts/ohc-run.py package postgresql-hll 2.19
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | pg_config 不存在，cmd-pkgs 无 PostgreSQL 预编译包 | OHOS 平台没有 PostgreSQL 预编译包 | 从源码编译 PostgreSQL 16.4 获取 pg_config 和 PGXS |
| 2 | PostgreSQL configure 无法识别 ohos triplet | config.guess/config.sub 不识别 aarch64-unknown-linux-ohos | 使用 patch-autotools-ohos.pl 补丁 + 手动添加 linux-ohos* 到 kernel-os 验证列表 |
| 3 | configure 在 /tmp 创建临时文件失败 | /tmp 是只读文件系统 | 设置 TMPDIR=$HOME/tmp/cs_tmp + sed 修复 configure 中硬编码 /tmp |
| 4 | make install Permission denied | HMDFS 文件系统不支持某些操作 | 手动复制关键文件到 ~/usr/local |
| 5 | PGXS 需要 Makefile.global/port/shlib | PGXS 构建系统依赖这些文件 | 手动复制所有必要的 Makefile 文件 |
| 6 | 缺少 pg_config_os.h | PostgreSQL 源码中是软链接 | 复制 linux.h 并创建 pg_config_os.h -> linux.h 软链接 |
| 7 | cpp 命令不存在 | 系统没有 GNU cpp | 设置 SQLPP=clang-cpp 使用 clang 预处理器 |

## 源码修改

postgresql-hll 源码无修改。PostgreSQL 源码修改（仅用于获取构建依赖）：
- config.guess/config.sub: 补丁支持 ohos triplet
- configure: 替换硬编码 /tmp 为 $TMPDIR
- 这些修改不在 postgresql-hll 的补丁中，因为它们是 PostgreSQL 的构建依赖修复

## 依赖版本

- PostgreSQL 16.4（构建依赖，从源码编译）
- clang (OpenHarmony NDK 系统编译器)
- libc.so（运行时依赖，系统库）

## 验证结果

### 回归测试（make check）

⚠️ **跳过**：postgresql-hll 是 PostgreSQL 扩展，需要运行中的 PostgreSQL 服务器才能执行回归测试。

**替代验证**：手动验证安装产物的完整性。

### Staging 验证（手动）

```bash
# hll.so ELF 验证
llvm-readelf -h hll.so
# Machine: AArch64, Type: DYN (Shared object file), Class: ELF64 ✅

# OHOS 签名验证
llvm-readelf -n hll.so
# Owner: OHOS, NT_VERSION (version) - ✅ 已签名

# 动态依赖验证
llvm-readelf -d hll.so | grep NEEDED
# NEEDED: libc.so 仅依赖系统库 ✅

# 导出符号验证
llvm-nm -D hll.so | grep -E "hll_|_PG_"
# hll_empty, hll_add, hll_cardinality, _PG_init 等关键符号 ✅

# 安装产物完整性
ls ~/usr/local/lib/postgresql/hll.so ✅
ls ~/usr/local/share/postgresql/extension/hll.control ✅
ls ~/usr/local/share/postgresql/extension/hll*.sql | wc -l
# 10 个 SQL 脚本 ✅
```

### 质量门禁 G1-G4: PASS
python3 ohc-run.py verify-build postgresql-hll 2.19
# 质量报告: PASS ✅

详细测试报告见：reports/test-report.md

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| postgresql-hll-2.19-ohos-aarch64.tar.gz | 100KB | 预编译包（含 .so + 10个SQL脚本 + 控制文件） |

## 注意事项

- postgresql-hll 使用 PGXS 构建系统（不是标准 autotools/cmake），使用 `make USE_PGXS=1` 编译
- 需要先编译 PostgreSQL 获取 pg_config 和 PGXS 构建基础设施
- 使用 clang-cpp 而不是 cpp 处理 SQL 文件中的预处理器指令
- 回归测试需要运行中的 PostgreSQL 服务器（跳过，需在部署环境中补测）
- PostgreSQL hardlink 权限问题在 HMDFS 文件系统上常见（影响 make install）

---

**编译结束**: 2026-06-09 01:38
**最终状态**: built
---

**编译结束**: 2026-06-09 01:38
**最终状态**: built
