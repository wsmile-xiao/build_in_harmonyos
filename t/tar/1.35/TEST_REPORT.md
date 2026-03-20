# GNU tar 1.35 测试报告

> **项目**: GNU tar  
> **测试日期**: 2026-03-18  
> **测试环境**: HarmonyOS HongMeng Kernel 1.11.0 aarch64  
> **测试类型**: 官方测试套件

---

## 一、测试摘要

| 指标 | 数值 | 百分比 |
|:----:|:----:|:------:|
| 总测试数 | 211 | 100% |
| 通过 (PASS) | 82 | 38.9% |
| 失败 (FAIL) | 98 | 46.4% |
| 跳过 (SKIP) | 31 | 14.7% |

**有效测试通过率**: 45.6% (82/180)

---

## 二、测试结论

### 2.1 总体评价

⚠️ **部分功能受限** - 核心归档/解压功能可用，但存在系统兼容性问题

### 2.2 主要问题

| 问题类别 | 影响范围 | 严重程度 |
|----------|----------|----------|
| UID 范围超限 | v7 格式归档 | 🟡 中 |
| stdin 操作受限 | 管道输入 | 🟡 中 |
| 符号链接操作受限 | 符号链接处理 | 🟡 中 |

### 2.3 可用功能清单

```
✅ 基本归档创建 (tar -cf)
✅ 基本解压 (tar -xf)
✅ 压缩归档 (tar -czf, tar -cjf)
✅ 列出归档内容 (tar -tf)
✅ 增量更新 (tar -uf) - 部分可用
✅ 追加文件 (tar -rf)
✅ PAX/POSIX 格式支持
✅ 稀疏文件支持 - 部分可用
```

### 2.4 已知限制

1. **v7 格式 UID 限制**: 鸿蒙系统的高 UID 值（20001006）超出 v7 格式支持范围
2. **stdin 读取限制**: 部分从管道读取的场景返回 Permission denied
3. **符号链接限制**: SELinux 策略限制符号链接访问

---

## 三、失败原因分析

### 3.1 UID 范围超限 (190+ 次)

**错误信息**:
```
tar: value 20001006 out of uid_t range 0..2097151
```

**原因**: 鸿蒙系统用户 UID（20001006）超出 tar v7 格式支持的最大值（2097151）。

**解决方案**:
- 使用 `--owner=root --group=root` 选项
- 使用 POSIX 或 PAX 格式 (`--format=posix`)

**验证**:
```bash
# 使用 POSIX 格式避免 UID 问题
tar --format=posix -cf archive.tar files/
```

### 3.2 stdin 操作受限

**错误信息**:
```
tar: -: Cannot open: Permission denied
```

**原因**: 鸿蒙系统安全限制。

**影响**: 部分管道操作测试失败。

### 3.3 符号链接操作受限

**错误信息**:
```
tar: symlink: Cannot open: Permission denied
```

**原因**: SELinux 策略限制用户进程访问符号链接。

**解决方案**: 使用 toybox tar 处理符号链接。

---

## 四、测试详情

### 4.1 官方测试

- 测试摘要: `test-details/official/summary.txt`
- 失败分析: `test-details/official/failed-tests.md`
- 跳过说明: `test-details/official/skipped-tests.md`

### 4.2 自定义测试

无（官方测试套件已覆盖核心功能）

---

## 五、建议使用方式

### 5.1 推荐格式

```bash
# 推荐: 使用 POSIX 格式
tar --format=posix -cf archive.tar files/

# 或 PAX 格式 (默认)
tar -cf archive.tar files/
```

### 5.2 处理 UID 问题

```bash
# 归档时指定所有者
tar -cf archive.tar --owner=root --group=root files/

# 或解压时忽略所有权
tar -xf archive.tar --no-same-owner
```

### 5.3 处理符号链接

```bash
# 使用 toybox tar 处理包含符号链接的归档
/bin/tar -xf archive.tar
```

---

*报告生成时间: 2026-03-18*
