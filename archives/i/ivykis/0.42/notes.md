# ivykis 0.42 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-05-29
- 编译器: clang/clang++
- 状态: published

## 编译步骤

1. **源码下载**：从 GitHub buytenh/ivykis 克隆 v0.42 标签
2. **初始化**：`ohc-run.py init-build ivykis 0.42`
3. **VPATH 构建**：
   ```bash
   mkdir -p /storage/Users/currentUser/builds/ivykis-0.42-build
   cd /storage/Users/currentUser/builds/ivykis-0.42-build
   export TMPDIR=/storage/Users/currentUser/builds/tmp
   export CC=clang
   export CXX=clang++
   export ac_cv_prog_cc_cross=no
   sh ../ivykis-0.42.work/configure --prefix=$DEFAULT_PREFIX
   make -j2
   make -C src install DESTDIR=$TEST_PREFIX
   ```
4. **验证**：`ohc-run.py verify-build ivykis 0.42`
5. **打包**：`ohc-run.py package ivykis 0.42`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 不识别 HarmonyOS | 缺少 HarmonyOS 检测分支 | 添加 `*:HarmonyOS:*:*` case 分支返回 `aarch64-unknown-linux-ohos` |
| 2 | config.sub 不接受 linux-ohos | OS 列表中缺少 `linux-ohos*` | 在第 118 行和第 1393 行添加 `linux-ohos*` |
| 3 | 交叉编译检测失败 | autotools 默认检测不适用于 OHOS | 设置 `ac_cv_prog_cc_cross=no` 缓存变量 |
| 4 | config.status 创建临时文件 Permission denied | HMDFS SGID 目录 + umask 077 导致新建目录无写权限 | 修改 configure 使用 `$TMPDIR` 临时目录，移除 umask 077 |
| 5 | test.mt 编译失败 | pthread_cancel/pthread_testcancel 在 musl/OHOS 上不可用 | 仅编译和安装主库 src/，跳过测试程序 |

## 源码修改

### config.guess (第 159-172 行)
```diff
+ *:HarmonyOS:*:*)
+     UNAME_MACHINE=aarch64
+     UNAME_SYSTEM=linux
+     UNAME_RELEASE=ohos
+     echo "${UNAME_MACHINE}-unknown-${UNAME_SYSTEM}-${UNAME_RELEASE}"
+     exit ;;
```

### config.sub (第 118 行和第 1393 行)
```diff
- # Earlier versions are historical exceptions
+ linux-ohos* | \
```

### configure (临时目录创建)
```diff
- {
-   tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null` &&
-   test -d "$tmp"
- }  ||
- {
-   tmp=./conf$$-$RANDOM
-   (umask 077 && mkdir "$tmp")
- } || as_fn_error $? "cannot create a temporary directory in ." "$LINENO" 5
+ tmp=$TMPDIR/conf$$-$RANDOM
+ mkdir -p "$tmp" || as_fn_error $? "cannot create a temporary directory in $TMPDIR" "$LINENO" 5
```

### test.mt/configure (同上修改)
同样修改临时目录创建逻辑

## 依赖版本

无外部依赖，纯 C 库实现异步 I/O 通知机制。

## 验证结果

```bash
# 质量门禁
G1 二进制完整性: PASS (✅3 - 3 个共享库)
G2 功能可用性: PASS (⚠️1 - 无可执行文件，纯库)
G3 可移植性: PASS
G4 档案完整性: PASS
质量报告: PASS

# 预编译包大小
ivykis-0.42-ohos-aarch64.tar.gz: 725KB
ivykis-0.42-ohos-aarch64-debug.tar.gz: 571KB
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| ivykis-0.42-ohos-aarch64.tar.gz | 725KB | 预编译包（含 lib/、include/） |
| ivykis-0.42-ohos-aarch64-debug.tar.gz | 571KB | 调试符号包 |

## 注意事项

1. **必须使用 VPATH 构建**：HMDFS 文件系统权限限制，不能在源码目录构建
2. **必须设置 TMPDIR**：configure 临时文件创建需要无 SGID 继承的目录
3. **跳过 test.mt**：多线程测试程序使用了 musl 不支持的 pthread_cancel
4. **manifest.yaml 格式**：需要顶层 `build_system:` 字段而非嵌套结构
---

**编译结束**: 2026-05-29 12:01
**最终状态**: built
