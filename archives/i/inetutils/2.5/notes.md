# inetutils 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-05-18
- 编译器: clang/clang++ 15
- 状态: failed

## 编译步骤

```bash
# 1. 解压源码
tar xf inetutils-2.5.tar.xz
cd inetutils-2.5

# 2. 更新平台识别文件
cp ~/usr/local/share/config.guess build-aux/
cp ~/usr/local/share/config.sub build-aux/

# 3. 配置
./configure --prefix=/data/service/el2/hnd_soft/soft_bus/usr/local \
    --host=aarch64-linux-ohos \
    CC=clang \
    CXX=clang++ \
    CFLAGS="-fPIC -O2" \
    LDFLAGS="-L${HOME}/usr/local/lib" \
    CPPFLAGS="-I${HOME}/usr/local/include"

# 4. 编译
make -j$(nproc)
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 失败：`error: could not setup config files machinery` | OHOS 平台配置不支持，config.status 执行失败 | 需要进一步调查 config.status 脚本 |

### 详细分析

configure 阶段失败，config.log 显示：
- 编译器检测正常（clang 识别成功）
- 大量头文件检测正常通过
- 最终在 config.status 阶段失败，错误信息：`config.status:2620: error: could not setup config files machinery`

这通常是因为：
1. autoconf 生成的配置脚本对 OHOS 平台支持不完善
2. 某些模板文件或变量替换失败
3. 需要检查 config.status 第 2620 行附近的具体失败原因

## 依赖版本

| 依赖 | 版本 |
|------|------|
| clang | 15 |
| autotools | autoconf 2.71+ |

## 验证结果

```bash
# 编译失败，configure 阶段退出
configure: exit 1
```

## 后续行动

1. 需要分析 config.status 脚本第 2620 行附近的失败原因
2. 可能需要手动修改 configure.ac 或添加 OHOS 特定的配置支持
3. inetutils 是网络工具集，包含 telnet, ftp, rsh 等，对平台依赖较高