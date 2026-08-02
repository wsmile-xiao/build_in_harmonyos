# ecKit

ECMWF 的 C++ 工具库。fckitlib 经 eckitlib==2.0.7.19 依赖它

上游：https://github.com/ecmwf/eckit

## 鸿蒙 PC 适配要点

- MPI 关闭仍产出 libeckit_mpi.so（串行 fallback），下游 fckitlib 的 DT_NEEDED 得到满足
- AEC 走 modern target（libaec::aec）、LZ4 走老式变量（LZ4_INCLUDE_DIRS）——同库两种风格并存
- 三个 musl 补丁：uid_t 未声明 / strerror_r 只有 POSIX 版 / 无 pthread_cancel
- 迭代时须 --build="eckit/*"：--build=missing 不会因改配方而重建
