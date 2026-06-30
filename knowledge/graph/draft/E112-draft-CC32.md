# E112: HMDFS umask 077 临时目录权限冲突

## 问题

在 HarmonyOS 的 HMDFS 文件系统上，autoconf 的 configure/config.status 脚本使用
`umask 077 && mktemp -d` 创建临时目录时，由于 HMDFS 的 setgid 继承机制，
临时目录权限变为 `drwx--S---`（2700），导致后续无法在目录内创建文件。

## 根因

1. HMDFS 挂载的用户目录（~/tmp, ~/usr/local 等）具有 setgid 位
2. autoconf configure 脚本在创建临时目录时使用 `umask 077`
3. `umask 077` 会去除 group/other 的所有权限
4. 但 setgid 位从父目录继承，导致权限为 `drwx--S---`（大写 S 表示 setgid 但无执行权限）
5. 在 HMDFS MAC 模型下，此权限组合导致文件创建被拒绝

## 修复方案

```bash
# 在 configure 和 config.status 中将 umask 077 替换为 umask 022
sed -i 's/umask 077/umask 022/g' configure config.status
```

## 受影响软件

所有使用 autoconf 的软件。已知：libusb, 以及任何在 HMDFS 挂载目录中编译的软件。

## 验证

```bash
cd $BUILD_SRC_DIR
tmp=$(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null
echo "test" > "$tmp/test.txt" 2>&1 && echo "OK" || echo "FAIL"
rm -rf "$tmp"
```
