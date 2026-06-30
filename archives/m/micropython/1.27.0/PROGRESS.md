# MicroPython 1.27.0 编译进度

**开始日期**: 2026-05-14 15:01
**完成日期**: 2026-05-14 23:39
**总耗时**: 约 8.5 小时
**状态**: ✅ 编译完成（minimal 变体）

## 步骤记录

| 步骤 | 状态 | 时间 | 备注 |
|------|------|------|------|
| Step 1 init | ✅ | 30min | 源码从 gitee 克隆，init-build 有嵌套检测问题，手动整理目录 |
| Step 2 patches | ✅ | 1min | 无需补丁，源码干净 |
| Step 3 configure | ⏭️ | - | MicroPython 使用 Makefile，无 configure 步骤 |
| Step 4 make | ✅ | 5min | 构建 mpy-cross 和 minimal 变体成功 |
| Step 5 install | ✅ | 2min | 手动复制到 DESTDIR（无 make install） |
| Step 6 safety | ✅ | 1min | 二进制签名后可执行 |
| Step 7 check | ✅ | 2min | 355 测试通过，566 跳过（minimal 变体正常） |
| Step 8 staging | ✅ | 1min | 文件已复制到 TEST_PREFIX |
| Step 9 package | ✅ | 2min | 打包预编译包成功（728KB） |
| Step 10 deploy | ✅ | 1min | 安装到本地 ~/usr/local，验证成功 |
| Step 11 finish | ✅ | 5min | 归档完成，质量门禁通过 |

## 构建详情

### 构建系统
| 项目 | 详情 |
|------|------|
| 类型 | custom (Makefile-based) |
| 平台 | ports/unix |
| 变体 | minimal（无 libffi） |
| 编译器 | clang 15.0.4 |
| 目标 | ohos-aarch64 |

### 构建命令
```bash
# Step 1: 构建 mpy-cross 跨编译器
cd ~/builds/micropython-1.27.0.work
make -C mpy-cross -j$(nproc)
# 输出: mpy-cross/build/mpy-cross (474KB)

# Step 2: 构建 minimal 变体
cd ports/unix
make VARIANT=minimal -j$(nproc)
# 输出: build-minimal/micropython (174KB)

# Step 3: 运行测试
make VARIANT=minimal test
# 结果: 355 passed, 566 skipped, 0 failed

# Step 4: 手动安装到 DESTDIR
source .build-context-micropython-1.27.0
mkdir -p $TEST_PREFIX/$DEFAULT_PREFIX/bin
cp ports/unix/build-minimal/micropython $TEST_PREFIX/$DEFAULT_PREFIX/bin/
cp mpy-cross/build/mpy-cross $TEST_PREFIX/$DEFAULT_PREFIX/bin/

# Step 5: 二进制签名
ohc-run.py sign-elf $TEST_PREFIX/$DEFAULT_PREFIX/bin/micropython
ohc-run.py sign-elf $TEST_PREFIX/$DEFAULT_PREFIX/bin/mpy-cross

# Step 6: 打包预编译包
ohc-run.py package micropython 1.27.0
# 输出: micropython-1.27.0-ohos-aarch64.tar.gz (728KB)

# Step 7: 安装到本地（模拟用户部署）
cd ~/usr/local
tar -xzf $BUILD_ARCHIVE_DIR/packaging/micropython-1.27.0-ohos-aarch64.tar.gz

# Step 8: 验证安装
micropython --version
micropython -c "print('Hello from MicroPython!')"
mpy-cross --version
```

### 构建产物
| 文件 | 大小 | 用途 |
|------|------|------|
| ports/unix/build-minimal/micropython | 174KB | Python 解释器（minimal 变体） |
| mpy-cross/build/mpy-cross | 474KB | 跨编译器（编译 .py → .mpy） |
| micropython-1.27.0-ohos-aarch64.tar.gz | 728KB | 预编译包（发布） |

## 测试详情

### 测试统计
```
总测试数: 921（执行 + 跳过）
执行测试: 355（38.6%）
通过测试: 355（100% 执行测试通过）
跳过测试: 566（minimal 变体正常）
失败测试: 0
```

### 测试分类
| 类别 | 执行 | 跳过 | 通过 |
|------|------|------|------|
| basics | 全部 | 0 | ✅ |
| import | 全部 | 0 | ✅ |
| stress | 全部 | 0 | ✅ |
| micropython | 部分 | 大量 | ✅ |
| extmod | 部分 | 大量 | ✅ |
| ports/unix | 部分 | 大量 | ✅ |

### 跳过原因
minimal 变体禁用了以下功能，相关测试被跳过：
- 原生代码生成（viper/native）~50 个测试
- 堆分配测试 ~30 个测试
- 外部模块 ~200+ 个测试
- FFI 测试 ~20 个测试（缺少 libffi）
- SSL/TLS ~50 个测试
- asyncio ~50 个测试

## 发现与知识

