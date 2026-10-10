Conan 配方包（conanfile.py），打包产物由 `conan create` 生成并上传至 CNB 制品仓。

本目录为归档占位（本仓 375 个 `packaging/` 目录均不含 tar.gz，交付物统一为 conan 包）。

- 包引用：`tunnelx/20190701@ohpcd/stable`
- 安装：`conan install --requires=tunnelx/20190701`
- 内容：`lib/tunnelx.jar`（Java 应用，`Main-Class: Tunnel.MainBox`）+ `bin/tunnelx` 启动器
- HarmonyOS 运行依赖：BiSheng OpenJDK 17.0.13（HNP 预装 `~/bishengjdk17`，或官方 `cmd-pkgs` 通道）
