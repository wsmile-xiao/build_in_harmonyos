# cheops 1.3 — 适配记录

> 上游: https://github.com/logological/cheops/releases/download/1.3/cheops-1.3.tar.bz2
> sha256: a3ce2e94f73068159827a1ec93703b5075c7edfdf5b0c1aba4d71b3e43fe984e
> 工程类型: autotools (autoconf 2.57 起 / 2016 生成 configure); C++03 console 程序 (bin_PROGRAMS=cheops)

## 结论快照
- 产物: `bin/cheops` 可执行文件（console 象棋），man6/cheops.6 + 文档数据装入包。
  `package_type: application`，无库 / 无头文件，无 commands.json 之外的工具登记见 name-level。
- 上游自动化测试: **0**。无 check/ctest/test 目标；为交互式人机对局程序。
- 反空壳 / 功能冒烟（test_package）: 见 `test_package/test_cheops.sh` ——
  `--version` 与 `--help` 退出码为 0 且输出含版本/用法；随后以
  `h h e2e4 e7e5 quit`（双人、两着棋、退出）驱动真实对局循环，退出码 0 且含 `Command:` 提示。

## OHOS 关键适配（详见 conanfile.py）
1. 发布包**不含 config.guess/config.sub** → 打包 FSF 2024 版（`files/`，aarch64 已支持，
   同 ncmpcpp 配方技法）在 build() 拷入源码根并 chmod +x。
2. `--build=aarch64-unknown-linux-gnu` 固定编译三元组，跳过 config.guess（无法猜 HarmonyOS）。
3. configure/config.guess/sub 内 `umask 077`→`umask 022`；TMPDIR → conan build `_tmp`
   （HMDFS 临时目录组写权限问题，同 pakchois/p11-kit/encript）。
4. doc 的 PDF 生成在 `HAVE_PDFLATEX` 条件内（设备无 pdflatex 自动跳过）；man6 预生成直接安装。
5. `package_type: application`；`validate()` os 白名单 Linux/OHOS（R32）。
6. 设备 profile `cppstd=17` 下，2003 代码里的 `register` 存储指示符（C++17 已移除）会被
   clang 15 判错 —— `src/ChessBoard.cpp:418` 唯一一处 `register bool white=is_white` 去掉
   该指示符（语义不变），见 conanfile `_drop_cxx17_register()`。

## 验证记录（true-device Harmony verify 后回填）
- [ ] HARMONY_VERIFY conan create PASS
- [ ] test_package 冒烟输出确认
- [ ] L0/L1/L4/L5 / CI 结果
