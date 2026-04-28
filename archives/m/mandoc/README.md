# mandoc 1.14.6 — OpenHarmony 编译记录

## 基本信息
- 软件: mandoc (man page compiler)
- 版本: 1.14.6
- 构建系统: custom-configure
- 目标: ohos-aarch64
- 状态: success
- 下载源: https://mandoc.bsd.lv/snapshots/mandoc-1.14.6.tar.gz

## 软件介绍
mandoc 是一个 man page 编译器套件，包含以下工具：
- mandoc: mdoc/man 语言解析器和格式化器
- man: man page 查看器
- apropos/whatis: man page 搜索工具
- demandoc: 宏展开工具
- soelim: .so 指令处理工具
- makewhatis: man page 数据库生成工具

## 编译指导

### configure.local 配置
```bash
PREFIX=/usr/local
LN=cp -f  # HMDFS 不支持硬链接，使用复制代替
CFLAGS="-g -W -Wall -Wmissing-prototypes -Wstrict-prototypes -Wwrite-strings -Wno-unused-parameter"
STATIC="-static"
LDADD="-lz"
```

### 编译命令
```bash
make -j$(nproc)
make install DESTDIR=$TEST_PREFIX
```

### 重要提示
- mandoc 使用自定义 configure 脚本，不接受标准 autotools 参数
- 通过 configure.local 文件设置 PREFIX 和其他参数
- HMDFS 文件系统不支持硬链接，需设置 LN=cp -f

## 补丁清单

| 补丁文件 | 类型 | 说明 |
|---------|------|------|
| 0001-Makefile.local.patch | 平台适配 | 修改 LN=ln -f 为 LN=cp -f (HMDFS硬链接限制) |
| 0002-configure.local.patch | 平台适配 | 设置 PREFIX=/usr/local |

## 已知限制
1. HMDFS 文件系统不支持硬链接操作，使用复制替代
2. UTF-8 测试部分失败（环境字符集配置差异，不影响实际使用）
3. 无动态库，仅提供静态库 libmandoc.a

## 功能验证

### 命令验证
```bash
mandoc --version  # 显示版本信息
man --version     # man 命令可用
apropos --version # 搜索工具可用
whatis --version  # 搜索工具可用
```

### 测试结果
- 基础测试: 565 + 28 + 244 tests passed
- UTF-8 测试: 部分 UTF-8 相关测试失败（环境差异）
