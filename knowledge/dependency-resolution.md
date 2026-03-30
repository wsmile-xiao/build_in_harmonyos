# 依赖递归处理流程

> 本文档描述鸿蒙系统上编译软件时的运行时依赖检测和递归处理流程。
> 静态依赖图请参考 [dependencies.md](./dependencies.md)，本文档聚焦于**编译过程中的动态依赖发现与递归解决**。

---

## §1 概述

当编译目标软件 X 时，如果发现缺少依赖库 Y，需要递归处理以下步骤：

1. **检测依赖**：X 需要 Y 吗？Y 需要安装还是已有？
2. **编译依赖**：如果需要，编译 Y
3. **递归处理**：如果 Y 也缺少依赖 Z，递归处理 Z（不限深度）
4. **版本冲突**：版本冲突时使用隔离环境

### 核心原则

- **不限深度**：递归可以无限深入，直到所有依赖都被满足
- **隔离优先**：遇到版本冲突时，使用隔离环境而非覆盖安装
- **归档复用**：如果 `archives/` 中已有某依赖的编译档案，优先复用其中的补丁和编译参数
- **最小安装**：非核心功能依赖可以通过 `--disable-X` / `--without-X` 禁用

### 与 dependencies.md 的关系

| 文档 | 职责 |
|------|------|
| `dependencies.md` | 静态依赖图、推荐编译顺序、依赖关系表 |
| `dependency-resolution.md`（本文档） | 运行时依赖检测、递归处理流程、版本冲突处理 |

---

## §2 依赖检测流程

### 阶段 1：configure 之前（静态分析）

在运行 `configure` 之前，通过静态分析提前发现依赖：

```
1. 检查 README / INSTALL 文档 → 列出依赖
2. 检查 configure.ac 或 CMakeLists.txt → 提取依赖
3. 查询 dependencies.md → 鸿蒙特有依赖关系
```

**具体操作**：

```bash
# 步骤 1：从文档中提取依赖列表
grep -i "depends\|requires\|prerequisite" README INSTALL 2>/dev/null

# 步骤 2：从构建配置中提取依赖
# autotools 项目
grep "AC_CHECK_LIB\|PKG_CHECK_MODULES\|AC_CHECK_HEADER" configure.ac

# CMake 项目
grep "find_package\|pkg_check_modules\|target_link_libraries" CMakeLists.txt

# 步骤 3：查询 dependencies.md
# 查找当前软件在依赖图中的位置和依赖列表
```

### 阶段 2：configure 运行时（自动检测）

`configure` 脚本会自动检测系统上已安装的依赖，输出包括：

```
# 成功找到
checking for zlib... yes
checking for openssl... yes

# 找不到（警告，可能可禁用）
checking for readline... no
configure: WARNING: readline library not found, building without line editing support

# 找不到（错误，无法继续）
configure: error: libssl development headers not found
Package 'openssl', required by 'xxx', not found    # pkg-config 报错
```

**处理策略**：

| 输出类型 | 含义 | 处理方式 |
|----------|------|----------|
| `... yes` | 依赖已满足 | 无需操作 |
| `... no`（无 error） | 可选依赖缺失 | 评估是否需要该功能 |
| `configure: error` | 必需依赖缺失 | 必须安装后重试 |
| `Package 'xxx' not found` | pkg-config 找不到 | 检查 PKG_CONFIG_PATH |

### 阶段 3：编译/链接时（编译器检测）

即使 configure 通过，编译或链接阶段仍可能暴露缺失的依赖：

```
# 编译时头文件缺失
fatal error: xxx.h: No such file or directory

# 链接时库缺失
/usr/bin/ld: cannot find -lxxx
/usr/bin/ld: undefined reference to `xxx_yyy'
```

**常见原因**：
- `PKG_CONFIG_PATH` 未正确设置，configure 误判依赖已存在
- 依赖库的头文件或库文件路径未被正确包含
- 依赖版本不兼容，API 已变更

**处理策略**：
```bash
# 检查 pkg-config 信息是否正确
pkg-config --cflags --libs xxx

# 手动检查库文件是否存在
ls $PREFIX/lib/libxxx* 2>/dev/null

