# gsl 2.7 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-05-21
- 编译器: clang / clang++
- 状态: published

## 编译步骤

1. 解压源码包
   ```bash
   tar xzf gsl-2.7.tar.gz
   cd gsl-2.7
   ```

2. 应用补丁（更新 config.guess 和 config.sub）
   ```bash
   patch -p1 < 0001-config.guess.patch
   patch -p1 < 0002-config.sub.patch
   ```

3. 配置构建选项
   ```bash
   ./configure --prefix=/usr/local \
       --host=aarch64-unknown-linux-ohos \
       CC=clang CXX=clang++
   ```

4. 编译
   ```bash
   make -j$(nproc)
   ```

5. 安装
   ```bash
   make DESTDIR=/path/to/install install
   ```

6. 打包
   ```bash
   tar czf gsl-2.7-ohos-aarch64.tar.gz ...
   ```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 HarmonyOS | 脚本中缺少 HarmonyOS 判断逻辑 | 应用补丁添加 `*:HarmonyOS:*:*` case 分支 |
| 2 | config.sub 不支持 linux-ohos 目标 | 脚本中缺少 linux-ohos triplet | 应用补丁添加 `linux-ohos*` 支持 |

## 源码修改

应用了两个平台识别相关的补丁：

### 0001-config.guess.patch
- 在 `config.guess` 中添加 HarmonyOS 系统识别
- 支持的架构：aarch64、arm、x86_64、i686
- 输出格式：`{arch}-unknown-linux-ohos`

### 0002-config.sub.patch
- 在 `config.sub` 中添加 `linux-ohos` 目标支持
- 支持 `ohos-linux` 输入转换为 `-linux-ohos` 输出

## 依赖版本

- **编译依赖**: 无外部依赖
- **构建工具**: autoconf, automake, libtool

## 验证结果

```bash
# 质量检查通过
# G1 Binary Integrity: PASS
# G2 Functional: PASS (⚠️ 1 警告)
# G3 Portability: PASS
# G4 Archive: PASS
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| gsl-2.7-ohos-aarch64.tar.gz | ~14.3 MB | 发布版本（strip后） |
| gsl-2.7-ohos-aarch64-debug.tar.gz | ~1.6 MB | 调试符号包 |

## 注意事项

1. 补丁文件仅涉及平台识别，不影响核心数学计算功能
2. 生成的库文件包括动态库 (libgsl.so) 和静态库 (libgsl.a)
3. 头文件安装在 `/usr/local/include/gsl/` 目录下
4. 无需额外配置即可使用 pkg-config 查找库路径