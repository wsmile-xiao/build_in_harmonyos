# perl-http-parser-xs 0.17-r9 编译笔记

## Phase 1: 初始化
- ✅ 下载源码成功（从 CPAN）
- ⚠️ init-build 脚本错误：嵌套源码检测 bug，将 picohttpparser 子目录提升为顶层
- ✅ 手动解压正确的源码解决此问题

## Phase 2: 编译尝试（第一次）

### 编译系统
- Perl Module::Install + XS
- 使用 perl Makefile.PL 生成 Makefile
- 需要编译 C 代码（XS 扩展）

### 遇到的问题

**问题 1: 缺少系统头文件**
- 错误：`fatal error: 'sys/types.h' file not found`
- 原因：Perl XS 模块需要编译 C 代码，而鸿蒙系统默认缺少系统头文件
- 解决方案：使用 OHOS SDK sysroot（`/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/sysroot`）

**问题 2: 缺少链接器启动文件（初次尝试失败）**
- 错误：
  ```
  ld.lld: error: cannot open crtbeginS.o: No such file or directory
  ld.lld: error: cannot open crtendS.o: No such file or directory
  ld.lld: error: unable to find library -l:libunwind.a
  ```
- 原因：OHOS SDK sysroot 中只有静态 crt 文件，缺少动态库编译所需的 crtbeginS.o 和 crtendS.o

## Phase 3: 参考 perl-dbd-pg 成功经验重新编译

### 关键发现
- perl-dbd-pg 成功编译了 Perl XS 模块，使用 `-nostartfiles -nodefaultlibs -lc` 参数
- 这些参数可以跳过缺失的 CRT 文件，直接链接 libc

### 解决方案

1. **修改 Makefile 的 OTHERLDFLAGS**（第 478 行）
   - 原值：`OTHERLDFLAGS = `
   - 新值：`OTHERLDFLAGS = -nostartfiles -nodefaultlibs -lc`

2. **重新运行 make**
   ```bash
   cd /storage/Users/currentUser/tmp/builds/perl-http-parser-xs-0.17-r9.work
   make OTHERLDFLAGS="-nostartfiles -nodefaultlibs -lc"
   ```

3. **安装**
   ```bash
   make install DESTDIR=/storage/Users/currentUser/tmp/test-install-perl-http-parser-xs-0.17-r9
   ```

### 编译结果
- ✅ XS.so 成功生成（25856 bytes）
- ✅ XS.pm（Perl 模块）
- ✅ PP.pm（纯 Perl 版本）

## 验证结果

| 文件 | 大小 | 类型 |
|------|------|------|
| XS.so | 25856 bytes | ELF shared object, 64-bit LSB arm64 |
| XS.pm | - | Perl 模块 |
| PP.pm | - | Perl 纯实现 |

## 注意事项

1. **Perl XS 模块链接参数**：所有 Perl XS 模块在鸿蒙上编译需要 `-nostartfiles -nodefaultlibs -lc`
2. **Module::Install 构建系统**：不能像 ExtUtils::MakeMaker 那样直接在 Makefile.PL 中添加 dynamic_lib 参数
3. **命令行传参**：可以通过 `make OTHERLDFLAGS="..."` 传递链接参数

## 知识沉淀

| 问题 | 解决方案 | 适用范围 |
|------|---------|---------|
| CRT 文件缺失 | `-nostartfiles -nodefaultlibs -lc` | 所有 Perl XS 模块 |
| Makefile.PL 不支持 dynamic_lib | 命令行传参或修改 Makefile | Module::Install 项目 |

## Phase 4: 功能测试

### 测试环境
- 平台: OpenHarmony (aarch64-unknown-linux-ohos)
- Perl: 5.42.0
- 测试日期: 2026-06-11

### 测试结果

| 测试类型 | 结果 | 详情 |
|---------|------|------|
| 模块加载 | ✅ PASS | HTTP::Parser::XS v0.17 加载成功 |
| 内置测试套件 | ✅ PASS | 6 文件, 81 测试, 全部通过 |
| 功能测试 | ✅ PASS | 4/4 功能测试通过 |

### 功能验证详情

**测试 1: GET 请求解析** ✅
- parse_http_request 正确解析 GET /foo/bar?baz=123
- 正确提取 REQUEST_METHOD, REQUEST_URI, PATH_INFO, QUERY_STRING

**测试 2: HTTP 响应解析** ✅
- parse_http_response 正确解析 HTTP/1.1 200 OK
- 正确提取 status, message, headers

**测试 3: POST 请求解析** ✅
- 正确解析 POST 请求和 Content-Type, Content-Length, Authorization 头

**测试 4: 错误处理** ✅
- 对无效请求正确返回错误码 -2

### 内置测试套件

```
make test HARNESS_OPTIONS=j1
All tests successful.
Files=6, Tests=81
Result: PASS
```

| 测试文件 | 状态 |
|---------|------|
| t/00base.t | ok |
| t/01simple.t | ok |
| t/02response.t | ok |
| t/03response-error.t | ok |
| t/04response-format.t | ok |
| t/05too-much.t | skipped (PP 无静态限制) |

### 使用说明

```bash
# 需要指定安装路径（系统 Perl @INC 不包含用户路径）
perl -I /storage/Users/currentUser/usr/local/lib/site_perl/5.42.0/aarch64-linux \
     -MHTTP::Parser::XS \
     -e 'print $HTTP::Parser::XS::VERSION'
```

### 平台兼容性验证

| 检查项 | 状态 | 说明 |
|--------|------|------|
| XS.so 加载 | ✅ | 需要 -I 指定路径 |
| SELinux HMDFS | ⚠️ | 已安装到本地目录可正常加载 |
| 功能完整性 | ✅ | 所有解析功能正常工作 |

---
**编译结束**: 2026-06-11 14:25
**最终状态**: built
**功能测试**: PASS (2026-06-11)
**参考**: perl-dbd-pg/3.18.0 成功经验
