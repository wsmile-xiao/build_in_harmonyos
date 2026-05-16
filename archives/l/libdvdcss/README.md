# libdvdcss 1.5.0 — OpenHarmony aarch64 编译记录

---

## 基本信息

| 项目 | 详情 |
|------|------|
| **软件名称** | libdvdcss |
| **版本** | 1.5.0 |
| **构建系统** | Meson 1.11.0 + Ninja 1.11.1 |
| **编译器** | Clang 15.0.4 |
| **目标平台** | OpenHarmony aarch64 |
| **编译日期** | 2026-05-11 ~ 2026-05-15 |
| **编译状态** | ✅ 成功 |
| **许可证** | GNU General Public License (GPL) |

---

## 编译输出

### 主要产物

| 文件名 | 类型 | 大小 | 说明 |
|--------|------|------|------|
| libdvdcss-1.5.0-ohos-aarch64.tar.gz | 主安装包 | 497KB | 包含动态库、静态库、头文件、文档 |
| libdvdcss-1.5.0-ohos-aarch64-debug.tar.gz | 调试符号包 | 342KB | 包含调试符号文件 |
| install-libdvdcss-1.5.0.sh | 安装脚本 | 1.4KB | 自动化安装脚本 |

### 库文件

| 文件 | 类型 | 大小 | 说明 |
|------|------|------|------|
| libdvdcss.so.2.3.0 | 动态库 | 83KB | 主动态库文件 |
| libdvdcss.so.2 | 符号链接 | - | soname链接 |
| libdvdcss.so | 符号链接 | - | 开发链接 |
| libdvdcss.a | 静态库 | 206KB | 静态库文件 |

### 头文件

| 文件 | 说明 |
|------|------|
| dvdcss/dvdcss.h | 主API头文件（函数声明、类型定义、常量） |
| dvdcss/dvdcpxm.h | CPXM扩展API头文件 |
| dvdcss/version.h | 版本信息头文件 |

### 配置文件

| 文件 | 说明 |
|------|------|
| lib/pkgconfig/libdvdcss.pc | pkg-config配置文件 |

### 文档文件

| 文件 | 说明 |
|------|------|
| AUTHORS | 作者列表 |
| COPYING | GPL许可证文件 |
| NEWS | 更新日志 |
| README.md | 说明文档 |

---

## 编译指导

### 系统要求

- **构建工具**: Meson >= 0.60.0, Ninja >= 1.8.0
- **编译器**: Clang >= 15.0 或 GCC >= 10.0
- **其他**: pkg-config >= 0.29
- **依赖**: 无外部依赖

### 编译步骤

#### 1. 环境准备
```bash
# 安装Meson和Ninja
pip install meson ninja

# 设置环境变量
export PATH="$HOME/.local/bin:$PATH"
```

#### 2. 解压源码
```bash
tar -xJf libdvdcss-1.5.0.tar.xz
cd libdvdcss-1.5.0
```

#### 3. 配置
```bash
meson setup build --prefix=/usr/local
```

**配置选项说明**:
- `--prefix` - 安装路径
- `buildtype=debugoptimized` - 优化调试构建
- `default_library=both` - 同时构建动态和静态库
- `c_std=c17` - 使用C17标准

#### 4. 编译
```bash
meson compile -C build
```

#### 5. 安装
```bash
meson install -C build
```

#### 6. 打包（可选）
```bash
meson install -C build --destdir=./package
tar -czf libdvdcss-1.5.0-ohos-aarch64.tar.gz -C ./package .
```

---

## 补丁清单

**本次编译无补丁**

源码包无需修改即可成功编译。

---

## 已知限制

### 1. DVD设备依赖
- 完整功能测试需要实际DVD设备
- 在无DVD设备的系统中只能进行API验证测试

### 2. 许可证限制
- 使用GPL许可证，需遵守相关条款
- 商业应用需注意许可证兼容性

### 3. 平台特性
- Linux/OpenHarmony: 支持标准DVD ioctl
- 需要内核支持DVD设备驱动

### 4. 权限要求
- 访问DVD设备需要适当权限
- 通常需要root或特定用户组权限

---

## 功能验证

### 验证方法

#### 1. 库文件验证
```bash
# 检查库文件
ls -l /usr/local/lib/libdvdcss.*

# 检查文件类型
file /usr/local/lib/libdvdcss.so.2.3.0
# 输出: ELF 64-bit LSB shared object, ARM aarch64

file /usr/local/lib/libdvdcss.a
# 输出: current ar archive
```

#### 2. 符号验证
```bash
# 检查导出符号
nm -D /usr/local/lib/libdvdcss.so.2.3.0 | grep dvdcss_
# 应显示: dvdcss_open, dvdcss_close, dvdcss_read等
```

#### 3. API功能测试

**测试程序示例**:
```c
#include <stdio.h>
#include <dvdcss/dvdcss.h>

int main() {
    printf("libdvdcss version: %s\n", DVDCSS_VERSION_STRING);
    
    // 测试NULL输入处理
    dvdcss_t h = dvdcss_open(NULL);
    if (h == NULL) {
        printf("PASS: dvdcss_open(NULL) returns NULL\n");
    }
    
    return 0;
}
```

**编译并运行**:
```bash
gcc -o test test.c -ldvdcss
./test
```

#### 4. pkg-config验证
```bash
# 设置路径
export PKG_CONFIG_PATH=/usr/local/lib/pkgconfig:$PKG_CONFIG_PATH

# 检查配置
pkg-config --modversion libdvdcss
# 输出: 1.5.0

pkg-config --cflags libdvdcss
# 输出: -I/usr/local/include

pkg-config --libs libdvdcss
# 输出: -L/usr/local/lib -ldvdcss
```

