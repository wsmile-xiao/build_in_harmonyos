#include <stdio.h>
#include <stdlib.h>
#include <netinet/in.h>
#include <osmocom/netif/stream.h>

int main(void)
{
    struct osmo_stream_cli *cli;
    struct osmo_stream_srv_link *srv;
    void *ctx = OTC_GLOBAL;

    cli = osmo_stream_cli_create(ctx);
    if (!cli) { printf("FAIL: osmo_stream_cli_create\n"); return 1; }
    printf("ok: osmo_stream_cli_create\n");

    osmo_stream_cli_set_addr(cli, "127.0.0.1");
    osmo_stream_cli_set_port(cli, 4222);
    osmo_stream_cli_set_proto(cli, IPPROTO_TCP);
    printf("ok: osmo_stream_cli_set_addr/port/proto\n");

    osmo_stream_cli_destroy(cli);
    printf("ok: osmo_stream_cli_destroy\n");

    srv = osmo_stream_srv_link_create(ctx);
    if (!srv) { printf("FAIL: osmo_stream_srv_link_create\n"); return 1; }
    printf("ok: osmo_stream_srv_link_create\n");

    osmo_stream_srv_link_set_addr(srv, "127.0.0.1");
    osmo_stream_srv_link_set_port(srv, 4222);
    osmo_stream_srv_link_set_proto(srv, IPPROTO_TCP);
    printf("ok: osmo_stream_srv_link_set_addr/port/proto\n");

    osmo_stream_srv_link_destroy(srv);
    printf("ok: osmo_stream_srv_link_destroy\n");

    printf("consumer test: PASS\n");
    return 0;
}
