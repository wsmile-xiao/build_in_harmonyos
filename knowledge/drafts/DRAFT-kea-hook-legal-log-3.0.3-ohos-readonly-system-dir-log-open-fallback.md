# DRAFT-kea-hook-legal-log-3.0.3: OHOS app 沙箱只读系统目录下的日志文件打开回退（EROFS/EACCES → $HOME scratch）

- **条目 ID**: `DRAFT-kea-hook-legal-log-3.0.3-ohos-readonly-system-dir-log-open-fallback`
- **严重度**: 2（🟡 中等）
- **类别**: cxx, runtime, file-io, sandbox, gtest, portability, ohos
- **触发工具/阶段**: cxx | conan | gtest — test / runtime
- **来源**: kea-hook-legal-log 3.0.3 适配（feat/kea-hook-legal-log-3.0.3，OHOS PC aarch64）
- **路径**: Path B（知识库扩展）
- **关联**: [[DRAFT-kea-hook-legal-log-3.0.3-ohos-runtime-command-spawn-interpreter-prefix]]（同一适配的另一运行时层问题：命令 spawn；本条目是文件 I/O 层）

## 症状

kea-hook-legal-log 3.0.3 的 `dhcp-forensic-log-tests` 套件在 OHOS 真机上，
`LegalLogMgrTest.pathEnvVarOverride` 用例 FAIL：

```
legal_log_mgr_unittests.cc:196: Failure
Expected: LegalLogMgrFactory::addBackend(map) doesn't throw an exception.
  Actual: it throws isc::dhcp::LegalLogMgrError with description
  "cannot open file:/tmp/kea-legal.20260929.txt reason: Read-only file system".
```

该用例的 fixture 把日志目录环境变量设为 `/tmp`（`KEA_LEGAL_LOG_DIR=/tmp`），
`addBackend` 构造文件后端时直接打开 `/tmp/kea-legal.<日期>.txt`——OHOS 上
这一步以 EROFS 失败。

## 根因

1. **沙箱挂载层**：OHOS app 沙箱把 `/tmp` 等系统目录以**只读**挂载（与 conan
   在真机上需要 pick_temp_dir 绕开 /tmp 是同一个约束）。上游代码按
   glibc/Linux 惯例假设 `/tmp` 可写。
2. **打开层**：`RotatingFile::openInternal()`（`src/hooks/dhcp/forensic_log/
   rotating_file.cc`）直接 `file_.open(file_name_, ofstream::app)`，失败即抛
   `LegalLogMgrError`。文件后端在 `addBackend` 时就打开日志文件，因此异常
   从测试的 `EXPECT_NO_THROW` 处冒出。
3. **修复位置的硬约束**：上游测试同时断言 `parseFile` 对非法路径抛出的
   `BadValue` 消息文本——`"invalid path specified: '/bogus', supported path
   is '<配置路径>'"`，消息里嵌着 `getLogPath()` 的返回值。所以修复**不能**
   改路径解析/校验层的字符串（改了消息就变，测试照样挂），只能落在**文件
   打开层**：改变字节落在哪里，而不改变配置说是什么。

## 最小复现

```cpp
// rotating_file.cc — openInternal()
file_.open(file_name_.c_str(), ofstream::app);   // file_name_ = /tmp/kea-legal.<date>.txt
int sav_error = errno;
if (!file_.is_open()) {
    isc_throw(LegalLogMgrError, "cannot open file:" << file_name_
              << " reason: " << strerror(sav_error));
}
```

OHOS 真机上 `KEA_LEGAL_LOG_DIR=/tmp` 时必抛 EROFS；glibc/Linux 上正常。

## 已试过的失败方案

1. 改 `getLogPath()`/PathChecker 把 `/tmp` 翻译成可写路径：BadValue 消息文本
   随之改变，上游 line 215 的消息断言失败（治标失彼）。
2. 在测试环境层给 /tmp 找可写替代（env、挂载）：/tmp 是只读挂载，无特权不可
   变更；测试硬编码 `/tmp` 字符串，外部环境变量无法覆盖 fixture 的 setValue。

## 解决方案

在 musl-Linux 编译期守卫下，打开失败且 `errno ∈ {EROFS, EACCES}` 时回退到
`$HOME` 下的可写 scratch 目录：

```cpp
    file_.open(file_name_.c_str(), ofstream::app);
    int sav_error = errno;

#if defined(__linux__) && !defined(__GLIBC__)
    if (!file_.is_open() && (sav_error == EROFS || sav_error == EACCES)) {
        const char* home = getenv("HOME");
        std::string scratch = std::string(home && *home ? home : ".") +
                              "/.kea-legal-log";
        mkdir(scratch.c_str(), 0755);
        std::string alt;
        for (size_t i = 0; i < file_name_.size(); ++i) {
            alt += (file_name_[i] == '/') ? '_' : file_name_[i];
        }
        file_.clear();
        file_.open((scratch + "/" + alt).c_str(), ofstream::app);
        if (!file_.is_open()) {
            sav_error = errno;
        }
    }
#endif
```

要点：

- **路径 `/` 转 `_` 编码进 scratch 文件名**：不同配置路径不碰撞，且映射
  确定性保证同一配置路径在轮转 reopen（`openInternal` 每次由
  `updateFileNameAndTimestamp` 重新生成配置路径名）时落回同一 scratch 文件。
- **只对 EROFS/EACCES 触发**：可写的配置路径行为与上游逐字节一致；配置
  字符串、PathChecker 校验消息全部原样保留（上游 BadValue 消息断言照常过）。
- **`file_.clear()` 不可省**：一次失败的 open 会置 failbit，不清状态直接
  二次 open 必然失败。
- **mkdir 幂等**：忽略 EEXIST 及失败（失败时二次 open 会失败并带上新的
  errno，异常路径仍然可见）。
- **守卫与家族约定一致**：`!__GLIBC__` 而非平台宏，glibc/Linux（上游 CI）
  保留原路径；与 0002/0005 的守卫约定相同，平台宏守卫 pending 合规。
- **用上游真实用例验收**：`pathEnvVarOverride`（`KEA_LEGAL_LOG_DIR=/tmp`）
  本身就是验证——addBackend 不再抛异常即回退生效，无需另写测试。

## 验证

kea-hook-legal-log 3.0.3 真机：补丁 0006 应用后 `meson test
dhcp-forensic-log-tests dhcp-forensic-log-libloadtests` 两套件全绿
（`pathEnvVarOverride` PASSED：`$HOME/.kea-legal-log/` 下出现实际日志文件，
配置路径消息仍为 `/tmp`）；其余 90 例（含 0005 覆盖的 3 个 spawn 用例）与
0006 前行为一致；glibc/Linux 分支未受扰动（守卫外路径逐字节保持上游原样）。
