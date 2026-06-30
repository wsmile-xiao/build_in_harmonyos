# open-mpi 5.0.10 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-05-28
- 编译器: clang/clang++
- 状态: built
- 目标平台: aarch64-unknown-linux-ohos

## 编译步骤

1. 初始化编译环境
   ```bash
   python3 $SKILL_ROOT/scripts/ohc-run.py init-build open-mpi 5.0.10 --url=https://download.open-mpi.org/release/open-mpi/v5.0/openmpi-5.0.10.tar.gz
   source .build-context-open-mpi-5.0.10
   cd $BUILD_SRC_DIR
   ```

2. 平台适配（config.guess/config.sub 已支持 ohos）
   ```bash
   # 检查是否识别 HarmonyOS
   grep -r "ohos" build-aux/config.sub  # ✅ 已支持
   ```

3. 执行 configure
   ```bash
   ./configure --prefix=$DEFAULT_PREFIX
   # 成功，配置目标平台为 aarch64-unknown-linux-ohos
   ```

4. 执行编译（解决 rindex 符号问题）
   ```bash
   make -j1  # 编译约 25 分钟
   ```

5. 安装验证
   ```bash
   make install DESTDIR=$TEST_PREFIX
   make install  # 本地安装
   $DEFAULT_PREFIX/bin/mpirun --version  # 验证成功
   ```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | rindex 符号未定义 | musl libc 不提供 rindex() 函数，只提供 strrchr() | 在 plm_ssh_module.c 开头添加 `#define rindex strrchr` |
| 2 | manifest.yaml 缺少 build_system 字段 | 模板使用 system 而非 build_system | 修改为 `build_system: autotools` |

## 源码修改

### 0001-3rd-party-prrte-src-mca-plm-ssh-plm_ssh_module.c.patch
- 文件: `3rd-party/prrte/src/mca/plm/ssh/plm_ssh_module.c`
- 修改: 在文件开头添加 `#define rindex strrchr`
- 原因: musl libc 兼容性修复，确保 rindex 函数可用

## 依赖版本

无外部依赖，OpenMPI 自带 libevent 和 hwloc

## 验证结果

```bash
$ $DEFAULT_PREFIX/bin/mpirun --version
mpirun (Open MPI) 5.0.10

$ $DEFAULT_PREFIX/bin/ompi_info | head -15
Package: Open MPI 100@localhost Distribution
Open MPI: 5.0.10
MPI API: 3.1.0
Configured architecture: aarch64-unknown-linux-ohos
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| open-mpi-5.0.10-ohos-aarch64.tar.gz | 103MB | 预编译包（已 ELF 签名） |
| open-mpi-5.0.10-ohos-aarch64-debug.tar.gz | 13MB | 调试符号包 |

## 注意事项

1. musl libc 平台需注意 rindex 函数兼容性问题
2. 编译时间较长（约 25 分钟），建议使用 -j1 避免并发问题
3. 自带的 libevent 和 hwloc 已自动适配 ohos 平台
---

**编译结束**: 2026-05-28 13:52
**最终状态**: published
**发布日期**: 2026-05-28