### 测试结果

| 测试项 | 结果 |
|--------|------|
| 库文件完整性 | ✅ PASS |
| 符号解析 | ✅ PASS (8个核心符号) |
| API函数调用 | ✅ PASS (7个函数测试) |
| NULL参数安全处理 | ✅ PASS |
| 错误返回值验证 | ✅ PASS |
| 版本常量验证 | ✅ PASS |
| 常量值验证 | ✅ PASS |

---

## 使用示例

### 基本使用

```c
#include <dvdcss/dvdcss.h>
#include <stdio.h>

int main() {
    // 打开DVD设备
    dvdcss_t dvd = dvdcss_open("/dev/dvd");
    if (!dvd) {
        printf("Error: %s\n", dvdcss_error(NULL));
        return 1;
    }
    
    // 定位到特定块
    dvdcss_seek(dvd, 0, DVDCSS_NOFLAGS);
    
    // 读取数据（自动解密）
    char buffer[DVDCSS_BLOCK_SIZE];
    int blocks_read = dvdcss_read(dvd, buffer, 1, DVDCSS_READ_DECRYPT);
    
    if (blocks_read > 0) {
        printf("Successfully read %d blocks\n", blocks_read);
    }
    
    // 检查是否加密
    if (dvdcss_is_scrambled(dvd)) {
        printf("DVD is encrypted, decryption enabled\n");
    }
    
    // 关闭设备
    dvdcss_close(dvd);
    
    return 0;
}
```

### 编译链接

```bash
# 动态链接
gcc myapp.c -ldvdcss

# 静态链接
gcc myapp.c /usr/local/lib/libdvdcss.a

# 使用pkg-config
gcc myapp.c $(pkg-config --cflags --libs libdvdcss)
```

---

## API参考

### 核心函数

#### dvdcss_open
```c
dvdcss_t dvdcss_open(const char *psz_target);
```
打开DVD设备或文件，返回句柄。

#### dvdcss_close
```c
int dvdcss_close(dvdcss_t dvdcss);
```
关闭DVD设备并释放资源。

#### dvdcss_read
```c
int dvdcss_read(dvdcss_t dvdcss, void *p_buffer, int i_blocks, int i_flags);
```
读取DVD数据块，可选择是否解密。

#### dvdcss_seek
```c
int dvdcss_seek(dvdcss_t dvdcss, int i_blocks, int i_flags);
```
定位到指定块位置。

#### dvdcss_error
```c
const char *dvdcss_error(const dvdcss_t dvdcss);
```
获取最后一次操作的错误信息。

#### dvdcss_is_scrambled
```c
int dvdcss_is_scrambled(dvdcss_t dvdcss);
```
检查DVD是否加密。

### 常量定义

| 常量 | 值 | 说明 |
|------|----|----|
| DVDCSS_BLOCK_SIZE | 2048 | DVD块大小（字节） |
| DVDCSS_NOFLAGS | 0 | 无标志 |
| DVDCSS_READ_DECRYPT | 1 | 解密读取标志 |
| DVDCSS_SEEK_MPEG | 1 | MPEG定位标志 |
| DVDCSS_SEEK_KEY | 2 | 密钥检查标志 |

---

## 安装指南

### 方法1: 使用安装脚本
```bash
tar -xzf libdvdcss-1.5.0-ohos-aarch64.tar.gz
cd libdvdcss-1.5.0
./install-libdvdcss-1.5.0.sh
```

### 方法2: 手动安装
```bash
tar -xzf libdvdcss-1.5.0-ohos-aarch64.tar.gz
cp -r libdvdcss-1.5.0/* /usr/local/
ldconfig
```

### 方法3: 使用打包目录直接安装
```bash
cd packaging/pkg-libdvdcss-1.5.0
cp -r lib/* /usr/local/lib/
cp -r include/* /usr/local/include/
cp -r share/* /usr/local/share/
ldconfig
```

---

## 相关文档

| 文档 | 说明 |
|------|------|
| manifest.yaml | 编译清单文件 |
| PROGRESS.md | 编译进度记录 |
| RELEASENOTE.md | 发布说明 |
| SUMMARY.md | 编译总结 |
| KNOWLEDGE.md | 知识整理文档 |
| reports/test-report.md | 详细测试报告 |
| reports/quality-report.md | 质量检查报告 |
| logs/build.log | 构建日志 |
| scripts/test-libdvdcss.sh | 自动化测试脚本 |

---

## 质量检查

| 检查项 | 结果 |
|--------|------|
| G1: 二进制完整性 | ✅ PASS - 无缺失符号 |
| G2: 功能可用性 | ✅ PASS - API可调用 |
| G3: 可移植性 | ✅ PASS - 符合标准 |
| G4: 档案完整性 | ✅ PASS - 文件完整 |

---

## 资源链接

- **官方网站**: https://www.videolan.org/developers/libdvdcss.html
- **源码仓库**: https://code.videolan.org/videolan/libdvdcss
- **相关库**: libdvdread, libdvdnav
- **构建系统**: https://mesonbuild.com/

---

## 归档信息

**归档路径**: 
```
/storage/Users/currentUser/.opendesk/apps/skills/resources/openharmony-compile-agent/archives/l/libdvdcss/1.5.0/
```

**归档时间**: 2026-05-15

---

**文档版本**: 1.0  
**生成时间**: 2026-05-15  
**状态**: 完成