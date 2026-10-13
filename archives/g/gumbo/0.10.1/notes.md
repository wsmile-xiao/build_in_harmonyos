# gumbo 0.10.1 适配笔记

## 基本信息
| 项目 | 值 |
|------|-----|
| 软件 | gumbo(Google HTML5 解析一致性库,html5lib 的 C 实现基础) |
| 版本 | 0.10.1(上游沉睡终版,2016) |
| 状态 | built |
| 构建系统 | 直驱编译(tag archive 只有 autotools 输入,无生成 configure/无 CMake) |
| 源码 | https://codeload.github.com/google/gumbo-parser/tar.gz/refs/tags/v0.10.1 |
| sha256 | 28463053d44a5dfbc4b77bcf49c8cee119338ffa636cc17fc3378421d714efad |

## 上游形态
- 纯 C89:tokenizer + parser,零外部依赖,零 config.h/HAVE_ 引用
  (grep 全源码证实——tag archive 的可移植性预设即"裸 libc 可编")。
- 预生成物齐全:char_ref.c(ragel 产物)、tag.c/tag_enum.h/tag_gperf.h/
  tag_sizes.h(gperf 产物)全部在树,无需 ragel/gperf。
- 产品:libgumbo.so.1.0.0(soname .so.1,上游 -version-info 1:0:0)/
  libgumbo.a + include/gumbo.h + include/tag_enum.h + gumbo.pc。
- 上游测试:未修改9个官方测试源，使用SHA固定的官方GoogleTest 1.7.0，
  原生框架注册与XML终态172/172；缺少框架不能声明上游测试为0。

## 配方设计
1. **直驱编译**:11 个 TU(src/{attribute,char_ref,error,parser,
   string_buffer,string_piece,tag,tokenizer,utf8,util,vector}.c)
   gcc -fPIC -O1 直编,共享库 -Wl,-soname,libgumbo.so.1 自行落
   libtool 版本化产物(subunit/libdbusmenu/krb5-wallet 同族先例)。
2. package():gumbo.h、其包含的tag_enum.h → include/;生成 lib/pkgconfig/gumbo.pc(镜像
   上游 pc.in);COPYING(Apache-2.0)。
3. 零补丁:上游零改动。

## 预验证(WSL glibc 全链路,提交前完成)
gcc:11/11 TU 编译零错误、libgumbo.so.1.0.0+libgumbo.a 链接成功、
消费者探针 **7/7 断言 PASS**(gumbo_parse/root 标签/元素计数×1/文本
节点计数/body 定位/首子 p/属性 id=a 取值)。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | tag archive 无生成 configure 也无 CMake | 上游只有 autotools 输入 | 直驱编译(预生成物在树+零 config 引用,11 TU 白名单) |
| 2 | 探针元素计数断言失败 | 文档含 br 自闭合元素,计数 7 非 6(断言笔误) | 修正断言;HTML5 void element 计入元素节点 |

## 已知限制(notes 如实声明)
- 不含 python 绑定(python/、setup.py)；GoogleTest是构建阶段的测试源码输入，
  不作为产品运行依赖或随包安装。
- 上游沉睡(2016 起无更新),0.10.1 即终版。

## 上游测试用例统计
- 上游自带:172个GoogleTest实际注册用例，原生全量172/172。
- 普通消费者:1个完整HTML5树形用例，7断言，不把7断言当7测试入口。
- 鸿蒙特有:1个HMDFS原生签名库加载、中文文件输入解析与清理用例，1/1。

## 2026-10-04 评审修复与证据边界

- CHECK仅累计失败却继续解引用out/root：增加显式提前退出和cleanup。
  Release/NDEBUG宿主定向控制5/5（4个失败路径+真实库正向）；不计入上游分母。
- get(strip_root=True)后不应再次拼gumbo-parser-0.10.1；公开gumbo.h必须连同
  tag_enum.h安装。两处均从实际解包布局/公开include关系修复。
- r001/r002因HMDFS投影属主与进程UID不相等而如实FAIL；r003绑定父目录存储
  身份并验证实际读写、签名dlopen、解析和清理，全量通过。
- W3 r003：upstream172/172、consumer1/1、harmony1/1、单次launch、进程清零、
  release/postrelease PASS；运行候选tree8170816507cbe3b83b342f9f1e111acd1d7a2e3d。
- Windows静态Conan create RC0。原生正式finish和修复HEAD的平台CI/Review仍
  必须独立完成，不以这些日志宣称提审。
- 本次必交知识草稿为E2026100404配对KV/MD，标题明确补充至PR#5346；
  旧R39/导入复盘草稿不作为本轮适配知识门禁证明。
