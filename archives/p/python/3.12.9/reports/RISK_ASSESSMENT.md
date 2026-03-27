# Python 3.12.9 鸿蒙编译风险评估报告

> **日期**: 2026-03-27 | **基于**: 源码全量分析 + 3.9.0 适配经验 + error-patterns.md 50 个已知错误模式

---

## 风险评估矩阵

### 评分标准
- **概率**: 🟢低(10%) / 🟡中(30-50%) / 🔴高(70%+)
- **影响**: 阻塞编译 / 阻塞功能 / 功能受限 / 无影响
- **可检测性**: 容易定位 / 需调试 / 难以发现

---

## 🔴 高风险（概率高 × 影响大）

### R1: configure 阶段平台识别失败
| 项目 | 内容 |
|------|------|
| **阶段** | configure |
| **症状** | `configure: error: cross build not supported for aarch64-unknown-linux-ohos` 或 `cannot guess build type` |
| **根因** | config.guess/config.sub 无 HarmonyOS 支持；configure.ac host case 无 `*-*-ohos*` |
| **已知模式** | E007 |
| **预判** | 🔴 100% 会发生（零 `__OHOS__` 支持代码） |
| **方案** | 补丁 0001(configure.ac) + 0003(config.guess) + 0004(config.sub)，与 3.9 相同策略 |
| **可检测性** | 🟢 极易（configure 第一步就报错） |

### R2: 模块构建系统缺失（setup.py 移除后的影响）
| 项目 | 内容 |
|------|------|
| **阶段** | make |
| **症状** | 扩展模块无法编译，或缺失 SDK sysroot 路径导致头文件/库找不到 |
| **根因** | 3.12 用 PY_STDLIB_MOD 宏替代 setup.py，但 SDK sysroot 搜索逻辑在 3.9 中由 setup.py 实现 |
| **已知模式** | E015 (找不到头文件) |
| **预判** | 🔴 80% 概率，影响所有依赖外部库的扩展模块 |
| **方案** | 需将 SDK sysroot 搜索逻辑迁移到 configure.ac 或 Modules/Setup.stdlib.in |
| **可检测性** | 🟢 易（编译错误直接指向缺失的头文件/库） |

### R3: musl BIND_NOW 扩展模块加载失败
| 项目 | 内容 |
|------|------|
| **阶段** | 运行时 |
| **症状** | `ImportError: symbol not found: _PyType_Name` |
| **根因** | musl 默认 BIND_NOW，扩展模块 NEEDED 缺少 libpython |
| **已知模式** | E004 |
| **预判** | 🔴 90% 概率（与 3.9 完全相同的问题） |
| **方案** | 修改 LDSHARED 添加 `-lpython`，与 3.9 补丁 0001 相同策略。但 3.12 中 LDSHARED 传递机制变化（不再通过 setup.py），需在 Makefile.pre.in 的 sharedmods 目标中确保正确传递 |
| **可检测性** | 🟢 易（扩展模块导入失败立即报错） |

### R4: subprocess 模块不可用
| 项目 | 内容 |
|------|------|
| **阶段** | 运行时 |
| **症状** | `subprocess.run()` 静默失败，`pip install` 不可用 |
| **根因** | SELinux 域转换限制 + 3.12 subprocess 新架构 |
| **已知模式** | E009 |
| **预判** | 🔴 80% 概率（SELinux 限制是平台根本性限制） |
| **方案** | 重写补丁 0016/0020 适配 3.12 的新 `_use_posix_spawn()` 和 `_can_fork_exec` 架构。3.12 已有 `_use_posix_spawn()` 函数，只需添加 musl 返回 True 的分支 |
| **可检测性** | 🟡 中（静默失败不易察觉，需用 SDK 工具作为锚点测试） |

### R5: ctypes CFUNCTYPE 回调 MemoryError
| 项目 | 内容 |
|------|------|
| **阶段** | 运行时 |
| **症状** | `@ctypes.CFUNCTYPE` 回调包装器创建失败，MemoryError |
| **根因** | W^X mmap 策略禁止 RWX 内存映射 |
| **已知模式** | E045 |
| **预判** | 🔴 70% 概率（3.12 中 `malloc_closure.c` 仍使用 RWX mmap） |
| **方案** | 确保 libffi 提供 `ffi_closure_alloc`（configure 自动检测），此函数使用分步 mmap (RW→RX) 避开 W^X。需确认编译的 libffi 是否支持 |
| **可检测性** | 🟡 中（需要实际测试 CFUNCTYPE 回调） |

### R6: HMDFS 符号链接问题
| 项目 | 内容 |
|------|------|
| **阶段** | make install + pip install |
| **症状** | `pip install` 编译 C 扩展时链接器找不到 libpython3.12.so |
| **根因** | HMDFS 不正常跟踪符号链接（E050） |
| **已知模式** | E050 |
| **预判** | 🔴 90% 概率（平台根本性限制） |
| **方案** | make install 后手动将 `.so` 符号链接替换为文件副本（`cp -p`）。3.12 中 distutils 已移除但 setuptools 的 build_ext 可能需要类似处理 |
| **可检测性** | 🟢 易（链接错误直接报错） |

---

## 🟡 中等风险

### R7: configure.ac MACHDEP 检测异常
| 项目 | 内容 |
|------|------|
| **阶段** | configure |
| **症状** | MACHDEP 变为 `harmonyos1.11.0`（含内核版本），导致模块搜索路径错误 |
| **根因** | `uname -s` 返回 `HarmonyOS`，`uname -r` 返回 `HongMeng Kernel 1.11.0` |
| **已知模式** | E036 |
| **预判** | 🟡 50%（取决于 MACHDEP case 分支是否匹配） |
| **方案** | 补丁 0001 添加 `harmonyos*|HarmonyOS*) MACHDEP="ohos"` |
| **可检测性** | 🟢 易 |

