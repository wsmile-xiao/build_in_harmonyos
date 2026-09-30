/*
    reliable 1.3.5 — test_package 消费者用例

    角色：业务上层组件 / 应用。本文件以"库的使用者"身份，只通过 reliable
    对外公开的 API 使用它，验证"这个库被别人拿过去能不能正常编译、链接、
    调用跑通"（官方路径A 硬性要求）。

    验证内容（端到端，非桩测试）：

      1. 头文件可用 + 静态库可链接 —— 能编译链接到这一步即是证明
      2. 两个 endpoint 通过 transmit 回调互投线包，构成一条真实双向链路
      3. 小包往返：client 发出 → server 的 process_packet 收到、正文逐字节
         相符 → server 的 ACK 回传到 client → client 按序号收到该 ACK
      4. 大包分片：5000 字节正文（> fragment_above=1200）被分片发送，
         server 重组后交给 process_packet，正文逐字节相符
      5. 计数器契约：packets / fragments 计数、invalid 计数
      6. 统计量契约：rtt / rtt_min / rtt_max / jitter / packet_loss /
         bandwidth 的返回值范围
      7. reset 语义：reliable_endpoint_reset() 后计数器归零，端点仍可复用

    ★ 链路驱动必须"双向发包"——reliable 的 ACK 是搭车的，不是独立包：

      - reliable_endpoint_send_packet() 会把本端"已收到的序号"编成 ACK
        写进**出站包的包头**（库内部实现，非公开 API，见 reliable.c:796）；
      - reliable_endpoint_update() 只做 RTT/丢包等统计，**一个包都不发**
        （全库 transmit 回调的调用点只有 reliable.c:820 与 874，都在
        send_packet 里）；
      - 也就是说：只有一方发包时，另一方永远收不到 ACK —— 包发出去了、
        对端也收到了，但发送方的 NUM_PACKETS_ACKED 恒为 0。
        上游官方测试（reliable.c 的 test_acks()）因此写成"每一轮两个端点
        各发一个 8 字节 dummy 包，再各自 update"。本用例照抄该形态：
        pump_link() 每轮双方各发一个心跳包，ACK 才有车可搭。
        这正是本用例首次上真机时 3/35 失败（两条 acked 断言 + reset 后
        rx_calls 不增长）的直接原因。

    为什么用自研 CHECK 宏而不是 assert()：
      CMake 的 Release 配置会定义 NDEBUG，**assert() 会被预处理掉变成空语句**，
      测试将退化为"必然通过"的假测试（CI 侧 L1e 破坏性反向验证正是针对
      这类假测试）。这里用不受 NDEBUG 影响的 CHECK，失败累计后以非 0 退出码
      结束，确保失败一定能被 conan 捕获。

    本用例真实依赖被测包的 libreliable.a 与 reliable.h —— CI 的 L1e 会把
    包缓存里的 include/ 与 lib/ 移走再重跑，链接必然失败，符合 R34 要求。

    CHECK 调用总数为固定值（不随循环轮数变化），便于 MANIFEST.yml 声明。
*/

#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include <reliable.h>

/* ── 用例参数 ───────────────────────────────────────────────────────── */

#define SMALL_PACKET_BYTES    64
#define LARGE_PACKET_BYTES    5000
#define FRAGMENT_ABOVE        1200
#define FRAGMENT_SIZE         1024
#define MAX_PACKET_BYTES      ( 32 * 1024 )
#define MAX_FRAGMENTS         32

#define UPDATE_ITERATIONS     24      /* 小包：足够完成一次往返 */
#define UPDATE_ITERATIONS_BIG 96      /* 大包：留给分片重组更多轮 */
#define TIME_STEP             0.05

/* 5000 字节 / 1024 字节分片 ≈ 5 片 */
#define MIN_EXPECTED_FRAGMENTS 5

/* ── 断言（NDEBUG 安全）────────────────────────────────────────────── */

static int g_checks = 0;
static int g_failures = 0;

