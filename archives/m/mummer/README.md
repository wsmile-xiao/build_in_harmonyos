# MUMmer

## 简介
MUMmer是一个用于快速比对大型DNA序列的系统。它可以比对：
- 整个基因组与其他基因组
- 大型基因组组装之间
- 部分（草稿）基因组序列
- 一组reads到基因组

## 特点
- **快速**: 能在几秒钟内找到两个细菌基因组之间的所有20-bp最大精确匹配
- **易于使用**: 简单的命令行界面
- **多功能**: 支持多种比对模式（nucmer、promer等）
- **可扩展**: 处理数百或数千个contigs轻松自如

## 主要工具
- **nucmer**: 核酸序列比对工具
- **promer**: 蛋白质序列比对工具（六帧翻译）
- **mummer**: 快速精确匹配查找
- **show-coords**: 显示比对坐标
- **show-aligns**: 显示比对序列
- **show-snps**: 显示SNP差异
- **delta-filter**: 过滤比对结果

## 安装
```bash
# 从预编译包安装（推荐）
curl -fsSL install.sh | sh -s -- mummer 4.0.1

# 从源码编译
tar -xzf mummer-4.0.1.tar.gz
cd mummer-4.0.1
autoreconf -fi
sed -i 's/umask 077/umask 022/g' configure  # 鸿蒙系统必需
./configure --prefix=/usr/local
make -j1
make install
```

## 使用示例
```bash
# 比对两个基因组
nucmer --prefix=out ref.fasta query.fasta

# 显示比对结果
show-coords out.delta

# 查找SNP
show-snps out.delta
```

## 编译注意事项（鸿蒙系统）
1. 需要修改configure中的umask: `sed -i 's/umask 077/umask 022/g' configure`
2. 需要修复C++ narrowing错误: 应用补丁 0002-postnuc-narrowing.patch
3. 要要安装yaggo工具: 从 https://github.com/gmarcais/yaggo/releases下载

## 参考文献
- MUMmer4: Marçais et al., PLoS Computational Biology (2018)
- MUMmer3: Kurtz et al., Genome Biology (2004)

## 许可证
MIT License

## 官方网站
- https://mummer4.github.io/
- https://github.com/mummer4/mummer
