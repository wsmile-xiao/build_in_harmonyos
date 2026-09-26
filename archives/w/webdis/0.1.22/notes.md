# webdis 0.1.22 适配笔记

## 编译环境

- 构建系统：上游手写 Makefile（`make` → 单文件可执行 `webdis`，无 configure/generate 步骤）
- 编译日期：2026-09-23
- 编译器：clang 15.0.4（`/data/service/hnp/bin/clang`，OHOS aarch64 / musl）
- 目标平台：OHOS 6.0 / armv8（profile `ci/conan/profiles/ohos-aarch64`）
- 状态：built（源码零补丁）

## 上游测试清点（R51 三步法第一步：申报表）

| 测试文件 | 类型 | 用例数 | 上游入口 |
|---|---|---|---|
| `tests/basic.py` | python unittest | 25（8 个 TestCase 类） | 根 Makefile `test:` 目标 |
| `tests/limits.py` | python unittest | 2 | 根 Makefile `test:` 目标 |
| `tests/pubsub`（由 `tests/pubsub.c` 编译） | libevent 压测客户端 | 无 pass/fail 断言 | 根 Makefile `test:` 目标 |
| `tests/ws-tests.py` | python unittest | 10 | 上游 CI 未调用（需 `websocket-client`） |
| `tests/curl-tests.sh` | shell 断言 | 2 | 上游 CI（build.yml）调用 |
| `tests/bench.sh` | 性能压测 | 无断言（需 `ab`） | 根 Makefile `perftest:` 目标 |

上游 CI（`.github/workflows/build.yml`，ubuntu-20.04 + `redis:6.2.1-alpine` sidecar）实际只执行
`make` → `./webdis <ci.json>` → `tests/basic.py` → `tests/curl-tests.sh`。
`basic.py` 中 2 个 `TestPubSub` 用例被上游 `@unittest.skip('Fails in GitHub actions')` 显式跳过。

**实测结果：39 项实际执行 / 37 项通过 / 0 失败 / 2 项上游自身跳过**
（逐用例与日志路径见 `reports/test-report.md`）。

## 编译步骤

```bash
# 1) 依赖（均来自制品仓预编译包，W0 已用 conan download 逐个验证可消费）
#    libevent/2.1.13（动态）  msgpack-c/7.0.1（静态）
conan create archives/w/webdis/0.1.22 \
  --profile:h=ci/conan/profiles/ohos-aarch64 --profile:b=ci/conan/profiles/ohos-aarch64

# 配方内部（build()）等价于：
make CC=clang \
     CFLAGS="-std=c99 -Wall -Wextra -Isrc -Isrc/jansson/src -Isrc/http-parser \
             -D_POSIX_C_SOURCE=200809L -Wno-pragmas -fPIC -DMSGPACK=1 <libevent/msgpack-c include>" \
     LDFLAGS="-L<libevent lib> -levent* -lpthread -L<msgpack-c lib> -lmsgpack-c -pthread" \
     FORMAT_OBJS="src/formats/{json,raw,common,custom-type,msgpack}.o" -j1
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `src/server.h:7:10: error: 'hiredis/async.h' file not found` | 上游 Makefile 用 `CFLAGS ?=` 设置默认参数，而构建环境已导出 `CFLAGS`，`?=` 不生效 → `-Isrc` 丢失 | 配方显式复述上游默认 CFLAGS（不新增任何 include 语义） |
| 2 | 只加 `-DMSGPACK=1` 时 `undefined symbol: msgpack_reply` | 上游只在自身 `/usr/lib/libmsgpack*.so` 探测分支里把 `src/formats/msgpack.o` 加进目标文件列表 | 同时显式传 `FORMAT_OBJS`（上游对象 + msgpack.o） |
| 3 | 首次 `conan create`：T7 MessagePack 断言失败（回退成 JSON） | 配方漏 `-DMSGPACK=1`（`src/cmd.c` 用 `#ifdef MSGPACK` 注册该格式） | CFLAGS 加 `-DMSGPACK=1`，复验通过 |
| 4 | 端到端 SET/GET 间歇性失败（3 次里 1 次，body 为空） | webdis 连接池冷启动时 `pool_get_context()` 返回 NULL → `CMD_REDIS_UNAVAIL`（cmd.c:297）→ 503 空 body（worker.c:249）。Linux 同源行为 | 测试脚本先预热连接池（有界重试）再断言；连跑 5 次稳定通过 |
| 5 | 鸿蒙专项测试 T8 之后脚本挂死 | 我的脚本里用了裸 `wait`，把后台的 webdis/redis 服务进程一起等上了（harness bug，非产品问题） | 改为只 `wait` curl 子进程 pid，并给 curl 加 `--max-time` |

## 源码修改

**无补丁**（`conandata.yml` 的 `patches: []`）。上游源码原样编译通过；
唯一的构建期调整是传入上游 Makefile 的默认 CFLAGS/FORMAT_OBJS（配方侧参数，不改源码）。

## 依赖版本

| 依赖 | 版本 | 链接方式 | 来源 |
|---|---|---|---|
| libevent | 2.1.13 | 动态（conan 管理依赖链） | ohpcd 制品仓预编译包 |
| msgpack-c | 7.0.1 | 静态（`libmsgpack-c.a`，无运行期依赖） | ohpcd 制品仓预编译包 |
| hiredis / jansson / http-parser / b64 / md5 / sha1 | 上游 vendored（`src/` 下） | 源码内编译 | 上游 tarball |

## 验证结果

```console
$ python3 tests/basic.py -v
Ran 25 tests in 0.246s
OK (skipped=2)

$ python3 tests/limits.py -v
Ran 2 tests in 2.364s
OK

$ python3 tests/ws-tests.py -v
Ran 10 tests in 0.996s
OK

$ bash tests/curl-tests.sh
Sending a PUT request with a large payload... OK
Verifying the upload... OK
Sending an OPTIONS request... OK

$ conan create archives/w/webdis/0.1.22 -pr:h=… -pr:b=…
（test_package 为 python unittest 套件，真实拉起被测二进制交互）
test_consumer.py    : Ran 5 tests  … OK
test_webdis_ohos.py : Ran 16 tests … OK
```

## 交付物

| 文件 | 说明 |
|------|------|
| `bin/webdis` | 264704 B，ELF64 AArch64 PIE，`/lib/ld-musl-aarch64.so.1`，NEEDED: libevent.so / libc.so |
| `share/webdis/webdis.json`、`webdis.prod.json` | 上游示例配置 |
| `licenses/COPYING` | BSD-2-Clause |

## 注意事项

- **运行期需要 `libevent.so`**：webdis 动态链接 libevent（非 OHOS 系统同名库，无需静态化）。
  二进制未内嵌 RPATH（避免把宿主构建路径写进产物），消费侧依赖 Conan 运行环境（`conanrun`）的
  `LD_LIBRARY_PATH`。
- **冷连接池竞态**：webdis 启动后第一个需要 Redis 的请求可能拿到 `503`（空 body），
  持续几十~几百毫秒；生产部署建议先探活（重试）再放量。该行为来自上游，未打补丁。
- **`tests/pubsub` 不可作为判据**：该 harness 在 libevent 回调里做阻塞 read 并对 level-triggered
  `EV_WRITE` 反复重注册，导致忙等自旋、消息推进停摆（详见 `reports/test-report.md` §5.2）；
  上游 CI 亦不运行它。SUBSCRIBE 推流本身已手工验证正常。
- `tests/bench.sh`（`make perftest`）需要 `ab`（apache2-utils），未执行。
---

**编译结束**: 2026-09-23 18:26
**最终状态**: built