#define CHECK( cond )                                                        \
    do                                                                       \
    {                                                                        \
        g_checks++;                                                          \
        if ( !( cond ) )                                                     \
        {                                                                    \
            g_failures++;                                                    \
            printf( "  [FAIL] line %d: %s\n", __LINE__, #cond );             \
        }                                                                    \
    } while ( 0 )

/* ── 回环链路：把两个端点的 transmit 回调对接起来 ──────────────────── */

struct link_ctx_t
{
    struct reliable_endpoint_t * self_endpoint;
    struct reliable_endpoint_t * peer_endpoint;
    int      tx_calls;        /* transmit_packet 回调被调用次数 */
    int      rx_calls;        /* process_packet 回调被调用次数 */
    int      payload_ok;      /* 收到的正文与预期逐字节相符的次数 */
    int      dropped;         /* 因对端未就绪而丢弃的包数（必须恒为 0） */
    int      expect_bytes;    /* 期望的正文长度 */
    uint32_t expect_hash;     /* 期望的正文 FNV-1a 哈希 */
};

static struct link_ctx_t g_client;
static struct link_ctx_t g_server;

static uint32_t fnv1a( const uint8_t * data, int bytes )
{
    uint32_t h = 2166136261u;
    int i;
    for ( i = 0; i < bytes; ++i )
    {
        h ^= (uint32_t) data[i];
        h *= 16777619u;
    }
    return h;
}

static void fill_payload( uint8_t * buf, int bytes, int seed )
{
    int i;
    for ( i = 0; i < bytes; ++i )
    {
        buf[i] = (uint8_t) ( ( i * 31 + seed * 17 + 7 ) & 0xff );
    }
}

static void transmit_packet( void * context, uint64_t id, uint16_t sequence,
                             uint8_t * packet_data, int packet_bytes )
{
    struct link_ctx_t * ctx = (struct link_ctx_t*) context;
    (void) id;
    (void) sequence;

    ctx->tx_calls++;

    /* 真实业务里这一步走 socket；用例中直接投递给对端端点，
       从而形成一条可断言的双向链路 */
    if ( ctx->peer_endpoint == NULL )
    {
        ctx->dropped++;
        return;
    }

    reliable_endpoint_receive_packet( ctx->peer_endpoint, packet_data, packet_bytes );
}

static int process_packet( void * context, uint64_t id, uint16_t sequence,
                           uint8_t * packet_data, int packet_bytes )
{
    struct link_ctx_t * ctx = (struct link_ctx_t*) context;
    (void) id;
    (void) sequence;

    ctx->rx_calls++;

    if ( packet_bytes == ctx->expect_bytes &&
         fnv1a( packet_data, packet_bytes ) == ctx->expect_hash )
    {
        ctx->payload_ok++;
    }

    return 1;   /* 接受并 ACK；返回 0 表示拒收且不回 ACK */
}

/* 心跳包：8 字节全 0，远小于 fragment_above（1200），不会产生分片。
   唯一作用是把本地已收到的序号作为 ACK 搭在包头里发给对端。
   它既不等于 expect_bytes（64 / 5000）也不匹配 expect_hash，
   所以不会污染 payload_ok 计数。 */
static uint8_t g_heartbeat[8];

/* 跑若干轮 update，收集 client 侧收到的 ACK。
   每轮先让双方各发一个心跳包（顺序与上游 test_acks() 一致），再各自 update，
   最后读走 client 累下的 ACK —— reliable 的 ACK 只能这样搭车回传。 */
static int pump_link( struct reliable_endpoint_t * client,
                      struct reliable_endpoint_t * server,
                      uint16_t want_seq, double * time, int iterations )
{
    int acked = 0;
    int i;

    for ( i = 0; i < iterations; ++i )
    {
        int num_acks = 0;
        uint16_t * acks;
        int j;

        reliable_endpoint_send_packet( client, g_heartbeat, (int) sizeof( g_heartbeat ) );
        reliable_endpoint_send_packet( server, g_heartbeat, (int) sizeof( g_heartbeat ) );

        reliable_endpoint_update( client, *time );
        reliable_endpoint_update( server, *time );

        acks = reliable_endpoint_get_acks( client, &num_acks );
        for ( j = 0; j < num_acks; ++j )
        {
            if ( acks[j] == want_seq )
            {
                acked = 1;
            }
        }

        reliable_endpoint_clear_acks( client );
        reliable_endpoint_clear_acks( server );

        *time += TIME_STEP;

        if ( acked )
        {
            break;
        }
    }

    return acked;
}

/* ── 主流程 ───────────────────────────────────────────────────────── */

int main( void )
{
    struct reliable_config_t config;
    struct reliable_endpoint_t * client = NULL;
    struct reliable_endpoint_t * server = NULL;
    uint8_t small[SMALL_PACKET_BYTES];
    uint8_t large[LARGE_PACKET_BYTES];
    double time = 0.0;
    int i;

    printf( "\n[reliable %s 消费者用例]\n", RELIABLE_VERSION_FULL );

    memset( &g_client, 0, sizeof( g_client ) );
    memset( &g_server, 0, sizeof( g_server ) );

    /* ── 1. 库初始化 ── */
    CHECK( reliable_init() == RELIABLE_OK );
    reliable_log_level( RELIABLE_LOG_LEVEL_NONE );

    /* ── 2. 用公开的 default_config 建立配置 ── */
    reliable_default_config( &config );
    CHECK( config.max_packet_size > 0 );
    CHECK( config.fragment_size > 0 );
    CHECK( config.fragment_above > 0 );
    CHECK( config.max_fragments > 0 );

    config.max_packet_size           = MAX_PACKET_BYTES;
    config.fragment_above            = FRAGMENT_ABOVE;
    config.fragment_size             = FRAGMENT_SIZE;
    config.max_fragments             = MAX_FRAGMENTS;
    config.transmit_packet_function  = transmit_packet;
    config.process_packet_function   = process_packet;

    /* ── 3. reliable_copy_string 语义（公开 API） ── */
    reliable_copy_string( config.name, "consumer-client", sizeof( config.name ) );
    CHECK( strcmp( config.name, "consumer-client" ) == 0 );

    /* ── 4. 建立两个端点 ── */
    config.context = &g_client;
    client = reliable_endpoint_create( &config, time );
    CHECK( client != NULL );
    g_client.self_endpoint = client;

    config.context = &g_server;
    reliable_copy_string( config.name, "consumer-server", sizeof( config.name ) );
    server = reliable_endpoint_create( &config, time );
    CHECK( server != NULL );
    g_server.self_endpoint = server;

    if ( client == NULL || server == NULL )
    {
        printf( "  端点创建失败，无法继续\n" );
        printf( "HMBS_TEST_PACKAGE_RESULT: FAIL (%d/%d checks failed)\n\n",
                g_failures, g_checks );
        return 1;
    }

    g_client.peer_endpoint = server;
    g_server.peer_endpoint = client;

    /* ── 5. ACK 缓冲区可获取 ── */
    {
        int probe_num = 0;
        uint16_t * probe = reliable_endpoint_get_acks( client, &probe_num );
        CHECK( probe != NULL );
    }

    /* ── 6. 小包往返 ── */
    {
        uint16_t small_seq;
        int small_acked;

        printf( "  链路驱动：每轮双方各发一个 8 字节心跳包（reliable 无独立 ACK 包，"
                "ACK 搭在出站包头上），下面的 tx/rx 计数含心跳\n" );

        fill_payload( small, SMALL_PACKET_BYTES, 1 );
        g_server.expect_bytes = SMALL_PACKET_BYTES;
        g_server.expect_hash  = fnv1a( small, SMALL_PACKET_BYTES );

        small_seq = reliable_endpoint_next_packet_sequence( client );
        reliable_endpoint_send_packet( client, small, SMALL_PACKET_BYTES );

        small_acked = pump_link( client, server, small_seq, &time, UPDATE_ITERATIONS );

        printf( "  小包: bytes=%d seq=%u client.tx=%d server.rx=%d payload_ok=%d acked=%d\n",
                SMALL_PACKET_BYTES, (unsigned) small_seq,
                g_client.tx_calls, g_server.rx_calls, g_server.payload_ok, small_acked );

        CHECK( g_client.tx_calls > 0 );       /* 确实发出了线包 */
        CHECK( g_server.rx_calls >= 1 );      /* server 确实收到了 */
        CHECK( g_server.payload_ok >= 1 );    /* 且正文逐字节相符 */
        CHECK( small_acked == 1 );            /* client 按序号收到 ACK */
    }

    /* ── 7. 大包：分片发送 + 重组 ── */
    {
        uint16_t large_seq;
        int large_acked;
        int payload_ok_before = g_server.payload_ok;

        fill_payload( large, LARGE_PACKET_BYTES, 2 );
        g_server.expect_bytes = LARGE_PACKET_BYTES;
        g_server.expect_hash  = fnv1a( large, LARGE_PACKET_BYTES );

        large_seq = reliable_endpoint_next_packet_sequence( client );
        reliable_endpoint_send_packet( client, large, LARGE_PACKET_BYTES );

        large_acked = pump_link( client, server, large_seq, &time, UPDATE_ITERATIONS_BIG );

        printf( "  大包: bytes=%d seq=%u payload_ok=%d acked=%d\n",
                LARGE_PACKET_BYTES, (unsigned) large_seq,
                g_server.payload_ok, large_acked );

        /* 大包经分片重组后，正文仍逐字节相符 */
        CHECK( g_server.payload_ok >= payload_ok_before + 1 );
        CHECK( large_acked == 1 );
    }

    /* ── 8. 计数器契约 ── */
    {
        const uint64_t * ccounters;
        const uint64_t * scounters;

        ccounters = reliable_endpoint_counters( client );
        scounters = reliable_endpoint_counters( server );
        CHECK( ccounters != NULL );
        CHECK( scounters != NULL );

        /* reliable_endpoint_counters() 返回端点内部数组，永不为 NULL
           （reliable.c: return endpoint->counters），所以下面是 2 行 printf
           + 6 项断言无条件执行 —— 借此保证本用例的 CHECK 总数恒为 35 项
           （MANIFEST.yml 里按固定值声明）。 */
        printf( "  client counters: sent=%llu acked=%llu frag_sent=%llu too_large=%llu\n",
                (unsigned long long) ccounters[RELIABLE_ENDPOINT_COUNTER_NUM_PACKETS_SENT],
                (unsigned long long) ccounters[RELIABLE_ENDPOINT_COUNTER_NUM_PACKETS_ACKED],
                (unsigned long long) ccounters[RELIABLE_ENDPOINT_COUNTER_NUM_FRAGMENTS_SENT],
                (unsigned long long) ccounters[RELIABLE_ENDPOINT_COUNTER_NUM_PACKETS_TOO_LARGE_TO_SEND] );
        printf( "  server counters: received=%llu frag_received=%llu invalid=%llu\n",
                (unsigned long long) scounters[RELIABLE_ENDPOINT_COUNTER_NUM_PACKETS_RECEIVED],
                (unsigned long long) scounters[RELIABLE_ENDPOINT_COUNTER_NUM_FRAGMENTS_RECEIVED],
                (unsigned long long) scounters[RELIABLE_ENDPOINT_COUNTER_NUM_PACKETS_INVALID] );

        CHECK( ccounters[RELIABLE_ENDPOINT_COUNTER_NUM_PACKETS_SENT] >= 2 );
        CHECK( scounters[RELIABLE_ENDPOINT_COUNTER_NUM_PACKETS_RECEIVED] >= 2 );
        CHECK( ccounters[RELIABLE_ENDPOINT_COUNTER_NUM_FRAGMENTS_SENT] >= MIN_EXPECTED_FRAGMENTS );
        CHECK( scounters[RELIABLE_ENDPOINT_COUNTER_NUM_FRAGMENTS_RECEIVED] >= MIN_EXPECTED_FRAGMENTS );
        CHECK( scounters[RELIABLE_ENDPOINT_COUNTER_NUM_PACKETS_INVALID] == 0 );
        CHECK( ccounters[RELIABLE_ENDPOINT_COUNTER_NUM_PACKETS_TOO_LARGE_TO_SEND] == 0 );
    }

    /* ── 9. 统计量契约 ── */
    {
        float rtt      = reliable_endpoint_rtt( client );
        float rtt_min  = reliable_endpoint_rtt_min( client );
        float rtt_max  = reliable_endpoint_rtt_max( client );
        float rtt_avg  = reliable_endpoint_rtt_avg( client );
        float jitter   = reliable_endpoint_jitter_avg_vs_min_rtt( client );
        float loss     = reliable_endpoint_packet_loss( client );
        float bw_sent  = 0.0f;
        float bw_recv  = 0.0f;
        float bw_acked = 0.0f;

        reliable_endpoint_bandwidth( client, &bw_sent, &bw_recv, &bw_acked );

        printf( "  stats: rtt=%.4fs min=%.4f max=%.4f avg=%.4f jitter=%.4f loss=%.2f%%\n",
                (double) rtt, (double) rtt_min, (double) rtt_max,
                (double) rtt_avg, (double) jitter, (double) loss );
        printf( "  bandwidth: sent=%.2f recv=%.2f acked=%.2f kbps\n",
                (double) bw_sent, (double) bw_recv, (double) bw_acked );

        CHECK( rtt >= 0.0f );
        CHECK( rtt_min >= 0.0f );
        CHECK( rtt_max >= rtt_min );
        /* packet_loss 是百分比（reliable.c: (num_dropped / num_sent) * 100.0f），
           不是 0~1 的比例 */
        CHECK( loss >= 0.0f && loss <= 100.0f );
        CHECK( jitter >= 0.0f );
        CHECK( bw_sent >= 0.0f );
        CHECK( bw_recv >= 0.0f );
        CHECK( bw_acked >= 0.0f );
    }

    /* ── 10. reset 语义：计数器归零且端点可复用 ── */
    {
        const uint64_t * ccounters;
        int rx_before = g_server.rx_calls;

        /* ⚠️ 必须两端一起 reset。reliable_endpoint_reset() 会把
           endpoint->sequence 归零（reliable.c:1387）并清空该端自己的
           received_packets：若只 reset client，它重发的第一个包序号仍是 0，
           而 server 侧 received_packets 里还留着上一轮的 seq 0，会被判为
           duplicate 直接丢弃（reliable.c:1169-1174），process_packet
           永远收不到调用，看起来就像"reset 后链路坏了"。上游自身的测试
           也从不做单边 reset。 */
        reliable_endpoint_reset( client );
        reliable_endpoint_reset( server );

        ccounters = reliable_endpoint_counters( client );
        CHECK( ccounters[RELIABLE_ENDPOINT_COUNTER_NUM_PACKETS_SENT] == 0 );

        g_server.expect_bytes = SMALL_PACKET_BYTES;
        g_server.expect_hash  = fnv1a( small, SMALL_PACKET_BYTES );

        reliable_endpoint_send_packet( client, small, SMALL_PACKET_BYTES );

        for ( i = 0; i < UPDATE_ITERATIONS; ++i )
        {
            /* 心跳包同样要有：ACK 只能搭车 */
            reliable_endpoint_send_packet( client, g_heartbeat, (int) sizeof( g_heartbeat ) );
            reliable_endpoint_send_packet( server, g_heartbeat, (int) sizeof( g_heartbeat ) );

            reliable_endpoint_update( client, time );
            reliable_endpoint_update( server, time );
            reliable_endpoint_clear_acks( client );
            reliable_endpoint_clear_acks( server );
            time += TIME_STEP;

            if ( g_server.rx_calls > rx_before )
            {
                break;
            }
        }

        CHECK( g_server.rx_calls > rx_before );   /* reset 后端点仍能收发 */
    }

    /* ── 11. 链路完整性：全程不应出现因对端未就绪而丢弃的包 ── */
    CHECK( g_client.dropped == 0 );
    CHECK( g_server.dropped == 0 );

    /* ── 12. 清理 ── */
    reliable_endpoint_destroy( client );
    reliable_endpoint_destroy( server );
    reliable_term();

    printf( "  检查项 %d 项，失败 %d 项\n", g_checks, g_failures );

    if ( g_failures > 0 )
    {
        printf( "HMBS_TEST_PACKAGE_RESULT: FAIL (%d/%d checks failed)\n\n",
                g_failures, g_checks );
        return 1;
    }

    printf( "HMBS_TEST_PACKAGE_RESULT: PASS (%d/%d checks passed) — "
            "small packet acked, %d-byte packet fragmented and reassembled\n\n",
            g_checks, g_checks, LARGE_PACKET_BYTES );
    return 0;
}
