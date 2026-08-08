#include <stdio.h>
#include <winscard.h>

/* 消费者视角验证（R34）：真实调用被测包 pcsc-lite 的 PC/SC API。
 * 无 pcscd 守护进程/读卡器时 SCardEstablishContext 返回 SCARD_E_NO_SERVICE，
 * 但只要链接成功并拿到预期错误码即证明头文件/库可用。
 * 若返回 0（SCARD_S_SUCCESS）说明存在可用的 pcscd 服务。 */
int main(void) {
    SCARDCONTEXT ctx = 0;
    LONG rv = SCardEstablishContext(SCARD_SCOPE_SYSTEM, NULL, NULL, &ctx);
    printf("SCardEstablishContext returned %ld (0x%lx)\n", (long)rv, (unsigned long)rv);
    if (rv == 0) {
        (void)SCardReleaseContext(ctx);
    }
    /* SCARD_S_SUCCESS=0 或 SCARD_E_NO_SERVICE=0x8010001D 均为库链路正常 */
    if (rv == 0 || rv == 0x8010001D) {
        printf("pcsc-lite 2.4.0 OK (rv=0x%lx)\n", (unsigned long)rv);
        return 0;
    }
    printf("pcsc-lite API returned unexpected error 0x%lx\n", (unsigned long)rv);
    return 1;
}
