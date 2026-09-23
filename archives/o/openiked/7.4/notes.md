# openiked 7.4 适配笔记

## 选型与版本核验（2026-09-08）

- GitHub openiked/openiked-portable tags 实拉：`v7.4`（带 v 前缀）✓
- 档案无 openiked；制品仓零发布（待 conan list 复核）✓
- 平台任务 contrib-5943 已认领（claimer Ember5843，第三单）✓
- 上游 tarball 321KB，sha256 cc35cb5a…6717f 锚定

## 前三轮筛选的教训（同晚被上游闸拦截的候选）

- concord v2.4.5：tag 不存在（v2.4.0 → v3.0.0 跳版本）
- c3c v0.4.11：tag 不存在（0.4 系只有 0.4）
- luvi v2.12.0：tarball OK 但 deps 是 7 个 git submodules（含 openssl），
  构建 moving parts 过多，主动放弃

## 配方决策

- 依赖：libevent/2.1.13 + libressl/3.9.1（OpenIKED 官方推荐 LibreSSL）
- 路径注入：CMAKE_C_FLAGS/EXE_LINKER_FLAGS 覆盖 /usr/local 硬编码
- bison：hnp 工具链自带（3.8.2），parse.c 生成在 build 期完成
- E549：iked + ikectl 双产物签名
- R34：iked -V 横幅 + ikectl usage（IPsec 数据面需 root/pfkey，降级申报）

## 待办（Phase 2，设备侧）

- [ ] bundle 推送 → conan create → conan-verify 八门禁 → finish

## 对话记录（关键转折）

- 2026-09-08 第三单：六连筛全绿（此前 concord v2.4.5/c3c v0.4.11 均被上游版本闸拦截，
  luvi 因 7 个 submodule 主动放弃）→ 两段式认领 contrib-5943
- create 循环 5 轮：libressl/3.9.2 未发布→3.9.1；fts.h 缺失→0001 vendored BSD fts；
  getpass 隐式声明→0002 compat getpass；宏语义反转致声明被隐藏→修正为存在时定义；
  OHOS SDK linux/socket.h 头卫生（sockaddr_storage 重定义）+WAIT_ANY→0003
- 产物：iked/ikectl 签名可执行，`iked -V` 输出 "OpenIKED 7.4" rc=0，ikectl usage 断言通过

## 终态（2026-09-08）

- **status: built（submit 就绪）**：create + test_package + 八门禁 + W3/W2 全绿
- 下一步（人工）：push 分支 → submit 建 PR → CI 绿后 submit 自动升级 success（R50）