### 问题 1: 网络下载失败
**现象**: GitHub tarball 下载失败（HTTPS 连接超时，等待超过 10 分钟）
**原因**: OpenHarmony 网络限制，无法直接访问 GitHub
**解决方案**: 从 gitee 镜像克隆源码
```bash
git clone --depth 1 --branch v1.27.0 https://gitee.com/mirrors/micropython.git
```
**知识沉淀**: 网络问题可使用镜像源解决

### 问题 2: init-build 嵌套检测错误
**现象**: init-build 将 docs 目录内容当作源码根目录
**原因**: init-build 的"嵌套源码检测"逻辑误判
**解决方案**: 手动整理源码目录结构
```bash
mv ~/tmp/micropython-check ~/builds/micropython-1.27.0.work
tar -cJf ~/builds/micropython-1.27.0.tar.xz micropython-1.27.0.work
ohc-run.py init-build micropython 1.27.0 --no-download --force
```
**影响**: 延迟约 30 分钟

### 问题 3: libffi 缺失
**现象**: standard 变体需要 libffi，但 OpenHarmony 平台无预编译 libffi
**决策**: 选择 minimal 变体构建
**理由**:
- minimal 变体无外部依赖
- 体积小（174KB vs 500KB+）
- 适合嵌入式场景
- 核心 Python 功能完整

### 问题 4: 自定义构建系统适配
**现象**: MicroPython 无 configure 和 make install
**原因**: 自定义 Makefile 构建系统
**解决方案**: 手动复制文件到 DESTDIR
**影响**: clean-verify G0 无法运行（无 configure）
**补救**: 手动验证构建成功

### 问题 5: 二进制签名要求
**现象**: 未签名二进制无法执行（permission denied）
**原因**: OpenHarmony 安全策略要求 ELF 签名
**解决方案**: 使用 `ohc-run.py sign-elf` 签名
```bash
ohc-run.py sign-elf micropython
ohc-run.py sign-elf mpy-cross
```

## 归档完整性

### 软件级文件
| 文件 | 状态 | 大小 |
|------|------|------|
| README.md | ✅ 完成 | 3.2KB |
| RELEASENOTE.md | ✅ 完成 | 4.5KB |
| install.sh | ✅ 完成 | 1.2KB |

### 版本级文件
| 文件 | 状态 | 大小 |
|------|------|------|
| manifest.yaml | ✅ 完成 | 589B |
| README.md | ✅ 完成 | 4.3KB |
| PROGRESS.md | ✅ 完成 | 本文件 |
| patches/ | ✅ 空（无补丁） | - |
| reports/test-report.md | ✅ 完成 | 6.7KB |
| reports/quality-report.md | ✅ 完成 | 288B |
| packaging/*.tar.gz | ✅ 完成 | 728KB + 39KB |
| packaging/*.sh | ✅ 完成 | 1.5KB |

### 质量门禁
| 门禁 | 状态 | 备注 |
|------|------|------|
| G0 | ⚠️ | 无 configure 步骤，已手动验证 |
| G1 | ✅ | 二进制完整性通过 |
| G2 | ✅ | 功能可用性通过 |
| G3 | ✅ | 可移植性通过 |
| G4 | ✅ | 档案完整性通过 |

## 最终验证

### 功能验证
```bash
$ micropython --version
MicroPython v1.27.0 on 2026-05-14; linux [Clang 15.0.4] version

$ micropython -c "print('Hello from MicroPython!')"
Hello from MicroPython!

$ mpy-cross --version
MPY-CROSS
```

### Python 语法验证
```python
>>> list(5 * x + y for x in range(10) for y in [4, 2, 1])
[4, 2, 1, 9, 7, 6, 14, 12, 11, 19, 17, 16, 24, 22, 21, 29, 27, 26, 34, 32, 31, 39, 37, 36, 44, 42, 41, 49, 47, 46]

>>> import sys
>>> sys.platform
'linux'

>>> 2**100
1267650600228229401496703205376
```

## 编译总结

### 成功要素
1. ✅ 源码获取：使用 gitee 镜像解决网络问题
2. ✅ 构建变体选择：minimal 适配 OpenHarmony 环境
3. ✅ 自定义构建系统：理解 Makefile 结构，手动安装
4. ✅ 二进制签名：符合 OpenHarmony 安全要求
5. ✅ 测试验证：100% 执行测试通过
6. ✅ 归档完整：所有必填文件齐全且内容详实

### 可改进项
1. ⚠️ init-build 嵌套检测逻辑需要优化
2. ⚠️ clean-verify G0 需适配无 configure 的构建系统
3. ⚠️ 可考虑编译 libffi 以支持 standard 变体

### 编译结论
MicroPython 1.27.0 minimal 变体在 OpenHarmony 平台编译成功，预编译包可用，归档完整。

---

**编译完成**: 2026-05-14 23:39
**最终状态**: ✅ success
**归档路径**: archives/m/micropython/1.27.0/
