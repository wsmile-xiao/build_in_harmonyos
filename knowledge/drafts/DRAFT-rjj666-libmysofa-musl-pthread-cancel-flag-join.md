# DRAFT-rjj666-libmysofa-musl-pthread-cancel-flag-join

## 基本信息
- **严重度**: 2
- **类别**: musl | pthreads | portability | ohos
- **作者**: rjj666

## 错误特征
```
error: use of undeclared identifier 'pthread_cancel'
```

## 根因分析
OHOS musl libc 的 pthread.h 不声明 pthread_cancel（glibc 扩展语义）。
上游 multithread.c 用 pthread_cancel 强杀慢速 worker，OHOS 交叉编译期
直接失败。

## 推荐方案
**方法**: atomic-flag-join-replacement（标志位 + pthread_join 等价替换）

**说明**: worker 循环每轮检查退出标志，主线程置位后 join 回收；
牺牲最长一个工作单元的等待时间，换取可移植性，并规避
pthread_cancel 的取消点不确定性与资源泄漏风险。测试场景完全等价。

## 验证
```bash
# 交叉编译不再报 undeclared identifier；真机 ctest 43/43 全绿
```

## 来源
- 草稿: DRAFT-rjj666-libmysofa-musl-pthread-cancel-flag-join
- 关联: E085, E127, E407, E513
- 提升日期: 待审核
