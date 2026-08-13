# E256 — OHOS getpwuid() 返回 NULL 导致 homedir() 为 NULL，程序启动 SIGSEGV

## 错误特征
```
Signal 11 (core dumped)
ros --version: SIGSEGV
```

## 触发条件
- 构建系统: autotools（任意构建系统均可能）
- 阶段: runtime（程序启动时解析用户主目录）

## 根因分析
OHOS 系统无 /etc/passwd 条目，`getpwuid()`/`getpwnam()` 返回 NULL。
依赖 `homedir()` 的软件（如 roswell 的 configdir()）在返回 NULL 后对 NULL 做
字符串拼接，直接 SIGSEGV（Signal 11）。非 E051 的 SIGSYS 问题。

## 解决方案

### 推荐方案
运行时设置软件官方支持的环境变量（如 `ROSWELL_HOME`）注入绝对路径；
或在源码中用 `#ifdef __OHOS__` 守卫在 homedir() 为 NULL 时回退到固定路径。

### 禁止做法
- ❌ 依赖 /etc/passwd 或 getpwuid 返回值非空（OHOS 上恒为 NULL）
