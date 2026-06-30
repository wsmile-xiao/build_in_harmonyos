# libfst

OpenFst 是一个用于构建、组合、优化和搜索加权有限状态转换器（FST）的库。

## 描述

OpenFst 是一个开源的有限状态机库，广泛应用于：
- 语音识别
- 自然语言处理
- 机器翻译
- 模式匹配
- 编译器设计

## 版本列表

| 版本 | 状态 | 编译日期 | 测试状态 |
|------|------|----------|----------|
| 1.8.4 | published | 2026-06-05 | ✅ 全部通过 |

## 核心功能

- **fstcompile**: 编译文本格式 FST 到二进制格式
- **fstprint**: 打印二进制 FST 到文本格式
- **fstinfo**: 显示 FST 详细信息
- **fstdraw**: 生成 DOT 格式图形
- **fstcompose**: 组合两个 FST
- **fstdeterminize**: 确定化 FST
- **fstminimize**: 最小化 FST
- **fstshortestpath**: 最短路径计算

共计 37 个 fst* 工具。

## 鸿蒙平台适配

### 编译要点

1. **必须显式指定编译器**（E053）:
   ```bash
   export CC=clang CXX=clang++
   ```

2. **修复 HMDFS 权限问题**（E011）:
   ```bash
   sed -i 's/umask 077/umask 022/g' configure
   ```

3. **使用支持 OpenHarmony 的 config.guess/config.sub**（E007）

### 性能

- 100 状态 FST 编译: ~0.04s
- 最短路径计算: ~0.03s

## 使用示例

```bash
# 创建简单 FST
cat > simple.txt << 'EOF'
0 1 1 1 0.5
1 2 2 2 0.3
2
EOF

# 编译
fstcompile simple.txt simple.fst

# 查看信息
fstinfo simple.fst

# 打印内容
fstprint simple.fst

# 生成图形
fstdraw simple.fst simple.dot

# 优化
fstdeterminize simple.fst det.fst
fstminimize det.fst min.fst
```

## 相关链接

- 官网: https://www.openfst.org/
- 源码: https://download.savannah.nongnu.org/releases/libfst/

---

*最后更新: 2026-06-05*