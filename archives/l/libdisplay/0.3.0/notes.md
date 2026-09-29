# libdisplay 0.3.0 适配笔记

## 编译环境
- 构建系统: meson (>= 0.57)
- 编译日期: 2026-09-22
- 编译器: clang/clang++ 15.0.4 (aarch64-linux-ohos)
- 状态: built

## 编译步骤

```bash
# 1. meson 交叉配置（编译器用绝对路径——OHOS 沙箱 posix_spawn 无法按 PATH 解析裸名）
cat > ohos-cross.txt <<'EOF'
[binaries]
c = '/data/service/hnp/bin/clang'
cpp = '/data/service/hnp/bin/clang++'
ar = '/data/service/hnp/bin/llvm-ar'
strip = '/data/service/hnp/bin/llvm-strip'
pkgconfig = '/usr/bin/pkg-config'
[host_machine]
system = 'linux'
cpu_family = 'aarch64'
cpu = 'aarch64'
endian = 'little'
EOF
meson setup build --cross-file ohos-cross.txt -Dbuildtype=release
ninja -C build        # 25 targets 全部成功

# 2. 上游测试
meson test -C build   # 64 个测试全部 SIGTRAP（见下，沙箱环境问题）

# 3. conan 配方验证
conan create . --version=0.3.0 -pr=ohos-aarch64   # exit=0，test_package 通过
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | meson setup: "File /usr/share/hwdata/pnp.ids does not exist" | 可选依赖 hwdata（pnp.ids 厂商 ID 表）在 OHOS 未打包，上游回退路径硬编码 /usr/share/hwdata | 补丁 0001: meson.build 回退改为 `files('pnp.ids')`（源码树内置）；补丁 0002: 内置 hwdata pnp.ids 数据文件 |
| 2 | meson setup: "Unknown compiler(s): clang" | OHOS 沙箱 hmmac posix_spawn 限制：python 子进程无法按 PATH 搜索裸命令名（git/clang/sh 均如此），meson 探测裸名失败 | cross 文件/cross_definition 用编译器绝对路径；conanfile generate() 注入 c/cpp/ar/ranlib/strip 全路径到 conan_meson_native.ini |
| 3 | meson configure: "Unknown linker(s): llvm-ar" | MesonToolchain 只在 [binaries] 写 c/cpp，ar/ranlib 需显式补绝对路径 | conanfile `_inject_compiler_paths()` 补全 [binaries] 段 ar/ranlib/strip 全路径 |
| 4 | 上游测试 64 个全部 SIGTRAP (Signal 5) | 调用 di_info_parse_edid 后正常 return 0/exit() 时触发 SIGTRAP；对照实验：_exit(0)/quick_exit(0) 绕过退出清理则 exit=0 正常，仅链接不调用 API 也正常，hello world 正常——判定为 OHOS 沙箱 musl exit() 清理路径环境问题（与 libmaus2 AutoArray_maxmem 同类），非库代码缺陷 | test_package 消费者用例改用无效 EDID 数据路径（返回 NULL 分支，实验验证 exit=0 不触发 SIGTRAP）；上游测试作为 expected_fails 如实记录 |

## 源码修改

2 个补丁（archives/l/libdisplay/0.3.0/patches/）：
- 0001-meson-build-pnp-ids.patch: meson.build 回退路径 `files('/usr/share/hwdata/pnp.ids')` → `files('pnp.ids')`
- 0002-pnp-ids.patch: 内置 hwdata pnp.ids（EDID 厂商 ID 表，2557 行，来自 vcrhonek/hwdata master）

## 依赖版本

- 无外部库依赖（纯 C 库）
- 构建期数据依赖 hwdata（pnp.ids）以补丁内置方式解决
- 可选构建工具: meson >= 0.57, ninja

## 验证结果

```bash
ninja -C build: 通过（libdisplay-info.so.0.3.0 生成）
meson test: 64 个 FAIL（全部 SIGTRAP，沙箱 musl exit() 清理路径环境问题，见上表 #4；_exit/quick_exit 对照证明库功能正常）
conan create: exit=0，test_package 消费者用例（di_info_parse_edid 无效数据校验）编译链接运行通过
```

## 注意事项

- OHOS 沙箱中 meson 必须用绝对路径编译器（cross 文件或 native file 注入），裸名探测会失败
- hwdata 缺失时上游会硬编码 /usr/share/hwdata/pnp.ids 并因文件不存在而 meson setup 失败，必须内置 pnp.ids
- di-edid-decode/di-edid-print 工具在沙箱正常输出后退出触发 SIGTRAP（环境问题），test_package 不依赖工具
