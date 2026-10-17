# moe 1.5 适配笔记

## 编译环境
- **构建系统**: 上游手写 configure + Makefile.in（非 autoconf/automake）
- **编译日期**: 2026-09-16
- **编译器**: clang（OHOS 工具链，configure 的 CXX 默认 g++ 已覆盖为 clang++）
- **平台**: arm64-ohos（OpenHarmony PC）
- **状态**: built（Conan 配方验证通过——conan create 全绿，一次构建通过）
- **补丁数量**: 0
- **依赖**: ncurses/6.6（终端 UI；上游 Makefile 硬编码 `-lncurses`，包侧导出 `ncursesw`）

## 编译步骤（conan create 全流程）

```bash
conan create archives/m/moe/1.5 --build=missing
```

### 1. 源码获取（source()）
```bash
tar -xzf moe-1.5.tar.gz --no-same-owner || true
cp -a moe-1.5/. . && rm -rf moe-1.5
```

### 2. 配置（configure）——手写脚本，位置参数传值
moe 的 configure 不是 autoconf 产物：它只解析自己的选项，编译相关变量必须
以**位置参数**给出（环境变量形式不生效），且默认 `CXX=g++`：
```bash
./configure --prefix=/usr CXX=clang++ \
  CPPFLAGS='-I<ncurses>/include' \
  CXXFLAGS='-O2 -Wno-error' \
  LDFLAGS='-L<ncurses>/lib'
```

### 3. 编译（make）——链接库覆盖
上游 Makefile 内硬编码 `LIBS = -lncurses`；ncurses/6.6 的 conan 包导出
`ncursesw`（宽字符版，`cpp_info.libs = ["formw","menuw","panelw","ncursesw"]`）：
```bash
make -j2 LIBS='-lncursesw'
```

### 4. 上游测试（清点结论：无自动化测试——R51 附证据）
- 仓库顶层无 `tests/` / `test/` 目录（仅源码 `.cc/.h`、`doc/`、`moerc` 与打包文件）；
- `Makefile.in` 的 `check` 目标为占位实现：
  ```make
  check : all
  	@echo "No tests yet defined for $(pkgname)-$(pkgversion)"
  ```
- 无 automake TESTS / CMake add_test / pytest 注册入口。
→ 上游测试数如实记 0；真实行为测试由消费者测试（test_package）承担。

### 5. 打包（package()）
```bash
make install DESTDIR=<package_folder>
```
安装布局：`usr/bin/moe`（主程序）、`usr/etc/moerc`（系统配置）、`usr/share/man/*`；
`package_type = "application"`，`package_info.bindirs = ["usr/bin"]`。
软件级 `commands.json` 声明 CLI（type=tool, binary=true）。

## 验证结果
- **构建**: `moe/1.5: Package created`（conan create 全绿，一次构建通过）
- **上游测试**: 上游无自动化测试（清点证据见上，N_static=0）
- **R34 消费者验证**: test_package — 运行被测二进制并断言行为：
  - `moe --version` → 输出 `GNU Moe 1.5`（断言含 1.5，退出码 0）
  - `moe --help` → 输出用法（退出码 0）

## 已知限制
- 上游 1.5 为 2015 年版本（登记备注：新版 1.9 tarball 不存在于镜像；1.5 为可用的稳定 tarball）。
- `make install` 的 `install-info` 步骤因环境无 `install-info` 工具而忽略（非致命，上游脚本 `-` 容错）。
- moe 为交互式编辑器；消费者测试仅覆盖非交互的 `--version/--help` 路径（编辑交互需终端，不属自动化测试范围）。
---

**编译结束**: 2026-09-16 01:18
**最终状态**: built
