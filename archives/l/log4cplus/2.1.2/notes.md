# 适配笔记 — log4cplus 2.1.2 (C++ 日志库)

## 2026-07-27 适配

### 库信息
- **软件**: log4cplus
- **版本**: 2.1.2
- **构建系统**: CMake (>= 3.12)
- **许可证**: Apache-2.0 AND BSD-2-Clause
- **上游**: https://github.com/log4cplus/log4cplus
- **功能**: 线程安全 C++ 日志 API，支持多种日志输出方式（文件、控制台、syslog 等）

### 构建说明
- `cmake` 标准构建流程
- 启用 LOG4CPLUS_BUILD_TESTING（构建并运行上游测试套件，16 套件 / 206 断言，build() 中 cmake.test() 实际运行）
- 禁用 LOG4CPLUS_BUILD_LOGGINGSERVER（不需要日志服务器）
- C++ 标准: C++11

### 依赖
- **运行时**: 零外部依赖（仅系统 pthreads）
- **构建时**: cmake + clang

### 本地验证记录
| 检查项 | 结果 |
|--------|------|
| conan create | 待验证 |
