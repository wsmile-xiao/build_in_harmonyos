# Python 3.9.0 HarmonyOS 适配 — 下一步工作规划

> 日期: 2026-03-30

## 1. 已完成

- Python 3.9.0 核心编译适配（27个核心补丁）
- 官方测试套件全面运行（425/425，85.6%通过）
- C扩展模块编译验证（204个.so，greenlet/brotli/netifaces等pip install验证通过）
- ctypes W^X问题解决（libffi 3.5.2 closure分配修复）
- 预编译可移植包制作与发布
- 完整技术文档和知识库建设
- 51个测试补丁（平台限制跳过、第三方包干扰过滤、HMDFS兼容性适配）

## 2. 鸿蒙内核/系统层面需推动的事项（P0）

### 2.1 HMDFS chmod/umask 语义修正

- **问题**：HMDFS强制group=6、other=0，不遵循POSIX语义
- **影响**：8+ Python测试失败，所有依赖Unix权限位的软件受影响
- **具体表现**：
  - `mkdir('dir', 0o755)` → 实际权限 `0o505`
  - `mkstemp(mode=0o600)` → 实际权限 `0o448`
  - `os.chmod(fd, 0o400)` 后文件仍可写
- **建议**：HMDFS正确实现chmod()语义，至少在ohos native层提供标准行为
- **优先级**：🔴 P0（影响面最广）

### 2.2 内核SIGSYS行为修正

- **问题**：未实现/无权限的syscall发送SIGSYS而非返回EPERM/ENOSYS
- **涉及syscall**：
  - clock_settime() → 应返回EPERM，实际触发SIGSYS
  - process_time()/thread_time() → CLOCK_PROCESS/THREAD_CPUTIME_ID未实现
  - setreuid()/setregid() → 应返回EPERM，实际触发SIGSYS
  - chroot() → 未实现，应返回ENOSYS/EPERM
- **影响**：相关syscall触发后进程直接崩溃，无catch机会
- **建议**：syscall handler应返回错误码，符合POSIX标准
- **优先级**：🔴 P0（进程安全性）

### 2.3 poll()/select() 设备节点行为修正

- **问题**：poll()对/dev/null不报告POLLOUT事件
- **影响**：selectors模块mock测试场景（实际使用不受影响，因为真实pipe fd行为正常）
- **建议**：修正poll()对字符设备的POLLOUT检测
- **优先级**：🟡 P1

### 2.4 /dev/ptmx 访问策略

- **问题**：adhoc_bin域无法访问/dev/ptmx（Hmmac MAC策略EACCES）
- **影响**：PTY功能完全不可用，test_openpty/test_pty/test_asyncio(pty相关)受影响
- **建议**：评估安全风险后开放必要的SELinux策略
- **优先级**：🟡 P1

### 2.5 fstat()管道访问权限

- **问题**：fstat()对管道返回EACCES
- **影响**：toybox等工具受限
- **建议**：SELinux策略调整
- **优先级**：🟡 P1

## 3. Python版本升级路径（P1）

### 3.1 Python 3.9.25 维护版本

- 已有patches（archives/p/python/3.9.25/）
- 基于现有3.9.0补丁扩展，工作量较小
- 建议：作为3.9系列的安全/bugfix维护更新
- 预估工作量：1-2天

### 3.2 Python 3.12.x

- 已有初始patches（archives/p/python/3.12.9/，21个补丁+WORKPLAN）
- distutils已被移除（PEP 632），适配工作更简洁
- 建议：作为主力开发版本推进
- 预估工作量：1-2周（基于3.9.0补丁迁移+新特性适配）

### 3.3 Python 3.13+

- 需要评估free-threaded模式（PEP 703）在鸿蒙上的兼容性
- 建议暂缓，等3.12稳定后再推进

## 4. Python生态建设（P2）

### 4.1 pip/PyPI 包兼容性

