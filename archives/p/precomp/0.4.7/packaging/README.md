# packaging — precomp 0.4.7

v3.0 Conan 配方模式（R19/R20）：产物即 `conan create` 生成的 Conan 包
（precomp/0.4.7@ohpcd/stable，ohos-aarch64 profile），经 CI release 流水线
`conan upload` 发布到 ohpcd 制品仓，不再手动维护 tar.gz 制品入库。

本目录在适配机上另保有 PackageBuilder 产物（不入库，根 .gitignore
排除 *.tar.gz）：precomp-0.4.7-ohos-aarch64.tar.gz（1093KB，含 strip +
ELF 签名后的 bin/precomp）与 -debug 符号包，用于本机分发验证；
包内容与测试证据见 ../reports/test-report.md。