# 检查头文件是否存在
ls $PREFIX/include/xxx.h 2>/dev/null
```

---

## §3 依赖判断标准

当发现缺少依赖 X 时，按照以下决策树判断处理方式：

```
发现缺少依赖 X
  │
  ├─ X 是系统预装的？
  │   │  检查命令: pkg-config --exists X
  │   │  或: ls $PREFIX/lib/libX*
  │   │
  │   ├─ 是 → 不需要编译，确认版本兼容即可
  │   │        pkg-config --modversion X
  │   │        对比所需版本范围
  │   │
  │   └─ 否 ↓
  │
  ├─ X 可以通过 --disable-X / --without-X 禁用？
  │   │  检查: ./configure --help | grep -i x
  │   │
  │   ├─ 是 → 评估功能影响
  │   │        ├─ 非核心功能 → 禁用，继续编译
  │   │        └─ 核心功能 → 不能禁用，继续 ↓
  │   │
  │   └─ 否 ↓
  │
  ├─ archives/ 中已有 X 的编译档案？
  │   │  检查: ls archives/第一字母/X/
  │   │  参考: archives/第一字母/X/manifest.yaml
  │   │
  │   ├─ 是 → 复用档案中的补丁和编译参数
  │   │        应用已验证的补丁，使用已验证的 configure 参数
  │   │
  │   └─ 否 → 从零编译，创建新的编译档案
  │
  └─ 开始编译 X → 递归进入 Phase 0-4（§5）
```

### 版本兼容性判断

```bash
# 查询已安装版本
pkg-config --modversion openssl
# 输出: 1.1.1w

# 查询所需版本范围
# 从 configure.ac 或 CMakeLists.txt 中提取
grep "min_version\|OPENSSL_MIN_VERSION\|required_version" configure.ac
```

| 情况 | 处理 |
|------|------|
| 已安装版本 ≥ 所需版本 | 直接使用 |
| 已安装版本 < 所需版本 | 需要编译新版本（考虑隔离环境） |
| 已安装版本不兼容（如 3.x vs 1.x） | 使用隔离环境 |

---

## §4 编译顺序与拓扑排序

### 推荐策略

- 使用 `dependencies.md` 的推荐编译顺序作为基准
- 核心原则：**被依赖最多的库最先编译**
- 典型顺序：zlib → openssl → ncurses → readline → (其他) → (目标软件)

### 拓扑排序规则

```
1. 从 dependencies.md 的依赖图中提取所有节点和边
2. 计算每个节点的入度（被多少其他节点依赖）
3. 按入度从高到低排序
4. 入度相同的节点，按以下优先级排列：
   a. 无依赖的优先（叶子节点）
   b. 基础库优先于应用层库
   c. 体积小的优先（编译速度快）
```

### 典型编译顺序

```
第零阶段：pkg-config（如系统预装版本不可用时）
    │
    ▼
第一阶段：基础工具链（无外部依赖）
  GNU sed → GNU coreutils → GNU gawk
    │
    ▼
第二阶段：Autotools 工具链
  automake → libtool
    │
    ▼
第三阶段：基础库（按依赖顺序）
  zlib → bzip2 → lzma → openssl → ncurses → readline → libffi → gettext → gdbm
    │
    ▼
第四阶段以后：按需编译
  wget → rsync → jq → bash → file → htop → strace → Python ...
```

> **注意**：上述顺序详见 `dependencies.md`，这里仅列出关键路径。实际编译时应根据目标软件的具体需求动态调整。

### 已编译依赖的检测

在开始编译新软件前，检查已有编译产物：

```bash
# 检查已编译的库
ls $PREFIX/lib/lib*.a $PREFIX/lib/lib*.so 2>/dev/null

