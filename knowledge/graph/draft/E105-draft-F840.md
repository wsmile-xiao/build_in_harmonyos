# E105: install 命令缺失

## 错误特征

执行 `make install` 时出现命令未找到错误：
```
install -m 0755 -d /storage/Users/currentUser/tmp/test-install-incron-0.5.12/storage/Users/currentUser/usr/local/share/man/man1
make: install: No such file or directory
make: *** [Makefile:63: install-man] Error 127
```

## 触发条件
- 构建系统: Makefile
- 阶段: installation（安装阶段）
- 操作: 执行 `make install` 或调用 install 命令的脚本

## 根因分析

OpenHarmony 缺少 GNU coreutils 的 `install` 命令。`install` 是 GNU coreutils 的一部分，用于：
- 复制文件到指定位置
- 设置文件权限（-m 参数）
- 设置文件所有者（-o, -g 参数）
- 创建目标目录（-d 参数）
- 创建备份（-b 参数）

OpenHarmony 的工具集不包含完整的 GNU coreutils，只提供了基本的 Unix 命令（cp, mv, rm, mkdir 等），导致依赖 `install` 命令的 Makefile install 目标失败。

## 解决方案

### 方案 A：手动安装（推荐）

手动使用 `cp` + `chmod` + `mkdir` 替代 `install` 命令：

```bash
# 示例 1: 安装二进制文件（权限 0755）
cp incrond ~/usr/local/sbin/
chmod 0755 ~/usr/local/sbin/incrond

# 示例 2: 安装 SUID 程序（权限 04755）
cp incrontab ~/usr/local/bin/
chmod 04755 ~/usr/local/bin/incrontab

# 示例 3: 安装文档（权限 0644）
mkdir -p ~/usr/local/share/man/man1
cp incrontab.1 ~/usr/local/share/man/man1/
chmod 0644 ~/usr/local/share/man/man1/incrontab.1

# 示例 4: 创建目录
mkdir -p ~/usr/local/share/doc/incron
cp -r examples/* ~/usr/local/share/doc/incron/
```

### 方案 B：修改 Makefile

修改 Makefile 中的 install 命令：

```makefile
# 原始 Makefile 片段
install: all
	install -m 0755 incrond $(DESTDIR)$(SBINDIR)
	install -m 04755 incrontab $(DESTDIR)$(BINDIR)
	install -m 0644 incrontab.1 $(DESTDIR)$(MANDIR)/man1/

# 修改后的 Makefile 片段
install: all
	mkdir -p $(DESTDIR)$(SBINDIR)
	cp incrond $(DESTDIR)$(SBINDIR)/
	chmod 0755 $(DESTDIR)$(SBINDIR)/incrond
	mkdir -p $(DESTDIR)$(BINDIR)
	cp incrontab $(DESTDIR)$(BINDIR)/
	chmod 04755 $(DESTDIR)$(BINDIR)/incrontab
	mkdir -p $(DESTDIR)$(MANDIR)/man1/
	cp incrontab.1 $(DESTDIR)$(MANDIR)/man1/
	chmod 0644 $(DESTDIR)$(MANDIR)/man1/incrontab.1
```

使用 sed 自动替换：
```bash
# 简单替换（不完美，需要手动调整）
sed -i 's/install -m \([0-9]*\) \(.*\)/cp \2 \&\& chmod \1/' Makefile
```

### 方案 C：创建 install 脚本包装

创建一个简化的 `install` 命令包装脚本：

```bash
cat > ~/usr/local/bin/install << 'EOF'
#!/bin/bash
# 简化的 install 命令包装
# 支持: -m MODE, -d, 源文件 目标

MODE="0644"
CREATE_DIR=false

while getopts "m:d" opt; do
    case $opt in
        m) MODE=$OPTARG ;;
        d) CREATE_DIR=true ;;
    esac
done
shift $((OPTIND-1))

if [ "$CREATE_DIR" = true ]; then
    mkdir -p "$1"
    chmod $MODE "$1"
else
    cp "$1" "$2"
    chmod $MODE "$2"
fi
EOF

chmod +x ~/usr/local/bin/install
```

### 禁止做法
- ❌ 不要尝试使用 `apt-get install coreutils`（OpenHarmony 不是标准 Linux 发行版）
- ❌ 不要尝试使用 `yum install coreutils`（OpenHarmony 不支持 yum）
- ❌ 不要直接复制 GNU coreutils 的 install 命令（可能依赖 glibc）

## 验证

检查 install 命令是否可用：
```bash
# 检查命令是否存在
which install || echo "install command missing"

# 检查手册页
man install 2>/dev/null || echo "install manpage missing"

# 测试安装（手动方式）
mkdir -p ~/tmp/test-install
cp test-binary ~/tmp/test-install/
chmod 0755 ~/tmp/test-install/test-binary
ls -l ~/tmp/test-install/test-binary
```

## install 命令对照表

| install 命令 | cp + chmod 等价组合 |
|-------------|---------------------|
| `install -m 0755 src dst` | `cp src dst && chmod 0755 dst` |
| `install -m 0644 src dst` | `cp src dst && chmod 0644 dst` |
| `install -m 04755 src dst` | `cp src dst && chmod 04755 dst` |
| `install -d dir` | `mkdir -p dir && chmod 0755 dir` |
| `install -m 0755 -d dir` | `mkdir -p dir && chmod 0755 dir` |
| `install -m 0644 src dir/` | `mkdir -p dir && cp src dir/ && chmod 0644 dir/$(basename src)` |

## 受影响项目

已知受影响项目：
- incron 0.5.12（Makefile install 目标）
- 其他使用 `install` 命令的 Makefile 项目

## 关联条目
- 相关: E001 (GNU 工具缺失), E080 (HMDFS 权限问题)
- 应用: 所有使用 Makefile install 目标的项目

## 平台差异

| 功能 | GNU/Linux | OpenHarmony |
|------|-----------|-------------|
| `install` 命令 | ✅ | ❌ |
| `cp` 命令 | ✅ | ✅ |
| `chmod` 命令 | ✅ | ✅ |
| `mkdir -p` | ✅ | ✅ |

## 历史

- 2026-05-26: 首次发现（incron 0.5.12 安装）
- 2026-05-27: 知识条目创建