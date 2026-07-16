# llhttp for OpenHarmony (HarmonyOS)

llhttp 是 http_parser 到 llparse 的移植，用于高性能 HTTP 请求/响应解析。本修改为 llhttp 添加了 OpenHarmony（鸿蒙系统）支持。llhttp 使用 CMake 构建系统，在鸿蒙系统上编译无障碍，无需源码修改。

## 代码准备

- 下载代码使用官方代码下载
  ```bash
  wget https://github.com/nodejs/llhttp/archive/refs/tags/release/v9.3.1.tar.gz
  tar -xzf llhttp-release-v9.3.1.tar.gz
  cd llhttp-release-v9.3.1
  ```

- 无需应用补丁（源码与鸿蒙系统兼容）

## 修改内容介绍

### 无需补丁

llhttp 9.3.1 源码与 OpenHarmony 系统完全兼容，不需要任何源码修改。编译过程中遇到的平台问题均可通过忽略或调整解决：

- **cmake 平台识别警告**：忽略即可，不影响功能
- **HMDFS fifo 权限问题**：make 自动降级处理
- **SSL 证书下载问题**：使用 SSL context bypass

## 使用方法

### 方法1：使用环境变量别名（推荐）✨

```bash
mkdir build && cd build
cmake -DCMAKE_INSTALL_PREFIX=$HOME/usr/local \
      -DCMAKE_BUILD_TYPE=Release \
      ..
make -j$(nproc)
make install
```

### 方法2：简化编译

```bash
mkdir build && cd build
cmake ..
make
make install
```

## 编译环境要求

### 必需工具
- CMake >= 3.10
- Clang 编译器
- Make

通过应用市场下载 DevBox 安装以上工具链。

### 环境变量

鸿蒙系统修改 `~/.zshrc` 或对应的解释器配置文件：

```bash
export DEFAULT_PREFIX=$HOME/usr/local

export PATH=$PATH:$HOME/npm/bin:$HOME/.local/bin:$DEFAULT_PREFIX/bin
export LIBRARY_PATH=$DEFAULT_PREFIX/lib:$LIBRARY_PATH
export LD_LIBRARY_PATH=$DEFAULT_PREFIX/lib:$LD_LIBRARY_PATH

export C_INCLUDE_PATH=$DEFAULT_PREFIX/include:$C_INCLUDE_PATH
export CPLUS_INCLUDE_PATH=$DEFAULT_PREFIX/include:$CPLUS_INCLUDE_PATH

alias cmake='cmake -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX'

export CC="clang"
export CXX="clang++"
```

### 无外部依赖

llhttp 是独立的 HTTP 解析库，不依赖外部库。

## 支持的功能

### ✅ 已支持
- HTTP 请求解析（GET/POST/PUT/DELETE/HEAD/OPTIONS）
- HTTP 响应解析
- Headers 解析
- Chunked encoding 支持
- 流式处理
- 错误处理机制
- HTTP 方法识别
- URL 解析
- 版本信息 API

### ⚠️ 注意事项

- 无内置测试套件，需编写独立测试程序
- cmake 平台识别警告可忽略
- HMDFS 文件系统不支持 fifo，make jobserver 自动降级

## 版本特性

### 9.3.1 特性
- 高性能 HTTP 解析器
- 支持所有标准 HTTP 方法
- Chunked transfer encoding
- 流式 API 设计
- 低内存占用
- 错误报告机制

## 故障排除

### 问题1：cmake 平台识别警告
```
CMake Warning: Platform "HarmonyOS" not recognized
```
忽略即可，不影响编译和功能。

### 问题2：找不到库文件
```bash
export LD_LIBRARY_PATH=$HOME/usr/local/lib:$LD_LIBRARY_PATH
```

### 问题3：SSL 证书下载失败
如遇到 SSL 证书问题，使用 SSL context bypass 或手动下载。

### 问题4：fifo 权限错误
```
make: warning: jobserver unavailable: using -j1
```
这是 HMDFS 文件系统限制，make 自动降级为单线程编译，不影响结果。

## 文件清单

```
llhttp-release-v9.3.1/
├── include/
│   └── llhttp.h           # API 头文件
├── lib/
│   ├── libllhttp.so       # 共享库
│   ├── pkgconfig/
│   │   └── libllhttp.pc   # pkg-config 文件
│   └── cmake/
│   │   └── llhttp/
│   │       └── llhttp-config.cmake
└── src/
    └── llhttp.c           # 源码（已编译进库）
```

