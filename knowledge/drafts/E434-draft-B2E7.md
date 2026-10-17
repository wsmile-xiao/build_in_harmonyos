# E434 — 上游硬编码 /tmp 临时目录，broker.backend 在鸿蒙只读 /tmp 下失败

## 错误特征
broker.backend 测试进程向 stderr 输出后退出：
```
Unable to create unique filename: Read-only file system.
```
ctest 显示 broker.backend FAILED；同一构建在 /tmp 可写的主机上通过。

## 触发条件
- 构建系统: cmake（zeek 8.2.1 / auxil-broker）
- 阶段: testing（R51 上游测试实测，ctest）

## 根因分析
auxil/broker/libbroker/broker/detail/filesystem.cc 的 `make_temp_file_name()` 硬编码
`char fname[] = "/tmp/broker.test.XXXXXX"`。鸿蒙 PC 上 /tmp 为只读 HMDFS 挂载，
mkstemp 返回 EROFS。
与 E002（平台 /tmp 只读）的关系：E002 是纯平台侧现象；本条是"源码硬编码 /tmp"×
"平台 /tmp 只读"双因素碰撞——仅 export TMPDIR 无效（源码不读取 TMPDIR）。

## 解决方案

### 推荐方案
将 /tmp 字面量替换为 `::getenv("TMPDIR")`（为空回退 /tmp）+ snprintf(512)；
测试时 export TMPDIR=<可写目录>。纯测试辅助路径（make_temp_file_name 仅用于测试
临时文件），生产运行零影响。zeek 8.2.1 实测 broker.* 25/26 → 26/26（100%）。

### 禁止做法
- ❌ 回退 /tmp 硬编码（补丁回滚）→ 只读 /tmp 环境必失败
- ❌ 只 export TMPDIR 不改源码 → 无效（源码不读取）

## 验证
```bash
grep -n '"/tmp' auxil/broker/libbroker/broker/detail/filesystem.cc  # 无输出=已修复
TMPDIR=<可写目录> ctest -R 'broker\.'   # 期望 26/26
```

## 关联条目
- 相关: E002（平台 /tmp 只读）
