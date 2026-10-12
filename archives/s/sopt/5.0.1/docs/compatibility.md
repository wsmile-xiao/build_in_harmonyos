# SOPT 5.0.1 兼容范围

实测范围为OHOS7 Beta AArch64 QEMU的单进程CPU配置。
Eigen数值算法、TIFF读写、小波和logger通过完整配置上游测试及安装包消费者验证。
MPI/OpenMP/ONNX关闭；尚无这些可选路径、正式OHOS6真机或远端CI验证。
上游v5.0.1发布常量为5.0.0，因此SO版本为5.0.0；保留该身份差异。
