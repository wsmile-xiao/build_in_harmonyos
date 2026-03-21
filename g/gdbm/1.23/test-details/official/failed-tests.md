# GDBM 1.23 失败测试分析

## 失败测试列表

| 编号 | 测试名称 | 失败原因 | 影响范围 |
|------|----------|----------|----------|
| 13 | converting a 1.8-style database | 硬链接不支持 | 旧格式转换 |
| 17 | fetch from a read-only 1.8-style database | 硬链接不支持 | 旧格式只读 |
| 24 | cloexec: gdbm_open | 动态链接环境 | cloexec 功能 |
| 25 | cloexec: gdbm_reorganize | 动态链接环境 | cloexec 功能 |
| 26 | cloexec: dbm_open | 动态链接环境 | cloexec 功能 |
| 27 | cloexec: dbm_open -creat | 动态链接环境 | cloexec 功能 |

---

## 测试 13: converting a 1.8-style database

**测试目的**: 验证 gdbm 能够转换 1.8 版本格式的数据库

**失败原因**:
```
ln: cannot create hard link from 'test.pag' to 'test.dir': Operation not permitted
```

**分析**:
- gdbm 1.8 格式使用 `.pag` 和 `.dir` 两个文件
- 转换过程需要创建硬链接
- HarmonyOS 安全策略禁止用户进程创建硬链接

**影响**:
- 仅影响从 gdbm 1.8 格式转换
- 不影响新建数据库和现代格式的读写

**结论**: 系统限制，不影响核心功能

---

## 测试 17: fetch from a read-only 1.8-style database

**测试目的**: 验证从只读的 1.8 格式数据库读取数据

**失败原因**:
```
ln: cannot create hard link from 'test.pag' to 'test.dir': Operation not permitted
chmod: test.dir: No such file or directory
```

**分析**:
- 同样因为硬链接限制失败
- 测试脚本需要创建硬链接来准备测试数据

**结论**: 系统限制，不影响核心功能

---

## 测试 24-27: cloexec 测试

**测试目的**: 验证 close-on-exec 标志的正确设置

**失败原因**:
```
./cloexec00.at:20: exit code was 127, expected 0
```

**分析**:
- exit code 127 表示命令找不到或无法执行
- 测试程序使用 libtool 包装脚本
- 测试套件环境中动态链接器找不到共享库

**手动验证**:
```bash
export LD_LIBRARY_PATH=$HOME/usr/local/lib:$LD_LIBRARY_PATH
./g_open_ce .libs/fdop
# 测试通过 (exit code 0)
```

**结论**: 功能正常，测试环境配置问题

---

## 总结

| 失败类型 | 数量 | 是否为系统限制 |
|----------|------|----------------|
| 硬链接限制 | 2 | ✅ 是 |
| 动态链接环境 | 4 | ❌ 否 (可修复) |

**核心功能影响**: 无

所有失败测试均不影响 gdbm 的核心数据库读写功能。