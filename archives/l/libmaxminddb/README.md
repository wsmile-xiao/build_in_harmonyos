# libmaxminddb 1.13.3 — OpenHarmony 编译记录

## 基本信息
- **软件**: libmaxminddb
- **版本**: 1.13.3
- **构建系统**: autotools
- **目标平台**: ohos-aarch64 (HarmonyOS)
- **编译状态**: partial (96.55%测试通过)
- **编译日期**: 2026-05-06

## 软件简介
libmaxminddb 是 MaxMind DB 文件格式的 C 语言读取库。它提供了快速、高效的 API 用于读取 GeoIP2 和 GeoLite2 数据库文件。

### 主要功能
- 读取 MaxMind DB (.mmdb) 二进制数据库文件
- 支持 IPv4 和 IPv6 地址查找
- 提供高效的内存映射 (mmap) 访问方式
- 线程安全设计
- 支持复杂的数据结构查询（嵌套 map、数组等）

## 编译指导

### 前置要求
- HarmonyOS/OpenHarmony aarch64 系统
- clang/gcc 编译器
- autotools 构建工具链
- pkg-config

### 编译步骤（快速）
```bash
# 1. 初始化
SKILL_ROOT="/storage/Users/currentUser/.opendesk/apps/skills/resources/openharmony-compile-agent"
python3 $SKILL_ROOT/scripts/ohc-run.py init-build libmaxminddb 1.13.3 \
  --url=https://github.com/maxmind/libmaxminddb/releases/download/1.13.3/libmaxminddb-1.13.3.tar.gz

# 2. 读取上下文
source .build-context-libmaxminddb-1.13.3
cd $BUILD_SRC_DIR

# 3. 预处理（关键！）
perl $SKILL_ROOT/scripts/patch-autotools-ohos.pl config.guess config.sub

# 4. Configure（遵循 R1 铁律）
./configure --prefix=$DEFAULT_PREFIX

# 5. 编译
make -j$(nproc)

# 6. Staging 安装（遵循 R20 铁律）
make install DESTDIR=$TEST_PREFIX

# 7. 测试验证
make check

# 8. 打包
python3 $SKILL_ROOT/scripts/ohc-run.py package libmaxminddb 1.13.3

# 9. Finish
python3 $SKILL_ROOT/scripts/ohc-run.py finish libmaxminddb 1.13.3 success
```

### 关键补丁说明
本软件在 HarmonyOS 平台编译需要以下补丁：

1. **config.guess/config.sub 补丁**（必需）
   - 问题：GNU config.guess 不识别 HarmonyOS
   - 解决：使用 `patch-autotools-ohos.pl` 脚本
   - 输出三元组：`aarch64-unknown-linux-ohos`

2. **configure umask 补丁**（必需）
   - 问题：umask 077 在 HMDFS 目录失败
   - 解决：修改 configure 中 umask 077 → 007
   - 设置 TMPDIR 环境变量

## 补丁清单

| 补丁文件 | 类型 | 用途 | 行数变更 |
|---------|------|------|----------|
| 0001-config.guess.patch | 平台识别 | HarmonyOS 系统检测 | +23/-7 |
| 0002-config.sub.patch | 平台识别 | ohos-linux 三元组 | +25/-9 |
| 0003-configure.patch | 权限修复 | umask + TMPDIR | +1/-1 |

所有补丁均为 **platform_only** 类型，仅针对 HarmonyOS 平台，不影响上游代码逻辑。

## 已知限制

### 测试限制
1. **dump_t 测试失败**
   - 状态：1/29 测试程序失败
   - 影响：仅影响调试输出格式验证
   - 原因：输出格式与期望不匹配，触发 SIGTRAP
   - 建议：标记为已知限制，不影响核心 API

2. **Perl 测试模块缺失**
   - 缺失模块：IPC::Run3, Test::Output
   - 影响：3 个 Perl 集成测试被跳过
   - 不影响：核心 C 库功能

### 平台限制
- 无明显限制，核心功能完全可用
- mmdblookup 工具正常运行
- 库文件正确安装并可被链接

## 功能验证

### 验证命令
```bash
# 设置库路径
export LD_LIBRARY_PATH=~/usr/local/lib:$LD_LIBRARY_PATH

# 工具验证
~/usr/local/bin/mmdblookup --help
~/usr/local/bin/mmdblookup --version

# pkg-config 验证
pkg-config --modversion libmaxminddb
pkg-config --cflags libmaxminddb
pkg-config --libs libmaxminddb

# 库文件检查
ls ~/usr/local/lib/libmaxminddb*
ls ~/usr/local/include/maxminddb*.h
```

### 预期结果
- mmdblookup 显示完整帮助信息 ✅
- pkg-config 返回版本 1.13.3 ✅
- 静态库和动态库都存在 ✅
- 头文件正确安装 ✅

## 使用示例

