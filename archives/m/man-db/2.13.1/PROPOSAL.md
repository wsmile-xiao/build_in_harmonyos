# man-db 预编译包安装路径适配方案

## 问题

man-db 二进制中硬编码了 `$TEST_PREFIX` 路径，部署到 `$HOME/usr/local` 后无法运行：

```
# 二进制中硬编码的路径（strings 输出）
/storage/Users/currentUser/tmp/test-install-man-db-2.13.1/etc/man_db.conf
/storage/Users/currentUser/tmp/test-install-man-db-2.13.1/lib/man-db
/storage/Users/currentUser/tmp/test-install-man-db-2.13.1/libexec/man-db/manconv
/storage/Users/currentUser/tmp/test-install-man-db-2.13.1/libexec/man-db/zsoelim
```

涉及 **5 类路径**：
| 路径类型 | 硬编码值 | 用途 |
|---------|---------|------|
| etc | `$TEST_PREFIX/etc/man_db.conf` | 配置文件 |
| lib | `$TEST_PREFIX/lib/man-db` | 共享库搜索路径 |
| libexec | `$TEST_PREFIX/libexec/man-db/manconv` | 格式转换 |
| libexec | `$TEST_PREFIX/libexec/man-db/zsoelim` | 预处理器 |
| libexec | `$TEST_PREFIX/libexec/man-db/globbing` | glob 扩展 |

## 方案对比

### 方案 A：DESTDIR 模式（❌ 不推荐）

```
configure --prefix=$HOME/usr/local
make install DESTDIR=$TEST_PREFIX
```

问题：
- 二进制中硬编码 `/storage/Users/currentUser/usr/local/etc/...`
- 另一个用户的 `$HOME` 不同，路径不匹配
- **不可移植**

### 方案 B：`--sysconfdir`（❌ 不够）

只解决 `man_db.conf` 路径问题，`libexec`、`lib` 路径仍然硬编码。

### 方案 C：install.sh 中 patchelf 替换路径（❌ 不可靠）

二进制中字符串长度可能不同，patchelf 不支持字符串替换。

### 方案 D：install.sh 中用 wrapper + `-C` 选项（✅ 推荐）

man-db 所有命令都支持 `-C` 指定配置文件，`MANOPT` 环境变量可全局传递 `-C`。
但 `-C` 只解决配置文件路径，**libexec/lib 路径仍需解决**。

### 方案 E：install.sh 中用 patchelf 重写所有路径（✅ 可行但重）

用 `patchelf` 或 `sed` 对二进制做字符串替换。
但路径长度不同时需 padding，有风险。

### 方案 F：configure 时 `--prefix=$HOME/usr/local` + 不用 DESTDIR（✅ 推荐）

直接将最终部署路径作为 `--prefix`，make install 时文件直接安装到 `$HOME/usr/local`，
**同时用 `--prefix=$TEST_PREFIX` 做隔离安装（当前方式）+ install.sh 中 sed 替换二进制路径**。

---

## 最终推荐方案

**两步走：框架通用改动 + man-db install.sh 路径重写**

### 第一步：通用框架改动（package_builder.py）

> 所有预编译包受益，合入上游无风险

#### 1.1 step2_copy — 自动扫描目录

**现状**：硬编码 `["bin", "lib", "include", "share"]`，漏掉 `sbin`、`libexec`、`etc`

**改为**：扫描 `src_prefix` 下的所有顶层目录，排除已知不需要的目录

```python
# 排除列表
EXCLUDE_DIRS = {".cache", ".config", ".state", "var", "run", "tmp", "log"}

for subdir in sorted(self.src_prefix.iterdir()):
    if subdir.is_dir() and subdir.name not in EXCLUDE_DIRS:
        dst = self.pkgdir / subdir.name
        dst.mkdir(parents=True, exist_ok=True)
        for item in subdir.iterdir():
            if item.is_dir():
                shutil.copytree(str(item), str(dst / item.name), dirs_exist_ok=True)
            else:
                shutil.copy2(str(item), str(dst / item.name))
```

#### 1.2 step1_create_pkgdir — 不再硬编码创建目录

**现状**：硬编码创建 `["bin", "lib", "lib/external", "include", "share", "doc"]`

**改为**：只创建 `lib/external`（收集依赖用），其他目录由 step2_copy 动态创建

#### 1.3 step10_tarball — 动态打包

**现状**：硬编码 `tar czf ... bin lib include share doc`

**改为**：扫描 `self.pkgdir` 顶层目录动态打包

```python
dirs = [d.name for d in self.pkgdir.iterdir() if d.is_dir()]
subprocess.run(["tar", "czf", str(tar_gz)] + sorted(dirs), cwd=str(self.pkgdir), ...)
```

### 第二步：man-db install.sh 路径重写

> man-db 专有逻辑，在 install.sh 中处理

#### 2.1 二进制路径重写（关键）

install.sh 中解压后，用 `sed` 对所有 ELF 二进制做路径替换：

```sh
# 在解压后、安装前，替换二进制中的硬编码路径
STAGING="$TMP"
OLD_PREFIX="$TEST_PREFIX"    # 编译时的前缀
NEW_PREFIX="$DST"             # 安装目标路径

# 对所有 ELF 文件做路径替换
find "$STAGING" -type f | while read f; do
    if file "$f" | grep -q ELF; then
        # 精确替换（路径长度必须相同，用 padding 补齐）
        # 方案：在 install.sh 中用 python3 做可靠的二进制替换
        python3 -c "
import sys
old = '$OLD_PREFIX'
new = '$NEW_PREFIX'
# 确保新路径不比旧路径长
if len(new) > len(old):
    print(f'Error: new path {len(new)} > old {len(old)}', file=sys.stderr)
    sys.exit(1)
# 用 null 字节 padding
padded = new + '\\0' * (len(old) - len(new))
with open('$f', 'r+b') as fh:
    data = fh.read()
    if old.encode() in data:
        data = data.replace(old.encode(), padded.encode())
        fh.seek(0)
        fh.write(data)
        fh.truncate()
"
    fi
done
```