# 检查 pkg-config 数据库
ls $PREFIX/lib/pkgconfig/*.pc 2>/dev/null

# 验证特定依赖可用
pkg-config --libs --cflags zlib openssl ncurses readline
```

---

## §5 递归编译流程

### 流程图

```
编译目标软件 A
  │
  ├─ Phase 1 检索：发现 A 需要依赖 B
  │   ├─ B 已安装？→ 继续
  │   └─ B 未安装 ↓
  │
  ├─ 创建子任务编译 B（独立会话/子任务）
  │   │
  │   ├─ Phase 1 检索：发现 B 需要依赖 C
  │   │   ├─ C 已安装？→ 继续
  │   │   └─ C 未安装 ↓
  │   │
  │   ├─ 创建子任务编译 C（继续递归）
  │   │   │
  │   │   ├─ Phase 1 检索：发现 C 需要依赖 D
  │   │   │   ├─ D 已安装？→ 继续
  │   │   │   └─ D 未安装 → 继续递归...
  │   │   │
  │   │   └─ C 无更多依赖 → 编译安装 C → 返回
  │   │
  │   └─ B 编译安装完成 → 返回
  │
  └─ A 继续编译
```

### 递归深度规则

- **不限深度**：递归可以无限深入，直到所有依赖都被满足
- **终止条件**：所有依赖都已安装，或所有缺失依赖都已编译安装
- **防重复**：维护一个"已编译依赖"列表，避免重复编译同一依赖

### 子任务拆分规则

每个依赖编译作为一个独立子任务，子任务的 objective 包含：

```yaml
# 子任务 objective 示例
objective: "编译安装 openssl 1.1.1w，供 python 3.9.0 链接使用"
context:
  parent_software: "python"
  parent_version: "3.9.0"
  parent_configure_args: "--with-openssl=$PREFIX"
  required_by: ["python", "wget", "curl"]
```

### 递归编译伪代码

```python
def build_software(name, version, parent_context=None):
    """递归编译软件及其所有依赖"""
    
    # Phase 0: 检查是否已安装
    if is_installed(name, version):
        log(f"{name} {version} already installed, skipping")
        return True
    
    # Phase 1: 检索依赖
    deps = detect_dependencies(name, version)
    
    # Phase 2: 递归编译每个缺失依赖
    for dep in deps:
        if not is_installed(dep.name, dep.version):
            log(f"{name} requires {dep.name} {dep.version}, starting recursive build")
            
            # 检查版本冲突
            if has_version_conflict(dep.name, dep.version):
                log(f"Version conflict for {dep.name}, creating isolated environment")
                prefix = create_isolated_env(dep.name, dep.version)
            else:
                prefix = DEFAULT_PREFIX
            
            # 递归编译依赖
            build_software(dep.name, dep.version, parent_context={
                "parent": name,
                "required_configure_args": dep.configure_args
            })
    
    # Phase 3: 编译当前软件
    log(f"Building {name} {version}")
    success = compile(name, version)
    
    # Phase 4: 验证安装
    if success:
        verify_installation(name, version)
        record_to_manifest(name, version)
    
    return success
```

### 子任务完成后验证

子任务完成后，主任务需要验证依赖可用性：

```bash
# 验证库文件存在
ls $PREFIX/lib/libxxx.a

# 验证 pkg-config 可查询
pkg-config --modversion xxx

# 验证头文件存在
ls $PREFIX/include/xxx.h

# 验证链接可用
echo '#include <xxx.h>' | cc -E -xc - > /dev/null 2>&1 && echo "OK"
```

---

## §6 版本冲突与隔离环境

### 冲突场景

**典型场景**：软件 A 需要 openssl 1.1.1，软件 B 需要 openssl 3.0

```
软件 A (如 python 3.9)
  └── 需要 openssl >= 1.1.1, < 2.0

软件 B (如 curl 8.x)
  └── 需要 openssl >= 1.1.1, < 3.1  或  >= 3.0

→ 两者可以共存于 openssl 1.1.1，但如果需要 openssl 3.0 的特性，则产生冲突
```

### 解决方案：隔离安装

通过将不同版本的库安装到独立的目录前缀，实现版本隔离：

```
隔离环境结构：
$HOME/usr/
├── openssl-1.1.1/     # 隔离环境 1
│   ├── bin/
│   ├── lib/
│   │   ├── libssl.a
│   │   ├── libcrypto.a
│   │   └── pkgconfig/
│   │       ├── openssl.pc
│   │       └── libcrypto.pc
│   └── include/
│       └── openssl/
├── openssl-3.0/       # 隔离环境 2
│   ├── bin/
│   ├── lib/
│   └── include/
└── bin/               # 公共 wrapper
    └── openssl        # 默认版本（wrapper 脚本）
```

### 隔离编译步骤

```bash
# ===== 编译 openssl 1.1.1 到隔离环境 =====
export PREFIX=$HOME/usr/openssl-1.1.1

# 配置编译环境，指向隔离目录
export PKG_CONFIG_PATH=$PREFIX/lib/pkgconfig
export CFLAGS="-I$PREFIX/include"
export LDFLAGS="-L$PREFIX/lib"

# 编译并安装到隔离目录
./config \
    --prefix=$PREFIX \
    --openssldir=$PREFIX/ssl \
    no-asm \
    shared \
    zlib \
    -I$HOME/usr/local/include \
    -L$HOME/usr/local/lib

make -j$(nproc)
make install

# ===== 使用隔离的 openssl 1.1.1 编译软件 A =====
export PKG_CONFIG_PATH=$HOME/usr/openssl-1.1.1/lib/pkgconfig
export CFLAGS="-I$HOME/usr/openssl-1.1.1/include"
export LDFLAGS="-L$HOME/usr/openssl-1.1.1/lib"

# 编译软件 A（如 python）
./configure --prefix=$HOME/usr/local \
    --with-openssl=$HOME/usr/openssl-1.1.1
make -j$(nproc)
make install

# ===== 编译 openssl 3.0 到隔离环境 =====
unset PKG_CONFIG_PATH CFLAGS LDFLAGS  # 清除环境
export PREFIX=$HOME/usr/openssl-3.0
export PKG_CONFIG_PATH=$PREFIX/lib/pkgconfig
export CFLAGS="-I$PREFIX/include"
export LDFLAGS="-L$PREFIX/lib"

# 编译并安装到隔离目录
./Configure \
    --prefix=$PREFIX \
    --openssldir=$PREFIX/ssl \
    no-asm \
    zlib \
    linux-aarch64

make -j$(nproc)
make install
```

### 全局默认版本管理

通过 wrapper 脚本或环境变量控制默认使用哪个版本：

```bash
# 方案 1：wrapper 脚本
# $HOME/usr/bin/openssl
cat > $HOME/usr/bin/openssl << 'EOF'
#!/bin/sh
# 默认使用 openssl 1.1.1
exec $HOME/usr/openssl-1.1.1/bin/openssl "$@"
EOF
chmod +x $HOME/usr/bin/openssl

# 方案 2：环境变量切换
# 在 .bashrc 中设置默认版本
export DEFAULT_OPENSSL_VERSION=1.1.1
export PKG_CONFIG_PATH=$HOME/usr/openssl-${DEFAULT_OPENSSL_VERSION}/lib/pkgconfig
```

### 隔离环境管理工具函数

```bash
# 切换隔离环境的辅助函数（加入 .bashrc）
use_isolated() {
    local pkg=$1
    local version=$2
    local base=$HOME/usr/${pkg}-${version}
    
    if [ ! -d "$base" ]; then
        echo "Error: $base does not exist" >&2
        return 1
    fi
    
    export PKG_CONFIG_PATH=$base/lib/pkgconfig:${PKG_CONFIG_PATH:+:$PKG_CONFIG_PATH}
    export CFLAGS="-I$base/include ${CFLAGS:+$CFLAGS}"
    export LDFLAGS="-L$base/lib ${LDFLAGS:+$LDFLAGS}"
    export PATH=$base/bin:${PATH:+:$PATH}
    
    echo "Switched to isolated $pkg $version"
    echo "  PKG_CONFIG_PATH=$PKG_CONFIG_PATH"
    echo "  CFLAGS=$CFLAGS"
    echo "  LDFLAGS=$LDFLAGS"
}

# 使用示例
# use_isolated openssl 1.1.1
# use_isolated openssl 3.0
```

---

## §7 依赖归档引用

### manifest.yaml 记录

编译依赖完成后，在主软件的 `manifest.yaml` 中记录所有依赖信息：

```yaml
# archives/p/python/3.9.0/manifest.yaml
name: python
version: 3.9.0

dependencies:
  required:
    - name: openssl
      version: 1.1.1w
      archive: archives/o/openssl/1.1.1w
      install_prefix: $HOME/usr/openssl-1.1.1w    # 如果使用了隔离环境
      reason: "_ssl and _hashlib modules (HTTPS support)"
    - name: zlib
      version: 1.3.1
      archive: archives/z/zlib/1.3.1
      install_prefix: $HOME/usr/local               # 标准安装位置
      reason: "_zlib module (zip/gzip support)"
  optional:
    - name: readline
      version: 8.2
      archive: archives/r/readline/8.2
      install_prefix: $HOME/usr/local
      reason: "readline module (command line editing)"
      status: installed
    - name: ncurses
      version: 6.4
      archive: archives/n/ncurses/6.4
      install_prefix: $HOME/usr/local
      reason: "_curses module (terminal UI)"
      status: installed
    - name: gdbm
      version: 1.23
      archive: archives/g/gdbm/1.23
      reason: "_gdbm module (database support)"
      status: skipped  # 未安装
```

### 归档记录的价值

1. **可复现性**：通过 manifest 可以完整重现编译环境
2. **依赖追踪**：清晰记录每个依赖的安装位置和版本
3. **故障排查**：当软件运行异常时，可追溯依赖链
4. **批量更新**：当需要升级某个依赖时，可快速定位所有受影响的软件

### 归档目录结构

```
archives/
├── o/openssl/1.1.1w/
│   ├── manifest.yaml          # openssl 自身的编译记录
│   ├── patches/               # 应用的补丁
│   │   └── 01-harmonyos.patch
│   └── build.log              # 编译日志
├── z/zlib/1.3.1/
│   ├── manifest.yaml
│   └── build.log
├── n/ncurses/6.4/
│   ├── manifest.yaml
│   ├── patches/
│   └── build.log
└── ...
```

---

## §8 循环依赖处理

### 什么是循环依赖

极少数情况下存在循环依赖：A 依赖 B，B 又依赖 A。

```
常见循环依赖场景：
  libA 依赖 libB（编译时需要 libB 的头文件）
  libB 依赖 libA（编译时需要 libA 的头文件）

  或者：
  A 需要 B 的库来编译
  B 需要 A 的工具来生成代码
```

### 策略 1：禁用导致循环的功能

最简单直接的方式：

```bash
# 如果 B 对 A 的依赖来自可选功能
./configure --without-feature-that-needs-A

# 示例：某些软件的测试框架依赖于自身的高层 API
# 编译时禁用测试即可打破循环
make -j$(nproc)  # 正常编译
# 跳过 make check
```

**适用场景**：
- 循环依赖来自可选功能
- 禁用后不影响核心功能

### 策略 2：分阶段编译（先静态库，再完整编译）

```
第一轮：编译 A 的静态库（不链接 B）
  ├── 生成 libA.a
  └── 不编译依赖 B 的部分

第一轮：编译 B（可以链接 libA.a）
  ├── 使用 libA.a 的头文件
  └── 生成 libB.a / libB.so

第二轮：重新编译 A（链接 B）
  ├── 此时 B 已可用
  └── 生成完整的 libA.so
```

**具体操作**：

```bash
# 第一轮：只编译 A 的静态库
cd libA
./configure --disable-shared --enable-static
make -j$(nproc)
# libA.a 现在可用

# 设置环境让 B 能找到 A
export CFLAGS="-I$(pwd)/include"
export LDFLAGS="-L$(pwd)/lib"

# 编译 B
cd ../libB
./configure
make -j$(nproc)
make install

# 第二轮：完整编译 A
cd ../libA
make clean
./configure --enable-shared --enable-static
make -j$(nproc)
make install
```

**适用场景**：
- 两个库互相依赖对方的头文件
- 可以通过先编译静态库来提供必要的接口

### 策略 3：使用系统预装版本打破循环

```
如果系统已预装 A 的某个版本：
  ├── 使用系统预装的 A 来编译 B
  ├── 编译完 B 后，再编译新版 A（链接新版 B）
  └── 如果版本兼容，也可以直接使用系统版本
```

**具体操作**：

```bash
# 检查系统是否预装
pkg-config --exists libA && echo "System has libA"

# 如果有预装版本，先用它编译 B
./configure --with-system-libA
make -j$(nproc)
make install

# 然后编译新版 A
cd ../libA
./configure --with-libB=$PREFIX
make -j$(nproc)
make install
```

**适用场景**：
- 系统预装的版本可以满足 B 的编译需求
- 不需要最新版本的 A

### 循环依赖决策树

```
发现循环依赖 A ↔ B
  │
  ├─ 可以禁用导致循环的功能？
  │   ├─ 是 → 使用策略 1（禁用功能）
  │   └─ 否 ↓
  │
  ├─ 可以分阶段编译（先静态库）？
  │   ├─ 是 → 使用策略 2（分阶段编译）
  │   └─ 否 ↓
  │
  └─ 系统有预装版本可用？
      ├─ 是 → 使用策略 3（系统预装）
      └─ 否 → 记录为已知问题，考虑替代方案
```

### 已知循环依赖案例

| 软件 A | 软件 B | 循环原因 | 解决策略 |
|--------|--------|----------|----------|
| glib | gobject-introspection | g-i 需要 glib 编译的 .gir 文件 | 策略 1：禁用 g-i |
| gcc | libgccjit | gcc 需要链接自身运行时 | 策略 2：分阶段编译 |
| (待补充) | (待补充) | (待补充) | (待补充) |

---

## 附录：依赖检测命令速查

```bash
# 检查库是否已安装
pkg-config --exists <name> && echo "installed" || echo "not found"
pkg-config --modversion <name>

# 检查头文件
find $PREFIX/include -name "<name>.h" 2>/dev/null

# 检查库文件
find $PREFIX/lib -name "lib<name>*" 2>/dev/null

# 检查可执行文件
which <name> 2>/dev/null
<name> --version 2>/dev/null

# 查看 configure 能识别的选项
./configure --help | grep -i "<name>"

# 查看 pkg-config 数据库
ls $PREFIX/lib/pkgconfig/<name>.pc 2>/dev/null
cat $PREFIX/lib/pkgconfig/<name>.pc
```

---

*最后更新：2026-03-30*
*相关文档：[dependencies.md](./dependencies.md)（静态依赖图）、[environment.md](./environment.md)（环境变量配置）、[harmonyos-specifics.md](./harmonyos-specifics.md)（鸿蒙特有问题）*
