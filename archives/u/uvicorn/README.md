# uvicorn

## 软件描述

Uvicorn 是一个基于 ASGI（异步服务器网关接口）标准的闪电般快速的 Python Web 服务器。它专为异步 Python Web 框架设计，支持 HTTP/1.1 和 WebSocket。

## 特性

- ⚡ 高性能：基于 uvloop 和 httptools 的异步实现
- 🔌 ASGI 标准：兼容所有 ASGI 框架（FastAPI, Starlette, Quart 等）
- 🔄 WebSocket 支持：完整的 WebSocket 协议实现
- 🚀 热重载：开发环境下的自动重载功能
- 🎯 生产就绪：支持多进程、信号处理等生产特性

## 版本历史

| 版本 | 状态 | 编译日期 | 说明 |
|------|------|---------|------|
| 0.49.0 | built | 2026-06-08 | 最新版本，支持 Python 3.10-3.14 |

## 使用方式

### 安装

推荐从 PyPI 直接安装：

```bash
# 基础安装
pip install uvicorn

# 或安装性能优化版本（推荐）
pip install uvicorn[standard]
```

### 运行

```bash
# 直接运行 ASGI 应用
uvicorn app:main

# 或使用 Python 模块方式
python -m uvicorn app:main

# 开发模式（自动重载）
uvicorn app:main --reload

# 生产模式（多进程）
uvicorn app:main --workers 4
```

## 鸿蒙适配说明

### 兼容性

✅ **完全兼容**

- Python 包无需源码修改即可在鸿蒙上构建和使用
- 自动识别 HarmonyOS 平台
- 支持所有标准功能

### 安装建议

1. **推荐方式**：直接从 PyPI 安装
   ```bash
   pip install uvicorn[standard]
   ```

2. **手动安装**：使用预编译 wheel 包
   ```bash
   pip install uvicorn-0.49.0-py3-none-any.whl
   ```

### 依赖

#### 核心依赖（必需）
- click >=7.0
- h11 >=0.8
- typing_extensions >=4.0 (Python <3.11)

#### 可选依赖（standard extras）
- httptools >=0.8.0 - HTTP 解析器（性能优化）
- uvloop >=0.15.1 - 事件循环（性能优化）
- watchfiles >=0.20 - 文件监控（热重载）
- websockets >=10.4 - WebSocket 支持
- PyYAML >=5.1 - YAML 配置
- python-dotenv >=0.13 - 环境变量文件

## 注意事项

1. **启动脚本路径**：如果使用 bin/uvicorn，可能需要调整 Python 路径
   - 推荐使用 `python -m uvicorn` 方式运行

2. **性能优化**：安装 uvicorn[standard] 可获得最佳性能
   - uvloop 替代 asyncio，性能提升显著
   - httptools 比 h11 更快的 HTTP 解析

3. **与 Gunicorn 配合**：生产环境推荐使用 Gunicorn + Uvicorn workers
   ```bash
   gunicorn app:main -w 4 -k uvicorn.workers.UvicornWorker
   ```

## 文档与资源

- 官方文档：https://uvicorn.dev
- GitHub：https://github.com/Kludex/uvicorn
- PyPI：https://pypi.org/project/uvicorn/

## 许可证

BSD-3-Clause