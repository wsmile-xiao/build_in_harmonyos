# libmicrohttpd

GNU libmicrohttpd 是一个小型的 C 库，用于将 HTTP 服务器功能嵌入到应用程序中。

## 软件简介

libmicrohttpd（GNU Micro HTTPD）是一个轻量级的 HTTP 服务器库，设计用于作为其他应用程序的组件运行。它提供完整的 HTTP 1.1 服务器功能，支持 GET、POST、PUT、DELETE 等方法，以及 HTTPS 加密传输（可选）。

**主要特点**：
- 轻量级：库大小小，易于嵌入
- API 简洁：只需几个函数即可实现 HTTP 服务器
- 线程安全：支持多线程和线程池模式
- 支持 HTTP/1.1：包括持久连接、分块传输编码
- 可选 HTTPS：支持 SSL/TLS 加密
- 跨平台：支持 Linux、Windows、macOS 等

## 功能说明

### 核心功能
- **HTTP 服务器**：提供完整的 HTTP 1.1 服务器实现
- **请求处理**：支持 GET、POST、PUT、DELETE、HEAD 等方法
- **响应生成**：支持动态生成响应内容和静态文件服务
- **连接管理**：支持持久连接（keep-alive）和连接超时
- **认证支持**：支持基本认证（Basic Authentication）和摘要认证（Digest Authentication）
- **POST 数据处理**：支持表单数据和文件上传

### 高级功能
- **线程池模式**：使用线程池处理并发请求
- **外部选择模式**：允许应用程序控制事件循环
- **升级支持**：支持 HTTP 协议升级（WebSocket）
- **IPv6 支持**：支持 IPv6 地址和双栈模式

## 编译说明

### 构建系统
libmicrohttpd 使用 GNU Autotools 构建系统。

### 编译依赖
- clang 编译器
- GNU make
- autotools（autoconf、automake、libtool）

### 编译选项
本归档使用以下配置：
- `--disable-shared --enable-static`：仅编译静态库
- `--prefix=/path/to/install`：指定安装路径

### 平台适配
libmicrohttpd 在 HarmonyOS 上需要以下平台适配：
- **umask 修复**：修改 configure 中的 umask 077 → 022（HMDFS 兼容）
- **config.guess/config.sub**：添加 ohos 平台识别
- **静态库编译**：禁用共享库以避免 libtool + HMDFS 权限问题

### 编译产物
- `libmicrohttpd.a`：静态库
- `microhttpd.h`：头文件
- `libmicrohttpd.pc`：pkg-config 文件

## 使用说明

### 安装
从预编译包安装：
```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- libmicrohttpd 1.0.5
```

### 链接静态库
编译时链接 libmicrohttpd：
```bash
clang -o myapp myapp.c -lmicrohttpd -lpthread
```

或使用 pkg-config：
```bash
clang -o myapp myapp.c $(pkg-config --cflags --libs libmicrohttpd)
```

### 基本用法示例
```c
#include <microhttpd.h>

int answer_to_connection(void *cls, struct MHD_Connection *connection,
                         const char *url, const char *method,
                         const char *version, const char *upload_data,
                         size_t *upload_data_size, void **con_cls) {
    const char *page = "<html><body>Hello, world!</body></html>";
    struct MHD_Response *response;
    int ret;
    
    response = MHD_create_response_from_buffer(strlen(page), (void*)page,
                                               MHD_RESPMEM_PERSISTENT);
    ret = MHD_queue_response(connection, MHD_HTTP_OK, response);
    MHD_destroy_response(response);
    return ret;
}

int main() {
    struct MHD_Daemon *daemon;
    
    daemon = MHD_start_daemon(MHD_USE_THREAD_PER_CONNECTION, 8888,
                              NULL, NULL, &answer_to_connection, NULL,
                              MHD_OPTION_END);
    if (daemon == NULL) return 1;
    
    getchar(); // Press enter to stop
    
    MHD_stop_daemon(daemon);
    return 0;
}
```

### HTTPS 示例
启用 HTTPS 需要额外的证书文件：
```c
daemon = MHD_start_daemon(MHD_USE_THREAD_PER_CONNECTION | MHD_USE_SSL, 443,
                          NULL, NULL, &answer_to_connection, NULL,
                          MHD_OPTION_HTTPS_MEM_KEY, key_pem,
                          MHD_OPTION_HTTPS_MEM_CERT, cert_pem,
                          MHD_OPTION_END);
```

## 版本列表

| 版本 | 状态 | 编译日期 | 说明 |
|------|------|---------|------|
| 1.0.5 | built | 2026-05-30 | 静态库，支持 HarmonyOS |

## 项目信息

- **官方网站**：https://www.gnu.org/software/libmicrohttpd/
- **源码仓库**：https://git.gnunet.org/libmicrohttpd.git
- **许可证**：LGPL v2.1 或更高版本
- **维护者**：GNU Project

## 参考资料

- [GNU libmicrohttpd Manual](https://www.gnu.org/software/libmicrohttpd/manual/)
- [libmicrohttpd Tutorial](https://www.gnu.org/software/libmicrohttpd/tutorial.html)
- [GNU Project](https://www.gnu.org/)