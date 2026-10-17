# onion 0.8 适配笔记

## 2026-10-05 当前事实（下方旧笔记仅保留为历史）

当前候选采用明确 `shared-library` 契约，不再声明无法控制上游产物的 `shared/fPIC` 选项。AtomCode 对旧 HEAD 的真实检视和逐项判断保留在 `reports/atomcode-r001-assessment.md`；`--list` 网络副作用意见由原测试宏顺序反证，未改动或弱化测试。最新独立事务 r020 上游89/89、消费者1/1、鸿蒙专项1/1、release/postrelease均PASS。配置SHA-256 `cbe944337252a1c659d9405ebd341f13844a7aa4df5a2f7e0c27e0dca69891f1`，终态快照 `406064157fe8d369b8b122dd6b484c5837bd41ceec035dbae41d6a67dfd34f8a`。正式 r013 实际Conan和本地CI通过，finish聚合RC1仍如实保留，不当作平台CI通过。下述r013/r019等旧事务仅为历史，不能覆盖r020身份。端口夹具依赖本版本安装的内部头文件和对应库共同冻结，不宣称跨版本ABI稳定性。

旧记录的“仅 pthread、零补丁、未采用上游测试、7个消费者用例”不再适用：消费者原来是1个场景的7个断言；禁用 TLS 后非 TLS WebSocket 仍需真实散列依赖。产品使用已发布 OpenSSL 3.5.8.1 公共 SHA1；完整测试使用已发布 curl 8.22.0、gettext 0.22.5.1 及闭包，W0精确RREV/PID/PREV留在任务证据中。

官方 v0.8 源码哈希不变；Conan 显式 filename `onion-0.8.tar.gz`，版本文件写 `0.8.0`。TLS/PAM/图像/XML/数据库/GC/C++ bindings/示例关闭，不能由非 TLS 散列成功宣称支持 HTTPS。pthread/epoll、普通 HTTP、模板、内存会话、非 TLS WebSocket 保留。

现代 CMake、版本脚本、HMDFS无版本链接SONAME、能力探测取消返回ENOTSUP、TMPDIR/mkstemp上传、私有端口/fork错误守卫等改动已固化。原测试修改如实披露：同 libc 空指针格式；AGPL固定载荷替代不存在的系统文件，保留完整字节断言；prerecorded分派/方法位、空值chunk刷新、有效裸POST key期望和重复释放修复。Ninja模板生成规则显式依赖 i18n 插件，解决正式构建的真实先后顺序失败。

17个补丁由官方 refresh-patch --auto 生成。r001的289文件重放匹配只对应旧集；追加i18n构建依赖后采用r002重放结果，不复用旧匹配结论。

新事务 `onion-20261005-r013`：配置启用的完整上游89/89（19个注册harness、2个原fixture的LF/CRLF四种运行、原资产工具场景），普通消费者1/1，鸿蒙签名库/HMDFS UTF-8真实HTTP响应1/1。非注册长期示例服务器不冒充无人值守测试；未启用功能的测试不宣称执行。前后校验、release/postrelease通过，自有进程0。

config SHA-256 `3441e989532adc7aa8d28b934f276baf457e512f71d0f4853e1cb193cd684aa3`；最终快照 `b6d6718b26e9fa48cc3fb898b65dd7fc26e863c3d1a3c1b23fe670bafca015fd`。r011失败/r012成功/正式前驱失败分别保留，不跨事务拼证据。配方真实 export_sources 导出补丁与包装器；curl 字面量是Conan依赖查询，不调用外部网络命令，不修改L0o检查器。

新知识配对草稿 E2026100502：关闭可选TLS不能删除非TLS协议必需散列闭包。是新机制而非补充草稿。正式Conan/finish、当前HEAD平台AI Review/CI与POST_CREATE仍为独立门禁；这里不宣称平台CI通过、发布或已提审。

## 以下为已被上述修复替代的 2026-10-03 历史笔记

## 基本信息
| 项目 | 值 |
|------|-----|
| 软件 | onion(C 语言 HTTP 服务库:路由/handler/模板/会话) |
| 版本 | 0.8(上游沉睡终版,2015) |
| 状态 | built |
| 构建系统 | 上游原生 CMake(可选项全部可关) |
| 源码 | https://codeload.github.com/davidmoreno/onion/tar.gz/refs/tags/v0.8 |
| sha256 | 9708ba74b6727fa2fef219a821241f21a661ea9a30611213b0133e7effab1b17 |

## 上游形态
- C 库 + CLI 工具(opack 资产打包/otemplate 模板编译/compilerunloop);
  可选依赖宽:SSL(GnuTLS)/PAM/PNG/JPEG/XML2/systemd/sqlite3/redis/GC,
  全部可经 CMake 变量关闭——本包全关,仅 pthreads(musl 原生)。
- 安装面:include/onion/*.h + libonion(共享+静态)+ pkgconfig +
  bin 三工具 + man 页。
- 上游测试:tests/(自研框架,ONION_USE_TESTS=false 未采用)。

## 配方设计
1. **第四形态(上游原生 CMake 直驱)**:选项映射 conan cache_variables,
   全可选依赖 OFF;pkgconfig/cmake-config 安装面由上游维护,零补丁。
2. **version 文件钉版本**:tag archive 无 .git,上游 git-version-gen
   会回退 "0.8.0.GIT" 弄脏版本与 soname——该脚本优先读源根 `version`
   文件,build() 写入 "0.8" 得干净 ONION_VERSION(知识草稿沉淀)。
3. **CLI 工具随安装面入库包**(opack/otemplate/compilerunloop 有真实
   用户价值),按 R38 落软件级 commands.json(binary: true)。
4. 许可证:AGPL-3 / Apache-2.0 双许可,四份许可文件随包。

## 预验证(WSL glibc 全链路,提交前完成)
cmake 3.22 + gcc:configure rc=0(全可选依赖 OFF)→ build rc=0 →
install(header/lib/pkgconfig/bin/man 齐)→ 消费者探针 **7/7 断言
PASS**:线程起真实 HTTP 服务(127.0.0.1:18099)→ 原生 socket 发
GET /hello → 断言连接成功/响应读取/HTTP 200/处理函数响应体。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | tag archive 构建版本变 0.8.0.GIT | 无 .git,git-version-gen 回退 DEF_VER | build() 钉源根 `version` 文件("0.8"),git-version-gen 优先读取 |
| 2 | 可选依赖拖链风险 | SSL/PAM/PNG/JPEG/XML2/systemd/sqlite3/redis/GC 默认全开 | CMake 变量全 OFF,仅 pthreads(musl 原生) |
| 3 | R38 CLI 义务 | cmake.install 装出 opack/otemplate/compilerunloop 三工具 | 软件级 commands.json 登记(binary: true) |
| 4 | 探针 listen 阻塞 | onion_listen 阻塞语义 | 探针以 pthread 起监听线程+原生 socket 真请求断言,listen_stop 收尾 |

## 已知限制(notes 如实声明)
- HTTPS(GnuTLS)、PAM 认证、PNG/JPEG 图片 handler、WebDAV(XML2)、
  systemd 套接字激活、sqlite3/redis 会话后端均未编译(可选依赖全关)。
- 上游测试套件未采用(自研框架);test_package 为真实 HTTP 往返探针。

## 上游测试用例统计
- 上游自带:0(tests/ 自研框架,ONION_USE_TESTS=false,未采用)
- 适配后:test_package 消费者断言 7
