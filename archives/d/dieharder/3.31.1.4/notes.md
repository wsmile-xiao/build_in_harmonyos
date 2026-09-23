# dieharder 3.31.1.4 编译笔记（HarmonyOS PC · 标准 Conan autotools）

## 定位
- 产动态 libdieharder.so.3（libtool -version-number 3:31:1，实测 SONAME=libdieharder.so.3，
  文件 libdieharder.so.3.31.1）+ bin/dieharder CLI，供链接与直接使用。
- 消费方契约：libdieharder.so 把 CLI 全局状态（verbose/rng/dh_rng_types/dh_test_types/
  ks_pvalue 等约 50 个符号）留空由使用方提供（上游 dieharder/globals.c 为唯一定义点，
  R 接口同款）；musl 立即绑定，漏定义在链接/加载期即报 undefined symbol。

## 关键适配
- tarball 无 config.guess/config.sub（上游靠维护者 autogen.sh，未入库）：patches/0001
  vendor GNU config master 副本（GCC 仓同步版，Copyright 1992-2021）到源码根目录；
  configure 再用 `--build/--host=aarch64-unknown-linux-musl` 显式三元组（gsl 同款）。
- 设备 HNP bash 的 getcwd() 在 spawn cwd 上不可靠（errno 随机）：generate() 显式导出
  与 build 目录一致的 PWD，configure/make/libtool 全部恢复（否则 configure 报
  "working directory cannot be determined"）。
- configure 就地 `umask 077`→`022`（build() 内替换，gsl 同款；不改上游文件、无 patch）。
- 依赖注入：AutotoolsDeps 把 gsl 的 -I/-L/-l 喂给 configure/make；另 prepend LD_LIBRARY_PATH
  保证原生 conftest 可加载依赖 .so。
- make -j1（R9：HMDFS jobserver fifo EPERM）。

## 上游测试
- 无 make check/ctest。官方测试入口 = dieharder CLI：
  test_package 跑 `-l` 冒烟 + `-d 0/2/13 -p 3 -S 42` 固定种子子集 + 链接探针；
  全量 `-a`（31 模块，默认 psamples=100）为小时级、超 CI 单包窗口，CI 通过后由
  Builder 于真机对同一构建产物补跑并留存日志（本机 run 目录 upstream-tests/）。

## 状态
built（CI conan create + test 通过）
