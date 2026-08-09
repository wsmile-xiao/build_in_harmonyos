#!/bin/bash
set -euo pipefail
# 本 recipe 的生成命令（由 conan_packager.py gen 自动记录）。
#
# 重生成时**照这个改**，别凭 conanfile.py 反推参数：漏一个 flag 就静默少一项能力，
# 而且往往是构建装包全绿、下游才炸（graphviz 漏了 --post-install-cmd "bin/dot -c"，
# 插件索引 config8 不再生成，dlopen 全失效）。
#
# --out/--src 未记录（本地绝对路径），跑的时候自己补。
python3 <conan_packager.py 的路径> gen --name poco --version 1.15.3 --build-system cmake --source-url https://github.com/pocoproject/poco/archive/refs/tags/poco-1.15.3-release.tar.gz --sha256 4f112fea59e0c65f0fffe30a4957f8d66cf41528c21dd9903e6d7550022c794e --requires openssl/3.5.6 --libs PocoNetSSL,PocoNet,PocoCrypto,PocoJWT,PocoUtil,PocoXML,PocoJSON,PocoEncodings,PocoZip,PocoDataSQLite,PocoData,PocoMongoDB,PocoRedis,PocoPrometheus,PocoActiveRecord,PocoFoundation --cmake-def ENABLE_TESTS=OFF --cmake-def ENABLE_SAMPLES=OFF --test-lang cpp --test-header Poco/Foundation.h --homepage https://pocoproject.org/ --sign-so --out <输出根目录>