无补丁文件（源码无需修改）

## 技术细节

### 库大小
- libllhttp.so：约 78KB
- llhttp.h：约 30KB

### CMake 配置选项

默认选项即可完成编译：
- `CMAKE_BUILD_TYPE=Release`：优化构建
- `CMAKE_INSTALL_PREFIX`：安装路径

### API 使用模式

llhttp 提供流式解析 API：
1. 创建解析器实例
2. 设置回调函数
3. 输入数据流
4. 解析并触发回调

## 验证编译结果

```bash
# 检查安装的文件
ls -lh $HOME/usr/local/lib/libllhttp*
ls -lh $HOME/usr/local/include/llhttp.h

# 检查 pkg-config
cat $HOME/usr/local/lib/pkgconfig/libllhttp.pc

# 编写测试程序
cat > test_llhttp.c << 'EOF'
#include <stdio.h>
#include <llhttp.h>

int on_method(llhttp_t* parser, const char* at, size_t length) {
    printf("Method: %.*s\n", (int)length, at);
    return 0;
}

int on_url(llhttp_t* parser, const char* at, size_t length) {
    printf("URL: %.*s\n", (int)length, at);
    return 0;
}

int on_header_field(llhttp_t* parser, const char* at, size_t length) {
    printf("Header field: %.*s\n", (int)length, at);
    return 0;
}

int on_header_value(llhttp_t* parser, const char* at, size_t length) {
    printf("Header value: %.*s\n", (int)length, at);
    return 0;
}

int on_body(llhttp_t* parser, const char* at, size_t length) {
    printf("Body: %.*s\n", (int)length, at);
    return 0;
}

int main() {
    llhttp_t parser;
    llhttp_settings_t settings;
    
    llhttp_settings_init(&settings);
    settings.on_method = on_method;
    settings.on_url = on_url;
    settings.on_header_field = on_header_field;
    settings.on_header_value = on_header_value;
    settings.on_body = on_body;
    
    llhttp_init(&parser, HTTP_REQUEST, &settings);
    
    const char* request = "GET /index.html HTTP/1.1\r\n"
                          "Host: example.com\r\n"
                          "Connection: keep-alive\r\n"
                          "\r\n";
    
    llhttp_execute(&parser, request, strlen(request));
    
    printf("Parse complete!\n");
    return 0;
}
EOF

clang -I$HOME/usr/local/include test_llhttp.c \
    -L$HOME/usr/local/lib -lllhttp -o test_llhttp
./test_llhttp
```

预期输出：
```
Method: GET
URL: /index.html
Header field: Host
Header value: example.com
Header field: Connection
Header value: keep-alive
Parse complete!
```

## 测试结果摘要

test_package 通过率：**100%**（21/21 断言，容器 `conan create` + test_package 真实运行）

测试覆盖（`test_package/test.c`）：
- GET 基础解析（`llhttp_execute` + 回调触发）：7 项
- PATCH 方法识别（`on_method` / `llhttp_get_method` / `llhttp_method_name`）：5 项
- 错误原因获取（`llhttp_execute` 报错 / `llhttp_get_errno` / `llhttp_get_error_reason`）：4 项
- pause/resume 状态（`HPE_PAUSED` / `llhttp_resume` / 多轮续解析）：5 项

> 备注：早期设备端临时测试（2026-04-20）曾跑 25 个用例得 88%，标注 PATCH 方法识别、
> pause 状态处理、error reason 获取 3 项失败。经核实，这 3 项均为 llhttp 9.3.1 原生支持
> 的功能（见 `include/llhttp.h`：`HTTP_PATCH=28`、`llhttp_pause`/`llhttp_resume`、
> `llhttp_get_error_reason`），当时失败源自临时测试程序的用法/断言问题，已在 test_package
> 补充针对性用例并全部验证通过。

## 参考资料

- llhttp 官方仓库：https://github.com/nodejs/llhttp
- Node.js 项目：https://nodejs.org
- OpenHarmony 官方网站：https://www.openharmony.cn/
- HarmonyOS 开发者文档：https://developer.huawei.com/consumer/cn/doc/
- OpenHarmony PC Developer gitcode社区：https://gitcode.com/OpenHarmonyPCDeveloper

## 许可证

llhttp 使用 MIT 许可证。