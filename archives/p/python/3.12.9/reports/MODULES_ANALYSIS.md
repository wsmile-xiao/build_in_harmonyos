# Python 3.12.9 Modules/ C 扩展 + Include/ 头文件分析报告

> **日期**: 2026-03-27 | **基于**: 子任务 task_mn8bfopc_l09s

---

## 核心发现

- **整个 3.12.9 源码树中 `__OHOS__` 出现次数：0**
- **Modules/_posixsubprocess.c 仍然存在**（1251行），未内联

## C 扩展模块对比（3.9 → 3.12 新增/移除）

| 状态 | 模块 | 说明 |
|------|------|------|
| 新增 | _zoneinfo.c | IANA 时区数据库 |
| 新增 | _hacl/ | HACL* 哈希库（SHA2/3/BLAKE2/MD5/SHA1） |
| 新增 | _uuidmodule.c | 内置 UUID |
| 新增 | _typingmodule.c | C 加速 typing |
| 新增 | _xxinterpchannelsmodule.c | 子解释器通道 |
| 合并 | sha2module.c | 原 _sha256/_sha512 合并 |
| 重构 | _blake2/ | 独立子目录 |
| 移动 | Programs/python.c | main() 从 Modules/main.c 迁移 |

## 鸿蒙适配需求矩阵（按优先级）

### 🔴 P0 必须适配
| 文件 | 需求 | 说明 |
|------|------|------|
| Modules/_posixsubprocess.c | FD_DIR → /dev/fd | 行63-66，鸿蒙无 /proc |
| Modules/timemodule.c | musl tm_zone 条件 | 行613/665/2116，`__linux__ && !__GLIBC__` 需扩展 |
| Python/thread_pthread.h | get_thread_native_id | 行326-352，需新增 `__OHOS__` gettid() 分支 |
| Modules/posixmodule.c | cpu_count 回退 | 行7609，鸿蒙无 /proc/self/stat |
| Modules/_ctypes/malloc_closure.c | RWX mmap | 行71，鸿蒙 W^X 限制 |

### 🟡 P1 重要
| 文件 | 需求 | 说明 |
|------|------|------|
| Python/pylifecycle.c | is_valid_fd | 行2333-2360，添加 `__OHOS__` 到 F_GETFD 条件 |
| Modules/posixmodule.c | sendfile | 行11072，评估鸿蒙是否支持 |
| Modules/_posixsubprocess.c | VFORK_USABLE | 行44，排除 `__OHOS__` |

### ⚪ 无需适配（条件编译自动排除）
pidfd_open, pidfd_send_signal, getrandom, memfd_create, splice, setns, unshare, CLONE_*, AF_UNIX abstract namespace

## 与 3.9 补丁对应关系

| 3.9 补丁 | 3.12 仍需要？ | 说明 |
|-----------|:---:|------|
| 0012 (FD_DIR) | ✅ | _posixsubprocess.c 行63-66 逻辑相同 |
| 0017 (musl tm_zone) | ✅ | timemodule.c 行613/665/2116 条件相同 |
| 0018 (thread native_id) | ✅ | thread_pthread.h 行326-352 分支链相同 |
| 0019 (fd 验证) | 🔄 | pylifecycle.c 结构变化，需简化 |
| 0021 (gettid 实现) | ✅ | thread_pthread.h 仍需新增 |
