# akms 0.3.0 — HarmonyOS PC 适配

akms（Alpine Kernel Module Support，DKMS for Alpine）是纯 POSIX shell 工具（上游 https://github.com/jirutka/akms，MIT）。

## 构建
- 无 C 编译：build() 用 `sh -n` 校验脚本语法
- 上游 Makefile 的 man 目标需 asciidoctor（OHOS 无）→ 跳过 man 生成
- package() 直接复制脚本：bin/akms、libexec/akms/{akms-build,akms-runas}、share/kernel-hooks.d/akms.hook、etc/akms.conf

## 使用
- `akms --version` → "akms 0.3.0"；`akms --help` 正常
- 注意：akms 的内核模块构建功能为 Linux/Alpine 特定，本适配按工具打包（脚本可运行，`--version/--help` 正常）

详见 archives/a/akms/0.3.0/ 的 conanfile.py、manifest.yaml、test_package/。
