# E-DRAFT: HMDFS mktemp -d setgid(2700) 目录拒所有者写入——本机同 uid 场景的 umask 022 轻处方

- **触发实例**：kexec-tools 2.0.32 适配（2026-09-18，分支 feat/kexec-tools-2.0.32）
- **错误签名**：`./config.status[724]: can't create ./confXXXXXX/subs1.awk: Permission denied` → `config.status: error: could not setup config files machinery`
- **类别**：platform/autotools/tmpdir/hmdfs（E011 家族 mktemp 变体的本机同 uid 子型）
- **严重度**：3（configure 后段确定性失败）

## 症状

configure 本体全部 checking 通过并打印 `configure: creating ./config.status`，随后 config.status 立即失败：

```text
./config.status[724]: can't create ./confHJdnEJ/subs1.awk: Permission denied
config.status: error: could not setup config files machinery
```

## 根因（与 DRAFT-6507 的差异点）

HMDFS 上 `(umask 077 && mktemp -d "./confXXXXXX")` 产出的目录呈 **2700（drwx--S---）** 状态：
- **同 uid 也拒写**（属主 20001006 == 进程 uid，touch 仍 Permission denied）
- 显式 `chmod 700 / chmod 755 / chmod g-s` **全部不生效**（stat 仍 2700，写仍拒）

对照实测矩阵（本机 HarmonyOS aarch64）：

| 创建方式 | stat | 可写 |
|---|---|---|
| `(umask 077 && mktemp -d "./xXXXXXX")` | **2700** | ❌ |
| `mktemp -d`（无 umask 包裹） | 2771 | ✅ |
| `(umask 077 && mkdir ./x)`（fallback 路径） | 2771 | ✅ |
| 显式 `mkdir + chmod 700` | 2771 | ✅ |

→ 唯一触发向量是 **mktemp -d + umask 077 组合**；fallback mkdir 路径天然安全。

DRAFT-6507（cln）是 SSH **跨 uid** 场景（mktemp 恒 0700 + uid 错位语义），
umask 放宽无效须 mkdir -m 0777；本条是**本机同 uid** 场景，umask 022 替换后
mktemp 直接产出 2771 可写目录——处方更轻（2 行 sed，不动 mktemp 结构）。

## 修复（处方 A：本机同 uid）

```bash
# configure 内有两处（autoconf 模板的 mktemp 主路径 + mkdir fallback）：
sed -i 's/umask 077/umask 022/g' configure
```

（CI worker SSH 跨 uid 场景走 DRAFT-6507 的 mkdir -m 0777 处方 B。）

## 判别探针（命中即用本条）

```bash
tmp=$( (umask 077 && mktemp -d "./tXXXXXX") 2>/dev/null )
stat -c %a "$tmp"        # 2700
touch "$tmp/probe"       # Permission denied → 命中
```

## 验证证据（kexec-tools 2.0.32，2026-09-18）

1. umask 077 原样 → config.status Permission denied（复现）
2. 探针隔离出 mktemp+077 组合是唯一向量（2700 vs 2771 矩阵）
3. sed 替换后 configure → config.status 全通
4. 干净 builddir 全流程（configure + make -j4 + make install DESTDIR）通过
5. conan create（ohos-aarch64 profile）+ test_package 消费者测试全绿

## 复用先例

- strace 6.19（archives/s/strace/6.19/conanfile.py build() 同款 umask 替换）
- 本条差异：把"为什么 umask 替换有效"的机理讲清了（2771 vs 2700），并给出
  与 DRAFT-6507 的场景判别（同 uid / 跨 uid）
