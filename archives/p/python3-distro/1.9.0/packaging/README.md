# packaging — python3-distro 1.9.0

纯 Python noarch 包，打包产物由 Conan 管理（conan create 生成
lib/python3.12/site-packages/distro + bin/distro），无独立源码
tarball 需要归档（JC3 合规：入库文件不包含 .tar.gz）。

发布路径：PR 合并 main 后由 CI release 流水线（build_and_test.sh →
upload.sh → sign.sh）将 conan 包上传至 CNB 制品仓（ohpcd remote）。

本地复现：`conan create archives/p/python3-distro/1.9.0
-pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64`
