# DRAFT-7640-jkmeter-0.9.0-signed-elf-chmod-eperm-defensive：HMDFS 上已签名 ELF 的 `os.chmod` 抛 EPERM（非 E046 静默失效），缓存复用场景才现形

> Contributor: 主理-60 | Status: Draft | Updated: 2026-09-26
> Source: jkmeter 0.9.0 适配（任务 7640）
> 对应：`knowledge/drafts/DRAFT-7640-jkmeter-0.9.0-signed-elf-chmod-eperm-defensive.kv`
> 近邻条目：E046（chmod 静默失效 → skip-test）——同为 HMDFS 上 chmod 面，但症状/解法/触发场景三点不同，见下表。

## 现象

conan test_package 对产物 `bin/jkmeter` 调 `os.chmod` 时：

```console
PermissionError: [Errno 1] Operation not permitted
```

最隐蔽的点：**首轮构建完全正常**，绿了一轮之后的复跑（缓存包复用、同
package_id 二次 create、下游消费者复用）才炸——首轮产物是刚解包/重打包
的未签文件，chmod 无碍；复用时产物带着 codesign 签名段，HMDFS 对它施加
写保护，chmod 直接抛 EPERM。

## 根因

HarmonyOS 的 HMDFS/安全子系统对**已签名 ELF** 施加写保护：签名段在文件里，
再对文件做 chmod 这类元数据写操作会被安全层拒绝——是**响亮异常**（EPERM），
不是 E046 的「chmod 返回成功但权限没变」的静默失效。两者的坑面完全不同：

| | E046 | 本条 |
|---|---|---|
| chmod 行为 | 返回**成功**但 mode 没变 | **抛 PermissionError 异常** |
| 被坑对象 | 依赖 chmod 的测试断言 | 打包/测试脚本流程（test_package 崩） |
| 触发条件 | HMDFS 一直生效 | **仅已签文件 + 缓存复用场景** |
| 解法 | 检测 chmod 失效后 skip-test | 防御式 chmod（位检查 + 异常兜底） |
| 与签名的关系 | 无关 | 文件签名完好，只是签后不可再改元数据 |

（与 E077B 的区别：那条是 codesign 本身不可用，签名面问题；本条的签名是
完好的，问题在签后写保护。）

## 方案：防御式 chmod 三段

```python
import os, stat

def ensure_exec(path):
    mode = stat.S_IMODE(os.stat(path).st_mode)   # ① 先读当前位
    if not mode & 0o111:                          # ② 位已在 ⇒ 跳过
        try:
            os.chmod(path, mode | 0o111)          # ③ 确需改才 chmod
        except PermissionError as e:
            print(f"warn: chmod skipped on signed ELF {path}: {e}")
```

- ⛔ 不要用「删除文件 → 重写 → chmod」绕：对已签文件重写同样被拒，
  且会破坏签名段。
- ⛔ 不要静默吞所有 OSError：只兜 `PermissionError`，别的错误照常抛，
  免得掩盖真问题。
- stat 兜底读也要防御：文件不可读时按明确失败处理，别输出假通过。

## 边界

1. **首轮绿 ≠ 验证过**：必须在缓存命中/复用条件下复跑一次 test_package
   （同 package_id 二次 create 或 conan install 缓存命中）才算覆盖本坑。
2. 确需改位的场景（权限真缺失）：把 chmod 挪到「解包后、签名前」的窗口期；
   缓存复用路径无法重排时，用「复制到可写目录再操作」替代原地 chmod。
3. 本坑不只在 test_package：打包脚本、install 脚本、CI 脚本对产物 chmod
   的所有位置同病。

## 证据（jkmeter 0.9.0，任务 7640，2026-09-26 B 机实测）

- 首跑：重打包产物 chmod 正常（未签），全绿。
- 复跑（缓存复用）：`bin/jkmeter`（68224B，codesign 附签）chmod 抛
  `PermissionError: [Errno 1]`。
- 整改：test_package 改防御式后复跑全绿；conan-verify 8 门全 PASS
  （`reports/conan-verify-report.md` Verdict: PASS）；finish built 成功
  （`reports/w3-local-ci.log`，`Success: 1 / Failed: 0`）。
- 提交链：`f77d3a4cfd`（chmod 防御式）→ `e60553b3e3`（终稿）。
