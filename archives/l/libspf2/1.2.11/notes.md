# libspf2 1.2.11 编译笔记

## 编译步骤
1. 定义 NETDB_SUCCESS=0
2. 定义 res_close=空操作
3. ./configure && make

## 交付物
- 库文件: libspf2.so, libspf2.a
- 工具: spfquery, spfd
