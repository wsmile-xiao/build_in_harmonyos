#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <unistd.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <sys/wait.h>
#include <modbus/modbus.h>

/* HarmonyOS-specific end-to-end consumer test:
 * - Uses only public libmodbus headers/API (modbus/modbus.h).
 * - Spawns a minimal raw Modbus TCP slave (plain sockets) in a child
 *   process, then a real modbus client calls modbus_read_registers()
 *   over a real TCP connection and verifies the values.
 * - Verifies set/get slave and unconnected-socket error path as well.
 */

#define TEST_REG_ADDR 0x0160
#define TEST_REG_NB   3

static const uint16_t expected[TEST_REG_NB] = { 0x022B, 0x0001, 0x0064 };

static void serve_one_request(int fd)
{
    unsigned char req[12];
    unsigned char rsp[12 + 2 * TEST_REG_NB];
    ssize_t n;
    int i;

    n = read(fd, req, sizeof(req));
    if (n < 8)
        return;

    /* Build a valid Modbus TCP response for read holding registers (FC 0x03):
       TID(2) PID(2)=0 LEN(2) SLAVE(1) FC(1) BYTE_CNT(1) REGS(2*NB) */
    rsp[0] = req[0];
    rsp[1] = req[1];
    rsp[2] = 0;
    rsp[3] = 0;
    rsp[4] = 0;
    rsp[5] = 3 + 2 * TEST_REG_NB;
    rsp[6] = req[6];
    rsp[7] = req[7]; /* echo FC */
    rsp[8] = 2 * TEST_REG_NB;
    for (i = 0; i < TEST_REG_NB; i++) {
        rsp[9 + 2 * i] = (unsigned char)(expected[i] >> 8);
        rsp[10 + 2 * i] = (unsigned char)(expected[i] & 0xFF);
    }
    (void)write(fd, rsp, sizeof(rsp));
}

int main(void)
{
    int listen_fd, client_fd;
    struct sockaddr_in addr;
    socklen_t alen = sizeof(addr);
    pid_t pid;
    int status;
    uint16_t tab[TEST_REG_NB];
    modbus_t *ctx;
    int rc;
    int port;

    listen_fd = socket(AF_INET, SOCK_STREAM, 0);
    if (listen_fd < 0) {
        perror("socket");
        return 1;
    }
    memset(&addr, 0, sizeof(addr));
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    addr.sin_port = 0;
    if (bind(listen_fd, (struct sockaddr *)&addr, sizeof(addr)) < 0 ||
        listen(listen_fd, 1) < 0) {
        perror("bind/listen");
        return 1;
    }
    if (getsockname(listen_fd, (struct sockaddr *)&addr, &alen) < 0) {
        perror("getsockname");
        return 1;
    }
    port = ntohs(addr.sin_port);

    pid = fork();
    if (pid < 0) {
        perror("fork");
        return 1;
    }
    if (pid == 0) {
        /* child: accept one connection and serve one response */
        client_fd = accept(listen_fd, NULL, NULL);
        if (client_fd >= 0) {
            serve_one_request(client_fd);
            close(client_fd);
        }
        close(listen_fd);
        _exit(0);
    }

    /* parent: real modbus client over TCP */
    ctx = modbus_new_tcp("127.0.0.1", port);
    if (ctx == NULL) {
        fprintf(stderr, "modbus_new_tcp failed\n");
        return 1;
    }
    modbus_set_slave(ctx, 17);
    if (modbus_get_slave(ctx) != 17) {
        fprintf(stderr, "modbus_get_slave mismatch\n");
        return 1;
    }

    if (modbus_connect(ctx) == -1) {
        fprintf(stderr, "modbus_connect: %s\n", modbus_strerror(errno));
        return 1;
    }
    memset(tab, 0, sizeof(tab));
    rc = modbus_read_registers(ctx, TEST_REG_ADDR, TEST_REG_NB, tab);
    modbus_close(ctx);
    modbus_free(ctx);

    waitpid(pid, &status, 0);
    close(listen_fd);

    if (rc != TEST_REG_NB) {
        fprintf(stderr, "modbus_read_registers rc=%d (expected %d)\n",
                rc, TEST_REG_NB);
        return 1;
    }
    if (memcmp(tab, expected, sizeof(expected)) != 0) {
        fprintf(stderr, "register values mismatch\n");
        return 1;
    }

    /* Unconnected-socket error path must fail gracefully */
    ctx = modbus_new_tcp("127.0.0.1", 9); /* discard port, nothing listening */
    if (ctx == NULL)
        return 1;
    rc = modbus_read_registers(ctx, 0, 1, tab);
    modbus_free(ctx);
    if (rc != -1) {
        fprintf(stderr, "expected -1 on unconnected socket, got rc=%d\n", rc);
        return 1;
    }

    printf("libmodbus %s HarmonyOS consumer test: OK "
           "(TCP roundtrip, slave=%d, values verified, error path verified)\n",
           LIBMODBUS_VERSION_STRING, 17);
    return 0;
}