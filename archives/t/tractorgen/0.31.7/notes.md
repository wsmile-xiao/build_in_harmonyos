# tractorgen 0.31.7 适配笔记

## 编译环境
- 构建系统: autotools (autoconf 2.13, automake 1.4)
- 编译日期: 2026-07-27
- 编译器: clang / clang++
- 状态: built

## 编译步骤

1. 下载源码: `wget -O tractorgen-0.31.7.tar.gz https://vergenet.net/~conrad/software/tractorgen/dl/tractorgen-0.31.7.tar.gz`
2. 解压源码到工作目录
3. 应用补丁: 0001-tractorgen.c.patch (增加 #include <stdlib.h>)
4. 运行 configure:
   ```bash
   ./configure --prefix=$DEFAULT_PREFIX
   ```
5. 编译: `make -j1`
6. 安装: `make install DESTDIR=$TEST_PREFIX`
7. 测试: `tractorgen 4` — 输出包含 ASCII tractor 图案

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | atoi/abort 隐式声明错误 | tractorgen.c 缺失 #include <stdlib.h> | 补丁 0001: 增加 #include <stdlib.h> 在 #include <stdio.h> 之后 |

## 源码修改

共 1 个补丁文件，均在 conandata.yml 中声明，通过 `apply_conandata_patches(self)` 自动应用：

| 补丁文件 | 说明 |
|---------|------|
| 0001-tractorgen.c.patch | 增加 #include <stdlib.h> 修复 atoi/abort 隐式声明 |

## 依赖版本

tractorgen 0.31.7 无第三方运行依赖，仅依赖系统基础构建工具（sh, cc/clang, make, install 等）。

## 验证结果

### make check 输出
```
Making check in src
make[1]: Entering directory '.../src'
make[1]: Leaving directory '.../src'
```
tractorgen 无测试套件，make check 输出 "Nothing to be done for 'check'" 等价行为。

### 二进制验证
```bash
$ tractorgen 4
         r-
        _|
       / |___\    \\
      |       |o|----\\
      |_______\\___--_\\
     (O)_O_O_(O)    \\
```
二进制可正常运行，输出包含 `(O)_O_O_(O)` 稳定片段。

### 功能验证
- `tractorgen 4` 退出码 0，输出包含 `(O)_O_O_(O)`、`r-`、`|o|----\\` 等稳定行片段
- `tractorgen` 无参运行默认输出 7 轮拖拉机，退出码 0

### conan-verify 结果
<待补充>

## 交付物

| 文件 | 说明 |
|------|------|
| bin/tractorgen | 主程序 |

## 注意事项

- R15: 不使用 --build/--host 参数。tractorgen 源码不含 config.guess/config.sub 文件
- R26: 终端工具必须静态链接（已在 generate() 中配置 -static）
- 该项目无测试套件，make check 不会执行任何测试
- clang/OHOS 下需要补丁增加 #include <stdlib.h>，否则 atoi/abort 隐式声明导致编译错误
---

**编译结束**: 2026-07-27 21:18
**最终状态**: built