- 已有pypi-compat-skill（ohos-python-release feat/pypi-compat-skill分支）
- 建议：建立持续集成测试，自动评估常用包的兼容性
- 重点包：numpy, pandas, requests, django, flask, fastapi
- 预估工作量：1周

### 4.2 包管理优化

- 推动wheel标签标准化（ohos平台tag）
- 考虑建立ohos-specific wheel仓库
- pip的--platform选项支持
- 建议：与PyPI社区协作，参考musllinux标签模式

### 4.3 开发者工具链

- VS Code Python扩展适配
- 调试器适配（基于ptrace的调试需替代方案）
- LSP/linter支持
- 建议：优先保障VS Code + pylsp基本可用

## 5. 技术债务（P2）

### 5.1 补丁上游贡献

已识别可提PR的补丁（manifest.yaml中的phase1_can_pr列表）：

| 补丁 | 文件 | 说明 |
|------|------|------|
| 平台识别 | configure.ac | 新平台支持 |
| 平台字符串 | Lib/sysconfig.py | 运行时平台标识 |
| 平台字符串 | Lib/distutils/util.py | distutils平台标识 |
| symlink回退 | Lib/venv/__init__.py | 通用errno检测 |
| 原生线程ID | Include/pythread.h | PY_HAVE_THREAD_NATIVE_ID |
| spawn默认值 | Lib/multiprocessing/context.py | 动态fork检测 |
| 抽象socket | Lib/multiprocessing/util.py | 平台支持检测 |
| 默认PATH | Lib/posixpath.py | defpath鸿蒙扩展 |
| FD_DIR | Modules/_posixsubprocess.c | /dev/fd路径 |
| musl时区 | Modules/timemodule.c | bpo-34672修复 |
| posix_spawn | Lib/subprocess.py | musl分支+shell检测 |

建议：逐步向CPython上游提交HarmonyOS平台支持，从小修改开始建立社区信任。

### 5.2 测试修复

- 39个失败测试中，~15个可通过平台检测改进修复（locale、format、pathlib等）
- HMDFS权限相关的测试需要平台特定的断言调整
- 时区相关测试可通过安装tzdata修复
- 建议：为鸿蒙平台添加专门的test support模块（类似test.support的ohos扩展）

### 5.3 文档完善

- 将适配经验沉淀为CPython官方文档的贡献
- 编写"Porting Python to HarmonyOS"指南
- 建立鸿蒙Python开发者wiki
- 建议：参考Android/iOS/ WASI的移植文档格式

## 6. 优先级总结

| 优先级 | 事项 | 预估工作量 | 依赖 | 责任方 |
|--------|------|-----------|------|--------|
| P0 | HMDFS chmod/umask修正 | 鸿蒙团队 | 无 | 鸿蒙内核团队 |
| P0 | SIGSYS行为修正 | 鸿蒙团队 | 无 | 鸿蒙内核团队 |
| P1 | /dev/ptmx策略开放 | 鸿蒙安全团队 | 安全评估 | 鸿蒙安全团队 |
| P1 | poll()/select()修正 | 鸿蒙内核团队 | 无 | 鸿蒙内核团队 |
| P1 | Python 3.9.25维护版 | 1-2天 | 3.9.0经验 | 社区 |
| P1 | Python 3.12.x适配 | 1-2周 | 3.9.0补丁迁移 | 社区 |
| P2 | pip包兼容性CI | 1周 | Python编译完成 | 社区 |
| P2 | wheel标签标准化 | 社区推动 | PyPI支持 | 社区+PyPI |
| P2 | 上游PR提交 | 持续 | 无 | 社区 |
| P2 | 开发者工具链 | 2-4周 | VS Code/调试器 | 社区 |
| P2 | 文档完善 | 持续 | 无 | 社区 |

---

> 本文档基于 regrtest v52 测试结果（2026-03-29）和现有补丁集v4（2026-03-29）编写。
> 随着鸿蒙系统更新和Python适配进展，优先级可能调整。
