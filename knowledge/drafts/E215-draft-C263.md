# E215 — OHOS 沙箱 setsockopt(SO_PRIORITY) 返回 EPERM 被误判为致命错误

## 错误特征
```
bluetoothd[26878]: android/avdtp.c:set_priority() setsockopt(SO_PRIORITY): Operation not permitted (1)
ERROR:unit/test-avdtp.c:243:context_new: assertion failed: (context->session != NULL)
```

## 触发条件
- 构建系统: 任意（运行期问题，测试阶段暴露）
- 阶段: testing/runtime（运行期 socket 操作）
- 平台: OHOS 沙箱（无 CAP_NET_ADMIN）

## 根因分析
OHOS 沙箱环境无 CAP_NET_ADMIN 权限，`setsockopt(SOL_SOCKET, SO_PRIORITY)` 返回 EPERM。若代码将 SO_PRIORITY 设置失败视为致命错误（返回失败并中止会话/连接建立），会导致功能不可用或测试失败。优先级设置本质是尽力而为的优化，不应阻断主流程。

## 解决方案

### 推荐方案
对 EPERM/EACCES 与 ENOTSOCK 同等对待，视为尽力而为（不致命）：
```c
err = setsockopt(fd, SOL_SOCKET, SO_PRIORITY, &priority, sizeof(priority));
if (err == 0 || errno == ENOTSOCK)
    return 0;
if (errno == EPERM || errno == EACCES)  /* OHOS 沙箱无 CAP_NET_ADMIN */
    return 0;
```

### 禁止做法
- ❌ 将 EPERM 视为致命错误中止会话
- ❌ 空壳 stub（`#ifdef __OHOS__` 空分支）

## 验证
```bash
./unit/test-avdtp   # 修复后 62/62 全部通过
```

## 关联条目
- 相关: E051（未实现 syscall/权限受限类）
