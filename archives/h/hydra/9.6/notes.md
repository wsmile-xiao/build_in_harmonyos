# hydra 9.6 编译笔记（HarmonyOS PC · 自定义 configure）

## 定位
- THC Hydra 网络登录破解工具，支持 50+ 协议；产物为可执行文件 hydra + pw-inspector。
- 上游：https://github.com/vanhauser-thc/thc-hydra（v9.6 tag）。

## 基本信息
- 构建系统: custom（自写 configure 脚本，非标准 autotools，无 configure.ac）
- 编译日期: 2026-08-17
- 编译器: clang 15.0.4（OHOS SDK）/ clang++
- 状态: built

## 编译步骤

```bash
# configure 是自定义 shell 脚本，检测可选库后生成 Makefile（Makefile.unix + Makefile.in + Makefile.am）
./configure --prefix=$PREFIX --disable-xhydra --nostrip --with-ssl=$OPENSSL_INC --with-ssl-lib=$OPENSSL_LIB
make -j1
```

- configure 前需将脚本内 `umask 077` 替换为 `umask 022`（HMDFS 权限兼容）。
- `--disable-xhydra` 禁用 GTK GUI（鸿蒙无 GTK）。
- 产物: `hydra`、`pw-inspector`、`hydra-wizard.sh`、`dpl4hydra.sh`。

## 关键适配

1. **package() 权限位**：`shutil.copyfile` 不保留源文件执行权限位，缺执行位会导致 test_package 运行报 Error 126；须显式 `os.chmod(0o755)`（知识 E098）。
2. **帮助命令退出码**：hydra 的 `-h/-H/--help` 退出码恒为 255（上游行为），test_package 不能依赖 `self.run` 退出码，应捕获 stdout 断言版本信息。
3. **依赖**：openssl/3.5.6（制品仓）；zlib 等可选库由 configure 自动检测，缺失的协议模块自动降级。

## 依赖版本

- openssl: 3.5.6（制品仓）
- zlib: system（OHOS sysroot）
- 编译器: clang 15.0.4（OHOS SDK）

## 验证结果

```bash
$ ./hydra -h
Hydra v9.6 (c) 2023 by van Hauser/THC & David Maciejak ...

$ ./pw-inspector -h
# 帮助命令退出码恒为 255，验证以 stdout 输出为准
```

- conan create 通过；test_package 断言 `hydra -h` 输出包含 "Hydra v9.6"。
- W3 本地 CI 模拟：Success 1/1（通过率 100%）。

## 打包产物

- bin/hydra、bin/pw-inspector、bin/hydra-wizard.sh、bin/dpl4hydra.sh
- licenses/README、licenses/LICENSE

## 注意事项

- hydra 是安全测试工具（网络登录破解），仅用于合法授权的渗透测试与安全研究场景。
- 部分协议模块（afp/firebird/mongodb/ssh/smb2 等）因 OHOS 无对应库未编译，`hydra -h` 会列出未编译的服务列表，属预期降级。
