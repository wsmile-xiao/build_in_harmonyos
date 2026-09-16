# units 2.22 适配笔记

## 编译环境
- 构建系统: autotools（tarball 自带 configure，无 Makefile.am 的扁平手写 Makefile.in）
- 编译日期: 2026-09-14
- 编译器: clang 15.0.4（OHOS aarch64）
- 状态: built

## 编译步骤

1. init-build 从官方 URL 下载 tarball（sha256=5d13e120…2584848）。
2. 手动探索构建（Mode B Step 2）：`sed -i 's/umask 077/umask 002/' configure` 后
   `CC=clang ./configure --build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu --prefix=…` →
   `make -j1` → `make check`，全部在设备原生执行（日志 ~/tmp/uc2/units-2.22/manual-build.log）。
3. `conan-init` 生成骨架后手写配方（以归档 bc/1.07.1 为范式，application 类型），
   `conan-verify` 完成 conan create + 消费者测试验证。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 阶段 `umask 077` mktemp 探针 | HMDFS 权限组合使 config.status 临时目录不可写（E011 同源） | 配方 build() 中 replace_in_file 放宽为 umask 002 |
| 2 | `autotools.install()` 失败：Makefile:161 install-info Error 1 | install-info 依赖重新生成 units.info，需要 makeinfo，OHOS/CI 环境没有 | build() 中将 `install-doc: install-man install-info` 改为 `install-doc: install-man`（bc/1.07.1 同源先例；tarball 自带 units.info 但规则按时间戳判定需重生成） |
| 3 | config.sub 不识别 linux-ohos triplet | 2021 年代 GNU 项目 config.sub 无 ohos 支持 | `--build`/`--host` 均传 aarch64-unknown-linux-gnu（vo-aacenc/0.1.3 先例） |
| 4 | install 后 share/units/currency.units 符号链接失效 | install-support 装到 $sharedstatedir/units($prefix/com) 并留下 DESTDIR 绝对路径链接，包移动后悬空 | package() 拍平：删链接→复制实际文件→rmdir com/ |

## 源码修改

无补丁文件（patches 为空）；全部适配动作在 conanfile.py build()/package() 内完成（configure 与 Makefile.in 的两处 replace_in_file + 打包拍平）。

## 依赖版本

无第三方依赖（readline 为可选自动探测，交叉构建探测不到即禁用；python3 缺失仅影响 units_cur 安装，不影响 units 本体）。

## 上游测试四维账本

- 上游静态声明总数（check 目标，逐项核对 Makefile.in）：**2**
  1. `currency-update-check`：运行 units_cur 联网刷新汇率数据（带 `-` 容错前缀，环境探测，非功能断言）
  2. 功能校验：`units -f definitions.units '(((square(kiloinch)+2.84m2) /0.5) meters^2)^(1|4)' m` 应输出 6
- 实际注册/可执行：2（check 目标整体可执行）
- 设备实跑（manual-build.log）：功能校验 **通过**（输出 "Units seems to work"，表达式求值=6）；currency-update-check **失败**（exit 127，该 shell PATH 无 python3，未及联网；容错前缀下不影响 check 总体退出码 0）→ 通过率口径：功能校验 1/1，currency 探测属环境受限项
- 新增消费者测试：1 个程序（test_package/test.sh，3 处断言：--version 冒烟、meter→foot 换算、上游 check 表达式=6）

## 验证结果

```bash
# 手动探索构建（设备原生）
$ make check
Trying to update currency.units
./units_cur currency.units.test        # 127, 容错忽略
Currency update failed
Checking units
Units seems to work
makecheck_exit=0
```

## 交付物

| 文件 | 说明 |
|------|------|
| bin/units | units 可执行文件（application） |
| share/units/definitions.units | 单位定义数据文件 |
| share/units/currency.units | 汇率数据（已拍平至同目录） |
| share/units/locale_map.txt | 本地化映射 |
| commands.json（软件级） | R38 可执行产物声明 |

## 注意事项

- units 是 application（非库）：package_type=application、cpp_info.bindirs=["bin"]、软件级 commands.json 必备。
- 消费者测试用 `-f <包>/share/units/definitions.units` 显式指定数据文件，绕开 DATADIR 编译期路径与运行时工作目录差异。
- 赛道二消费者测试属"运行被测程序并断言行为"形态（application 无库可链接）。
---

**编译结束**: 2026-09-14 01:22
**最终状态**: built
