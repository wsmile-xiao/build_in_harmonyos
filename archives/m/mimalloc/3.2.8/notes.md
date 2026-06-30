# mimalloc 3.2.8 编译笔记

## 基本信息

- 软件名称: mimalloc
- 版本: 3.2.8
- 构建系统: CMake
- 编译日期: 2026-05-20
- 编译器: clang/clang++

## 编译流程

### Phase 1: 初始化

- 下载源码: https://github.com/microsoft/mimalloc/archive/refs/tags/v3.2.8.tar.gz
- 解压位置: ~/tmp/mimalloc-3.2.8
- 归档目录: archives/m/mimalloc/3.2.8/

### Phase 2: 预扫描

- 构建系统: CMake
- 特殊选项: MI_LIBC_MUSL (用于 musl libc 环境)

### Phase 3: 编译

#### Step 1: CMake 配置

```bash
cd ~/tmp/mimalloc-3.2.8
mkdir -p build
cd build
cmake -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX \
      -DCMAKE_BUILD_TYPE=Release \
      -DMI_LIBC_MUSL=ON \
      ..
```

#### Step 2: 编译

```bash
make -j2
```

#### Step 3: 安装（staging）

```bash
make install DESTDIR=$TEST_PREFIX
```

#### Step 4: 测试

```bash
make test
```

#### Step 5: 预编译包制作

```bash
python3 $SKILL_ROOT/scripts/ohc-run.py package mimalloc 3.2.8
```

#### Step 6: 安装到本地

```bash
make install
```

### Phase 4: 收尾

- 验证安装
- 生成质量门禁报告
- 归档整理

## 遇到的问题

（编译过程中记录）

## 知识提取

### E999: mimalloc MI_OVERRIDE 导致段错误

**现象**: 当 MI_OVERRIDE=ON 时，测试程序段错误，进程被 killed

**根因**: mimalloc 尝试覆盖系统 malloc/free 时，与鸿蒙系统的内存管理机制冲突

**解决方案**: 设置 MI_OVERRIDE=OFF，使用 mimalloc 作为独立库

**知识草稿**: knowledge/graph/draft/E999-draft-F27F.kv

---

**编译结束**: 2026-05-20 23:30
**最终状态**: built
**测试结果**: 4/4 通过 (100%)
**预编译包**: mimalloc-3.2.8-ohos-aarch64.tar.gz (979KB)
---

**编译结束**: 2026-05-20 23:27
**最终状态**: built
