# libbigwig

libbigwig (libBigWig) 是一个 C 语言实现的 bigWig / bigBed 文件读写库,是 UCSC Kent 源码的轻量替代。

## 简介

bigWig / bigBed 是生物信息学中广泛使用的二进制基因组数据格式(压缩、支持随机访问与缩放视图)。
libBigWig 通过 zlib 实现数据压缩,通过 libcurl 支持本地与远端(HTTP/FTP)文件访问,
被 pyBigWig、cpp11bigwig、bw-python 等下游项目使用。

## 主要特性

- 读写 bigWig 与 bigBed 两种格式
- 支持本地文件与 libcurl 远端访问(可经 `WITH_CURL` 关闭,关闭后定义 `NOCURL`)
- 基于 zlib 的块级压缩与多级缩放(zoom level)索引
- 区间/区间跨度/定步长三类数据块写入接口与重叠区间迭代查询接口
- 纯 C11 实现,仅依赖 zlib 与 libcurl(可选),无平台专属系统调用

## 鸿蒙适配说明

- 构建系统: CMake(≥3.8),配方注入 `BUILD_SHARED_LIBS`/`WITH_CURL`/`ENABLE_TESTING`
- 依赖: zlib/1.3.1.1、curl/8.15.0(均取自 ohpcd 制品仓)
- 源码无平台专属 API,未打补丁,直接交叉编译通过
- 本版本随包附消费者测试(test_package): 写入→重开→逐条读回断言

## 上游地址

- 仓库: https://github.com/dpryan79/libBigWig
- 许可: MIT
