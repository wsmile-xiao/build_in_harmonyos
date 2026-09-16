# E429 — 已发布 conan 包内 *-config 脚本 prefix="/" 导致下游找不到头文件

## 错误特征

```
xapian-config --cxxflags  ->  -I//include
fatal error: 'xapian.h' file not found
Makefile: XAPIAN_CXXFLAGS = (空) / XAPIAN_LIBS = -L//lib -lxapian
```

## 触发条件
- 构建系统: autotools（configure 宏强制要求可执行 `*-config`，如 xapian.m4 的 XO_LIB_XAPIAN）
- 阶段: configure（探测通过后 build 编译期缺头文件）
- 前提: 依赖以 conan 发布包形式提供（包已上传制品仓并被下游安装）

## 根因分析
conan 2 的 Autotools.install 打包时把安装前缀重写为 `/`（可重定位约定），
`xapian-core` 发布包内 `bin/xapian-config` 的 `prefix="/"` 是该重写的静态残留。
脚本全部路径由 `${prefix}` 派生，于是 `--cxxflags/--libs` 报 `-I//include -L//lib`；
而 xapian.m4 即使 pkg-config 能找到库，也仍要求一个可执行的 xapian-config 并直接
采用其输出，故消费方编译必然缺头文件。依赖包本身无错，问题在消费侧。

## 解决方案

### 推荐方案
消费方配方 `generate()` 中：读取依赖包内 config 脚本，把唯一的 `prefix="/"` 赋值行
改写为依赖实际 `package_folder`，另存到 `self.build_folder/bin/xapian-config` 并
`chmod 0o755`（HMDFS 上实测生效），经 `Environment(scope="build")` 以 `XAPIAN_CONFIG`
导出。参考实现：`archives/o/omega/2.0.0/conanfile.py::_make_working_xapian_config`。

### 禁止做法
- ❌ 直接改写 conan 缓存/制品仓内依赖包内容（破坏包完整性与哈希）
- ❌ 把修正副本注入共享系统前缀（/usr/local 等，违反 R49/PF6）
- ❌ 用 `conan list/search` 判断包是否存在（R35）

## 验证
```bash
sh <generators>/../bin/xapian-config --cxxflags   # 应输出 -I<package_folder>/include
sh ... --ltlibs && sh ... --version               # -L<package_folder>/lib -lxapian / 2.0.0
```

## 关联条目
- 相关: E490（autotools 脚本可执行位保留）、R49（私有 prefix 注入原则）
- 来源 PR: feat/omega-2.0.0
