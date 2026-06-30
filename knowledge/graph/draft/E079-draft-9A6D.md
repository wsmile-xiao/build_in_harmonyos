# E079 — GNU cat stdout Permission Restriction on HarmonyOS

## 错误特征
在 HarmonyOS 上编译 autotools 项目时，configure 或 config.status 阶段报错：
```
cat: standard output: Permission denied
configure: caught signal 13
```
或出现 SIGPIPE（管道破裂）错误。

## 触发条件
- 构建系统: autotools (configure scripts)
- 阶段: configuration (configure/config.status)
- 前置: GNU coreutils 已编译安装并位于 PATH 前部

## 根因分析
GNU coreutils cat (版本 9.10) 在 HarmonyOS 上受 SELinux/HMDFS 文件系统约束，stdout 输出被权限限制阻止。系统原生 toybox cat (/bin/cat) 可以正常工作。

问题出在 PATH 顺序：
1. 用户编译 GNU coreutils 安装到 ~/usr/local/bin
2. ~/usr/local/bin 在 PATH 中优先级最高
3. configure 脚本的管道操作调用 cat
4. GNU cat 执行时 stdout 被阻止
5. 管道破裂 → SIGPIPE → configure 失败

## 解决方案

### 推荐方案（手动）
在 configure 执行前临时调整 PATH，确保 toybox 命令优先：
```bash
export PATH=/bin:$PATH
./configure --prefix=$DEFAULT_PREFIX
```

### 方案 B（wrapper）
创建 cat wrapper 脚本，fallback 到 toybox cat：
```bash
# scripts/wrappers/cat-wrapper.sh
if [ -x /bin/cat ]; then
    exec /bin/cat "$@"
else
    exec /usr/bin/cat "$@"
fi
```

### 禁止做法
- ❌ 不要删除 GNU coreutils（其他工具如 expr、sed 可能正常工作）
- ❌ 不要永久改变系统 PATH（可能影响其他软件）
- ❌ 不要使用 --build/--host 绕过（native 编译不需要）

## 验证
```bash
# 验证 cat stdout 是否可用
echo "test" | cat && echo "cat stdout works" || echo "cat stdout fails"

# 验证 toybox cat
echo "test" | /bin/cat && echo "toybox cat works"
```

## 关联条目
- 相关: E002 (/tmp 只读), E046 (chmod 不生效)
- 类似: E070 (toybox sh 限制)
- 影响: 所有 autotools 项目