### R8: BUILDEXEEXT 误判为 .exe
| 项目 | 内容 |
|------|------|
| **阶段** | configure |
| **症状** | 生成 `python3.12.exe` |
| **已知模式** | E021 |
| **预判** | 🟡 50%（3.9 中遇到过） |
| **方案** | 补丁 0001 中已有对应处理，3.12 中行号变化需重新定位 |
| **可检测性** | 🟢 易 |

### R9: cpu_count() 调用崩溃
| 项目 | 内容 |
|------|------|
| **阶段** | 运行时 |
| **症状** | `os.cpu_count()` 抛异常（读取 `/proc/self/stat` 失败） |
| **根因** | posixmodule.c 行7609：`#ifdef __linux__` 分支读 /proc/self/stat，鸿蒙无 /proc |
| **已知模式** | E031 |
| **预判** | 🟡 60% |
| **方案** | 需新增 3.12 专属补丁：在 cpu_count 中添加 `#elif defined(__OHOS__)` 回退到 `sysconf(_SC_NPROCESSORS_ONLN)` |
| **可检测性** | 🟢 易 |

### R10: timemodule musl 时区处理异常
| 项目 | 内容 |
|------|------|
| **阶段** | 运行时 |
| **症状** | `time.localtime()` 时区显示错误 |
| **根因** | timemodule.c 条件 `__linux__ && !__GLIBC__` 不覆盖 `__OHOS__` |
| **已知模式** | E023 |
| **预判** | 🟡 70% |
| **方案** | 扩展条件为 `(__linux__ \|\| defined(__OHOS__)) && !defined(__GLIBC__)` |
| **可检测性** | 🟢 易 |

### R11: CAN socket 编译失败
| 项目 | 内容 |
|------|------|
| **阶段** | 编译 |
| **症状** | `CAN_RAW_FD_FRAMES undeclared` |
| **已知模式** | E025 |
| **预判** | 🟡 40%（取决于鸿蒙内核头文件） |
| **方案** | configure.ac 中跳过 CAN_RAW 检测（与 3.9 补丁 0001 相同） |
| **可检测性** | 🟢 易 |

### R12: setuptools 不兼容
| 项目 | 内容 |
|------|------|
| **阶段** | pip install |
| **症状** | `pip install` 时 setuptools 编译 C 扩展失败 |
| **根因** | distutils 移除后 setuptools 成为唯一方案，其 build_ext 可能需要鸿蒙适配 |
| **预判** | 🟡 40% |
| **方案** | 需测试验证。如果 setuptools 的 build_ext 有类似 3.9 distutils 的问题，可能需要 setuptools 层面的适配 |
| **可检测性** | 🟡 中 |

### R13: venv lib64 symlink 失败
| 项目 | 内容 |
|------|------|
| **阶段** | 运行时 |
| **症状** | `python3 -m venv` 失败 |
| **已知模式** | E018 |
| **预判** | 🟡 50%（lib64 处仍有裸 symlink 调用） |
| **方案** | 小幅修改：给 venv 行176-181 的 `os.symlink('lib', link_path)` 添加 try/except |
| **可检测性** | 🟢 易 |

---

## 🟢 低风险

| # | 风险 | 预判 | 说明 |
|---|------|------|------|
| R14 | `/tmp` 只读 | 🟢 10% | 已知问题，`export TMPDIR` 解决 |
| R15 | LLVM 工具链路径 | 🟢 10% | 沿用 3.9 环境配置 |
| R16 | OpenSSL 编译 | 🟢 5% | 已有 1.1.1w 静态库 |
| R17 | find_library 崩溃 | 🟢 10% | 3.12 会自然返回空，不会 SubprocessError |
| R18 | multiprocessing /dev/shm | 🟢 5% | 已有 tempdir fallback |
| R19 | pidfd/getrandom/memfd_create | 🟢 0% | 条件编译自动排除 |
| R20 | abstract sockets | 🟢 0% | 条件编译自动排除 |

---

## 风险汇总统计

| 风险等级 | 数量 | 占比 |
|----------|------|------|
| 🔴 高 | 6 | 30% |
| 🟡 中 | 7 | 35% |
| 🟢 低 | 7 | 35% |

## 编译阶段风险分布

```
configure 阶段:  R1(高), R7(中), R8(中), R11(中)  → 4 个风险点
make 阶段:      R2(高), R5(中)                       → 2 个风险点
make install:   R6(高)                               → 1 个风险点
运行时:         R3(高), R4(高), R5(高), R9(中), R10(中), R12(中), R13(中), R14-R20(低)  → 14 个风险点
```

## 预判准确性验证清单

> 编译验证时逐一确认以下预测：

| # | 预测 | 预判结果 | 实际结果 | 准确？ |
|---|------|----------|----------|--------|
| 1 | configure 第一步就报错 | 🔴 100% | ⏳ | |
| 2 | 扩展模块缺少 SDK 头文件 | 🔴 80% | ⏳ | |
| 3 | musl BIND_NOW ImportError | 🔴 90% | ⏳ | |
| 4 | subprocess 静默失败 | 🔴 80% | ⏳ | |
| 5 | ctypes CFUNCTYPE MemoryError | 🔴 70% | ⏳ | |
| 6 | HMDFS symlink 问题 | 🔴 90% | ⏳ | |
| 7 | cpu_count 崩溃 | 🟡 60% | ⏳ | |
| 8 | timemodule 时区异常 | 🟡 70% | ⏳ | |
| 9 | venv lib64 失败 | 🟡 50% | ⏳ | |
| 10 | setuptools 兼容 | 🟡 40% | ⏳ | |