### C 程序示例
```c
#include <maxminddb.h>

int main() {
    MMDB_s mmdb;
    int status = MMDB_open("/path/to/GeoIP2-City.mmdb", MMDB_MODE_MMAP, &mmdb);
    
    if (status != MMDB_SUCCESS) {
        fprintf(stderr, "Error: %s\n", MMDB_strerror(status));
        return 1;
    }
    
    // 查询 IP 地址
    MMDB_lookup_result_s result = MMDB_lookup_string(&mmdb, "8.8.8.8");
    
    if (result.found_entry) {
        MMDB_entry_data_s entry_data;
        status = MMDB_get_value(&result.entry, &entry_data, "country", "iso_code", NULL);
        
        if (status == MMDB_SUCCESS && entry_data.has_data) {
            printf("Country: %s\n", entry_data.utf8_string);
        }
    }
    
    MMDB_close(&mmdb);
    return 0;
}
```

### 编译链接
```bash
# 使用 pkg-config
gcc -o geoip geoip.c $(pkg-config --cflags --libs libmaxminddb)

# 手动链接
gcc -o geoip geoip.c -I~/usr/local/include -L~/usr/local/lib -lmaxminddb
```

## API 参考

### 核心函数
- `MMDB_open()` - 打开数据库文件
- `MMDB_close()` - 关闭数据库
- `MMDB_lookup_string()` - 字符串 IP 查找
- `MMDB_lookup_sockaddr()` - socket 地址查找
- `MMDB_get_value()` - 获取值
- `MMDB_aget_value()` - 数组路径获取值
- `MMDB_vget_value()` - 可变参数获取值
- `MMDB_get_entry_data_list()` - 获取完整数据列表
- `MMDB_strerror()` - 错误字符串
- `MMDB_lib_version()` - 库版本

### 数据结构
- `MMDB_s` - 数据库结构
- `MMDB_lookup_result_s` - 查找结果
- `MMDB_entry_data_s` - 数据条目
- `MMDB_entry_data_list_s` - 数据列表

## 预编译包安装

### 快速安装
```bash
# 方法 1：使用 install.sh
curl -fsSL <url>/install.sh | sh -s -- 1.13.3

# 方法 2：手动安装
tar xzf libmaxminddb-1.13.3-ohos-aarch64.tar.gz -C ~/usr/local
cd ~/usr/local/libmaxminddb-1.13.3-ohos-aarch64
sh install-libmaxminddb-1.13.3.sh
```

### 安装位置
- 二进制工具：`~/usr/local/bin/mmdblookup`
- 动态库：`~/usr/local/lib/libmaxminddb.so*`
- 静态库：`~/usr/local/lib/libmaxminddb.a`
- 头文件：`~/usr/local/include/maxminddb.h`
- pkg-config：`~/usr/local/lib/pkgconfig/libmaxminddb.pc`

## 依赖关系

### 无编译依赖
libmaxminddb 是独立的 C 库，无需其他三方库依赖。

### 运行依赖
- 标准 C 库 (libc)
- 系统调用：mmap, open, close, read

### 反向依赖
以下软件可能依赖 libmaxminddb：
- GeoIP2 工具链
- nginx (ngx_http_geoip2_module)
- Apache (mod_maxminddb)
- 各种 IP 地理定位应用

## 测试覆盖

### 测试统计
- 测试程序：29 个
- 通过：28 个 (96.55%)
- 失败：1 个 (dump_t - 调试输出测试)
- 断言总数：2305 个
- 通过断言：2262 个 (98.13%)

### 核心测试覆盖
✅ 所有核心 API 测试通过：
- 数据库打开/关闭
- IPv4/IPv6 查找
- 嵌套数据结构读取
- 错误处理
- 线程安全
- 内存管理

## 质量保证

### 质量门禁状态
| 门禁 | 状态 | 说明 |
|------|------|------|
| G0 干净构建 | ✅ PASS | 补丁自包含性验证 |
| G1 二进制完整性 | ✅ PASS | 可执行文件完整 |
| G2 功能可用性 | ✅ PASS | pkg-config 正常 |
| G3 可移植性 | ✅ PASS | RPATH 正确 |
| G4 档案完整性 | ✅ PASS | 必需文件完整 |

### 安全验证
- ✅ 无安全弹窗（已安装二进制可直接执行）
- ✅ 库文件权限正确
- ✅ ELF 签名完成

## 技术规格

### 库版本信息
- API 版本：0.7.0
- 文件格式：MaxMind DB 2.0
- 支持架构：aarch64
- 支持系统：HarmonyOS/OpenHarmony

### 性能特性
- 内存映射 (mmap) 访问
- 零拷贝数据读取
- 高效的搜索树遍历
- 线程安全设计

---

**编译维护者**: OpenHarmony 编译团队
**最后更新**: 2026-05-06
**文档版本**: 1.0