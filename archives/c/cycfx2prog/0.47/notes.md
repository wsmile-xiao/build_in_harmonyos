# cycfx2prog 0.47 适配笔记

## 编译环境

- 构建系统: makefile（上游手写 Makefile，无 configure）
- 编译日期: 2026-09-11
- 编译器: clang 15.0.4（`/data/service/hnp/bin/clang`，profile `ci/conan/profiles/ohos-aarch64`）
- 目标平台: OHOS 6.0 / armv8（aarch64）
- 状态: built（conan-verify/W3 通过；release upload 未确认）

## 编译步骤

上游 Makefile 只有 `all/clean/distclean/dist` 目标（无 `install`、无 `check/test`），因此配方
不调用 `make install`，而是：

1. `get(self, **self.conan_data["sources"], strip_root=True)` 取官方 tarball（顶层目录
   `cycfx2prog-0.47/`，4 个文件）；
2. `apply_conandata_patches(self)`（零补丁，no-op）；
3. `make -j1 CC='<profile clang>' CFLAGS='<tc.cflags + -D defines + -I 依赖头目录 + 上游自带
   告警 flags + -DCYCFX2PROG_VERSION=\"0.47\">' LDFLAGS='<tc.ldflags + -L 依赖库目录 +
   -lusb -lusb-1.0>'`（R9：小工程保持单 job）；
4. `copy()` 显式安装 `bin/cycfx2prog`。

原生（裸 make）与 Conan 两条路径都实跑过，命令与原始结果见 `manifest.yaml` 的
`validation.native_build` / `validation.conan_create`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 首轮原生构建后 `--version` 会打印垃圾，编译只有 2 条 `-Wformat` 告警 | 上游 Makefile 用 `=` 赋值 `CFLAGS`，必须以 make **命令行变量**覆盖；命令行变量的值会被解析两次（make 展开 + recipe shell），配方里只写一级 `\"` 时反斜杠在调用 shell 就被吃掉，宏 `CYCFX2PROG_VERSION` 从字符串退化成 `double` | 写成两级转义并放进 shell 单引号参数：`-DCYCFX2PROG_VERSION=\\"0.47\\"`；`--version` 随后输出 `cycfx2prog version 0.47`（知识条目 E575） |
| 2 | OHOS 上没有 libusb-0.1 本体，按名字找不到 `libusb/0.1.x` | 制品仓提供的是 `libusb-compat/0.1.7`（0.1 API 兼容层，静态 fPIC）与 `libusb/1.0.27`（真正的 USB 实现）两个包名 | `requires("libusb-compat/0.1.7")`，链接 `-lusb -lusb-1.0`；不写 stub、不加平台条件编译（知识条目 E574） |
| 3 | `test_package` 首轮 `bash: test.sh: No such file or directory` | test_package 加了 `basic_layout()` 后测试运行目录是 `<test_package>/build-release`，不是 test_package 源目录 | `self.run(..., cwd=self.source_folder, env="conanrun")` 显式指定目录（保留 `layout()`：不定义它会让构建残留落进包源目录，见 workflow 第 5.3 节） |
| 4 | 无 USB 设备的环境里 `--list` 是否算"未验证" | `--list` 走到 `usb_init()`/`usb_find_busses()`/`usb_find_devices()` 才打印，三者都必须成功才 exit 0 | 把 `--list` 的退出码 0 + 两条 "usb_find_* failed" 反断言纳入 test_package，作为 libusb 真实运行路径的证据（源码位置 `cycfx2prog.cc:212-222`） |

## 源码修改

无。0.47 用 OHOS clang 15 原样编译通过（唯一告警是上游自带的 `cycfx2dev.cc:98` 与
`:177` 的 `-Wunused-but-set-variable`），`patches/` 目录不存在，R8 无豁免项。

## 依赖版本

- 编译依赖：`libusb-compat/0.1.7`（它 `requires` `libusb/1.0.27`）、profile 中的 clang 15.0.4
- 运行依赖：`libusb-1.0.so.0`（`DT_NEEDED`）、`libc.so`（OHOS musl）

## 验证结果

命令与原始结果以 `manifest.yaml` 的 `validation.*` 为权威副本（本节不复制）：

- `validation.source_fetch`：官方源 HTTP 200 / 8768 字节 / sha256 `0e2669c11e81…`
- `validation.upstream_ledger`：上游测试入口计数 0
- `validation.w0_dependency` + `dependency_feature_check`：依赖 binary 可装，0.1 API 符号 27 个
- `validation.native_build`：`make` rc=0，`--version`/`--help`/`--list` rc=0，无参数 rc=1
- `validation.conan_create`：`conan create` rc=0，零补丁
- `validation.test_package`：`TOTAL=33 PASS=33 FAIL=0`
- `validation.l1e_negative`：破坏产物后 `TOTAL=33 PASS=8 FAIL=25`、rc=1
- `validation.package_contents`：包内只有 `bin/cycfx2prog`
- `validation.conan_verify_supplement`：G4/L2/L4/L5 人工补测全部 PASS（工具对 application 包整组跳过）
- `validation.conan_create_round`：提交版 `reports/conan-create.log` 产自 tip 轮（`RUN: make` ×1、`Calling build()` ×1、33/33），与 PR 内最终 `test_package/` 严格对应
- `validation.w3_local_ci`：W3 的 L0/L1/L4/L5 pass、L1e 反向验证确认、通过率 100.0%（1/1）
- `validation.w3_l2_skip`：W3 的 L2 探针 skip 属探针运行环境问题，人工补测为 PASS
- `validation.finish_exit`：finish `EXIT_REASON: finish_success`，失败步骤全在 workflow 第 7.2 节白名单内

## 注意事项

- **未覆盖范围**：需要真实 Cypress EZ-USB FX2/FX2LP 芯片的路径（`-d=`/`-id=` 命中设备后的
  `prg:` 固件下载、`run`/`reset`、`dbulk:`/`sbulk:`/`fbulk:`/`bench_bulk:`/`ctrl:` 端点收发）
  在无硬件的 CI 环境无法执行。这是上游的硬件依赖，不是 OHOS 平台缺陷；已在
  `test_package/MANIFEST.yml` 的 `not_covered` 中逐项列明。
- **不要用包内 `libusb.pc` 定位依赖**：其 `prefix` 固化在打包机路径
  （`/storage/Users/currentUser/.cache/conan2/p/b/libus8c4e8f03c5cab/p`），本机不存在；
  配方改为从 `cpp_info` 取 `-I/-L`。
- 设备 `/tmp` 与 `umask` 相关的构建期限制在本包未触发（上游只编译 4 个文件、无临时文件
  生成步骤）。
