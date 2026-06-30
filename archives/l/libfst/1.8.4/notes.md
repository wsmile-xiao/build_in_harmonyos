# libfst 1.8.4 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-05
- 编译器: clang/clang++
- 状态: published ✅

## 编译步骤

```bash
# 1. 解压源码
tar xzf libfst-1.8.4.tar.gz

# 2. 应用补丁
# - 0001-config.guess.patch: OpenHarmony 平台识别
# - 0002-config.sub.patch: OpenHarmony 三元组验证
# - 0003-configure-umask.patch: HMDFS 权限修复

# 3. configure（需要显式指定 C++ 编译器）
export CC=clang CXX=clang++
./configure --prefix=$HOME/usr/local

# 4. 编译
make -j2

# 5. 安装（DESTDIR 模式）
make install DESTDIR=$TEST_PREFIX
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure: C++ compiler cannot create executables | E053: 需要显式指定 clang++ | export CC=clang CXX=clang++ |
| 2 | config.status: Permission denied (subs1.awk) | E011: HMDFS umask 077 导致临时目录不可写 | sed -i 's/umask 077/umask 022/g' configure |
| 3 | config.guess/config.sub 不存在 | 清理源码时误删 | 从 automake-1.16 复制 |

## 源码修改

- **config.guess**: 使用 automake-1.16 版本（支持 OpenHarmony）
- **config.sub**: 使用 automake-1.16 版本（支持 OpenHarmony）
- **configure**: umask 077 → 022

## 依赖版本

无外部依赖

## 功能测试结果

**测试日期**: 2026-06-05
**测试状态**: ✅ 全部通过

### 测试摘要

| 类别 | 测试数 | 通过 | 失败 |
|------|--------|------|------|
| 基础功能 | 4 | 4 | 0 |
| 组合操作 | 3 | 3 | 0 |
| 优化操作 | 4 | 4 | 0 |
| 变换操作 | 4 | 4 | 0 |
| 查询操作 | 4 | 4 | 0 |
| 工具可用性 | 37 | 37 | 0 |

### 性能测试

| 测试 | 时间 |
|------|------|
| 100状态 FST 编译 | 0.041s |
| 最短路径计算 | 0.032s |

详细测试报告见: `reports/test-report.md`

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libfst-1.8.4-ohos-aarch64.tar.gz | 93.6MB | 预编译包 |
| libfst-1.8.4-ohos-aarch64-debug.tar.gz | 17.5MB | 调试符号包 |

## 使用示例

```bash
# 编译文本 FST
fstcompile input.txt input.fst

# 打印 FST 内容
fstprint input.fst

# 查看信息
fstinfo input.fst

# 生成 DOT 图形
fstdraw input.fst input.dot

# 组合操作
fstunion a.fst b.fst union.fst
fstconcat a.fst b.fst concat.fst

# 优化操作
fstdeterminize input.fst det.fst
fstminimize det.fst min.fst
```

## 注意事项

- ⚠️ **必须使用 `CC=clang CXX=clang++` 进行 configure**（E053）
- ⚠️ **configure 中的 umask 必须修改为 022**（E011）
- ✅ 所有 37 个 fst* 工具功能正常
- ✅ 性能表现良好，可用于生产环境