**但这个方案有问题**：`$TEST_PREFIX` 路径包含用户名，长度因用户而异。

#### 2.2 最终方案：用固定的 staging 路径编译

**核心思路**：编译时用**固定长度的 staging 路径**，install.sh 中替换为等长或更短的部署路径。

```
# 编译时
TEST_PREFIX=~/tmp/test-install-man-db-2.13.1  # 路径长度约 50 字节

# 部署时
DST=$HOME/usr/local  # 路径长度约 30 字节
# 替换后用 \0 padding 补齐差额
```

这样 sed/python 替换是安全的（新路径 ≤ 旧路径长度）。

**验证路径长度**：
```
TEST_PREFIX=/storage/Users/currentUser/tmp/test-install-man-db-2.13.1
DST=/storage/Users/currentUser/usr/local

len(TEST_PREFIX) = 55
len(DST) = 38
差值 = 17，用 \0 padding ✅
```

### 完整 install.sh 伪代码

```sh
#!/bin/sh
VER="${1:-}"
[ -z "$VER" ] && { echo "Usage: sh install.sh <version>"; exit 1; }

TMP="$HOME/tmp/install-man-db-$$"
DST="$HOME/usr/local"
URL="https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/man-db/man-db-${VER}-ohos-aarch64.tar.gz"

mkdir -p "$TMP" "$DST" || exit 1

# 1. 下载
curl -fSL -o "$TMP/man-db.tar.gz" "$URL" || { rm -rf "$TMP"; echo "Download failed"; exit 1; }

# 2. 解压
tar xzf "$TMP/man-db.tar.gz" -C "$TMP"
rm -f "$TMP/man-db.tar.gz"

# 3. 路径重写：替换二进制中的编译时 staging 路径为部署路径
OLD="/storage/Users/currentUser/tmp/test-install-man-db-2.13.1"
# 用 sed -b (binary mode) 做精确替换，\0 padding 自动补齐
find "$TMP" -type f -exec file {} \; | grep ELF | cut -d: -f1 | while read f; do
    sed -b -i "s|${OLD}|${DST}|g" "$f"
done

# 4. 生成适配的 man_db.conf
mkdir -p "$TMP/etc"
sed -e "s|/usr/share/man|$DST/share/man|g" \
    -e "s|/usr/local/share/man|$DST/share/man|g" \
    -e "s|/usr/local/man|$DST/share/man|g" \
    -e "s|/usr/man|$DST/share/man|g" \
    -e "s|/var/cache/man|$DST/var/cache/man|g" \
    "$TMP/etc/man_db.conf" > "$TMP/etc/man_db.conf.tmp"
mv "$TMP/etc/man_db.conf.tmp" "$TMP/etc/man_db.conf"

# 5. 安装
cp -r "$TMP"/* "$DST/"

# 6. 创建缓存目录
mkdir -p "$DST/var/cache/man"

# 7. 清理 + 权限 + PATH
rm -rf "$TMP"
chmod +x "$DST/bin/"* "$DST/sbin/"* "$DST/libexec/man-db/"* 2>/dev/null || true
grep -q 'usr/local/bin' "$HOME/.zshrc" 2>/dev/null || \
    echo 'export PATH="$HOME/usr/local/bin:$PATH"' >> "$HOME/.zshrc"

# 8. 预触发安全弹窗
"$DST/bin/man" --version >/dev/null 2>&1 || true

echo "=== man-db $VER installed ==="
```

### 关键风险

#### 路径重写的可靠性

`sed -b -i` 对 ELF 二进制做替换时：
- 新路径必须 ≤ 旧路径长度（否则溢出）
- 当前 `TEST_PREFIX` (55) > `DST` (38)，✅ 安全
- 但**不同用户的 TEST_PREFIX 长度可能不同**

**缓解措施**：
1. 编译时用固定长度的 staging 路径（如 `/opt/staging/man-db-2.13.1`，24 字节）
2. 或在 `step9_install_sh` 中**只对 man-db 这类有硬编码路径的软件**生成路径重写逻辑
3. 或在 package_builder.py 中增加 `--path-rewrite` 选项

## 推荐改动文件列表

| 文件 | 改动类型 | 影响范围 |
|------|---------|---------|
| `package_builder.py` step2_copy | 通用 | 所有软件自动打包 sbin/libexec/etc |
| `package_builder.py` step10_tarball | 通用 | 动态打包 |
| `package_builder.py` step9_install_sh | man-db 专有 | install.sh 中增加路径重写和配置适配 |
| `archives/m/man-db/install.sh` | 生成物 | 重新生成 |

## 不需要改动

| 项 | 说明 |
|----|------|
| configure 参数 | 不需要加 `--sysconfdir`，路径重写已覆盖 |
| 重新编译 | 不需要，当前二进制可以直接路径重写 |
| driver.py | 不需要改 |
| SKILL.md 流程 | 不需要改 |

## 可选改进（不在本次范围）

1. **编译时用固定 staging 路径**：在 SKILL.md 中建议 `TEST_PREFIX` 使用固定长度路径
2. **`patchelf` 增加 `--replace-string` 功能**：比 sed -b 更可靠
3. **manifest.yaml 增加 `rewrite_paths: true`**：标记哪些软件需要路径重写
