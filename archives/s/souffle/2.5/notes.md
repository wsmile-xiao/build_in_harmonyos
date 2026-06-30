# souffle 2.5 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-06-15
- 编译器: clang 15.0.4 / clang++ 15.0.4
- 平台: HarmonyOS (aarch64, musl libc)
- 状态: published

## 编译步骤

1. 初始化：使用 `ohc-run.py init-build souffle 2.5 --url=<URL>`
   - GitHub直连超时，通过ghfast.top镜像下载源码包
   - init-build脚本误判构建系统为autotools，需手动修正为cmake
2. cmake配置（手动模式B）：
   ```bash
   mkdir -p build && cd build
   cmake .. -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX \
     -DCMAKE_BUILD_TYPE=Release \
     -DSOUFFLE_USE_CURSES=OFF \
     -DSOUFFLE_USE_ZLIB=OFF \
     -DSOUFFLE_USE_SQLITE=OFF \
     -DSOUFFLE_USE_OPENMP=OFF \
     -DSOUFFLE_USE_LIBFFI=OFF \
     -DSOUFFLE_GIT=OFF \
     -DSOUFFLE_ENABLE_TESTING=OFF \
     -DCMAKE_CXX_COMPILER=clang++
   ```
3. `make -j2` 编译（约5分钟）
4. `make install DESTDIR=$TEST_PREFIX` （staging隔离安装）
5. `make install` （本地安装验证）
6. `ohc-run.py verify-build` 质量门禁 → PASS
7. `ohc-run.py package` 预编译包制作 → 成功
8. `ohc-run.py finish souffle 2.5 published` 收尾

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | cmake FindCurses找不到ncursesw | 平台cmake FindCurses模块无法识别libncursesw.a | 禁用SOUFFLE_USE_CURSES=OFF（curses是可选的provenance显示功能） |
| 2 | init-build误判构建系统为autotools | URL的tar.gz格式导致脚本猜测为autotools | 手动修正BUILD_SYSTEM=cmake，手动执行cmake配置 |
| 3 | GitHub下载超时 | 网络无法直连github.com | 通过ghfast.top镜像下载 |
| 4 | SOUFFLE_GIT导致cmake报错 | tarball构建无git仓库 | 禁用SOUFFLE_GIT=OFF，版本号字段为空 |
| 5 | 运行souffle缺少mcpp/gcc预处理器 | 平台无mcpp和gcc可执行文件 | 使用--no-preprocessor参数运行 |
| 6 | 编译输出模式(-o)链接失败 | libc++ ABI与OHOS SDK不兼容（std::__n1命名空间） | 暂不可用，需后续排查libc++兼容性 |

## 源码修改

无补丁，无源码修改。所有问题通过cmake配置选项解决。

## 依赖版本

| 依赖 | 版本 | 用途 |
|------|------|------|
| flex | 2.6.4 | Datalog语法扫描器 |
| bison | 3.8.2 | Datalog语法解析器 |
| clang | 15.0.4 | C++编译器 |
| cmake | 4.1.2 | 构建系统 |

## 功能验证结果

### 解释模式（核心功能）

| 测试 | 结果 | 说明 |
|------|------|------|
| 传递闭包（路径计算） | ✅ | 正确计算5节点图的全部路径 |
| 符号类型关系查询（祖先） | ✅ | 正确递推4代人祖先关系 |
| 聚合操作（max/count） | ✅ | max=70000, count=4 |
| 否定查询 | ✅ | 正确排除disqualified |
| 等价关系 | ✅ | 正确计算所有等价关系对 |
| 内建函数count | ✅ | 正确返回1 |
| souffleprof可执行 | ✅ | 二进制可执行 |
| 帮助信息 | ✅ | 正确显示 |

### 预处理器兼容性

| 模式 | 结果 | 说明 |
|------|------|------|
| --no-preprocessor | ✅ | 可用 |
| --preprocessor=clang | ❌ | Datalog注释被视为C预处理指令 |
| 默认（mcpp/gcc） | ❌ | 平台缺少mcpp和gcc |

### 编译输出模式

| 模式 | 结果 | 说明 |
|------|------|------|
| -o（生成独立可执行文件） | ❌ | libc++ ABI链接失败 |

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| souffle-2.5-ohos-aarch64.tar.gz | 20267KB | 预编译包（含souffle和souffleprof二进制） |
| souffle-2.5-ohos-aarch64-debug.tar.gz | 10432KB | debug符号包 |

## 注意事项

1. **版本号字段为空**：由于从tarball构建（非git仓库）且禁用SOUFFLE_GIT，版本号无法自动提取。这是预期行为，不影响功能。
2. **预处理器限制**：本平台缺少mcpp和gcc，用户必须使用`--no-preprocessor`参数运行souffle，否则会报错。建议后续安装mcpp预编译包。
3. **编译输出模式不可用**：souffle -o 生成的C++代码因libc++ ABI问题链接失败，此为平台限制。解释模式完全可用。
4. **可选功能已禁用**：CURSES/ZLIB/SQLITE/OPENMP/LIBFFI均已禁用，核心Datalog编译器功能正常。provenance交互显示、文件压缩、sqlite存储、并行执行、外函数接口等功能不可用。

---

**编译结束**: 2026-06-15 22:40
**最终状态**: published
