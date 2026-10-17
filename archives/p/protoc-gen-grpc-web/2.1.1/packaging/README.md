# packaging — protoc-gen-grpc-web 2.1.1

v3.0 Conan 配方模式（R19/R20）：产物即 `conan create` 生成的 Conan 包
（protoc-gen-grpc-web/2.1.1@ohpcd/stable，ohos-aarch64 profile），经 CI release
流水线 `conan upload` 发布到 ohpcd 制品仓，不再手动打包 tar.gz。

包内容（bin/protoc-gen-grpc-web 单可执行文件，静态链接 protobuf/absl，仅依赖
系统 libc/libc++_shared）见 ../reports/test-report.md 交付物一节。
