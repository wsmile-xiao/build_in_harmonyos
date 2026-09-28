# DRAFT-E3002：mkstemp 探针的 musl 安全语义与 TMPDIR 规避（/tmp 只读）

- **触发实例**：samba 4.21.0 适配（2026-09-21，分支 feat/samba-4.21.0，wafsamba configure）
- **错误签名**：`Checking for HAVE_SECURE_MKSTEMP : not found` / `mandatory failure for this one` / `The configuration failed`
- **类别**：libc（musl）/ 探测（detection）/ compat
- **严重度**：3（configure 确定性中断）

## 症状（可复现）

```text
Checking for HAVE_SECURE_MKSTEMP : not found
from .../lib/replace: The configuration failed False   # mandatory=True 直接中断
```

## 根因

Samba `lib/replace/wscript` 的 `HAVE_SECURE_MKSTEMP` 探针（execute=True）运行时在 `TMPDIR` 创建 `test.XXXXXX` 并断言其 mode 恰为 `0600`：

1. **/tmp 只读（E002）**：OHOS `/tmp` 是只读 erofs，探针无法在其下创建临时文件；
2. **HMDFS mode 归一化（E046）**：即使换到可写目录，HMDFS 把新建文件权限归一化为 `0640`，`chmod` 不生效；
3. **判定过严**：musl/OHOS 的真实安全语义是「属主可读写且组/其他无写权限」，与上游"恰 0600"的 glibc 假设不一致——探针在任何可写目录都必然判 not found；
4. 上游把该探针标 `mandatory=True`（源码注释 "lets see if we get a mandatory failure for this one"），configure 直接中止。

## 方案

对 `0001-lib-replace-wscript.patch`：
- 探针改用 `TMPDIR`（conan build env 注入可写临时目录）；
- 安全判定从「恰 0600」放宽为「属主可读写且组/其他无写权限」（`(mode & 0o022) == 0`）；
- `HAVE_SECURE_MKSTEMP` 由探针**真实结果**驱动，不做平台宏。

## 验证

```sh
OHOS 实测：Checking for HAVE_SECURE_MKSTEMP : ok
```

samba 4.21.0 全量 waf configure 通过，0 处 `__OHOS__`（R8 配置式探测）。

## 边界 / 禁止

- 不 hrefchd /dev/shm 或设备专用路径；
- 不注入 `-D__OHOS__`；
- 不为探针伪造通过；若"not found"是真实结果，则接受并走 lib/replace bundled 实现。

## 关联

- 强关联：E046（HMDFS mode 归一化）、E002（/tmp 只读）、DRAFT-11055（Samba 独立库同族）。
- 触发 PR：!11515。
