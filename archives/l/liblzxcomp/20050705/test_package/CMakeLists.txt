cmake_minimum_required(VERSION 3.15)
project(test_liblzxcomp C)

find_package(liblzxcomp REQUIRED)

# 1) 消费者测试（鸿蒙特有测试）：内存后端构造 512KB 可压缩数据，
#    调用真实 API lzx_init / lzx_compress_block / lzx_finish 并断言压缩有效。
add_executable(test_liblzxcomp test.c)
target_link_libraries(test_liblzxcomp liblzxcomp::liblzxcomp)

# 2) 上游自测程序：lzx_test.c 为上游 2005 发行包自带的测试源文件，字节级原样复制
#    （sha256 217d2002d7f71586ddf1d45c6fbdb1d05055fd29d7df5b4deb763c98a061dad2），
#    未改动一行；对应上游 Makefile 的 lzx_test2 目标（链接 liblzxcomp.a 的对象集）。
add_executable(lzx_test2 lzx_test.c)
target_link_libraries(lzx_test2 liblzxcomp::liblzxcomp)

# 上游 lzx_test.c 要求 stdin 是可 seek 的普通文件（fseek/ftell 取输入总长度），
# 因此在配置阶段生成一份确定性语料，供 conanfile.py test() 重定向为 stdin。
string(REPEAT
  "OpenHarmony PC liblzxcomp upstream lzx_test2 corpus 20050705 - window sliding LZ77 with Huffman coding. "
  1400
  _lzx_corpus)
file(WRITE "${CMAKE_CURRENT_BINARY_DIR}/upstream_in.bin" "${_lzx_corpus}")

enable_testing()
add_test(NAME test_liblzxcomp COMMAND test_liblzxcomp)
