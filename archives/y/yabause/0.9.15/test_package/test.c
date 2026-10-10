/* test_yabause — 消费者测试：真实调用 yabause 核心库 API（R34）。
   headless 端口式核心表 + skip_load，验证库可链接、可初始化、可仿真循环。 */
#include <stdio.h>
#include <string.h>
#include "core.h"
#include "yabause.h"
#include "sh2core.h"
#include "sh2int.h"
#include "m68kcore.h"
#include "vidsoft.h"
#include "scsp.h"
#include "cdbase.h"
#include "peripheral.h"
#include "osdcore.h"
#include "cs0.h"

SH2Interface_struct *SH2CoreList[] = { &SH2Interpreter, NULL };
PerInterface_struct *PERCoreList[] = { &PERDummy, NULL };
CDInterface *CDCoreList[] = { &DummyCD, &ISOCD, NULL };
SoundInterface_struct *SNDCoreList[] = { &SNDDummy, NULL };
VideoInterface_struct *VIDCoreList[] = { &VIDSoft, &VIDDummy, NULL };
M68K_struct *M68KCoreList[] = { &M68KDummy, NULL };

/* Port-provided UI hooks (同上游 tools/cdtest.c 的 stub) */
void YuiErrorMsg(const char *string) { (void)string; }
void YuiSwapBuffers(void) { }

int main(void) {
    yabauseinit_struct yinit;
    memset(&yinit, 0, sizeof(yinit));
    yinit.percoretype = PERCORE_DUMMY;
    yinit.sh2coretype = SH2CORE_INTERPRETER;
    yinit.vidcoretype = VIDCORE_SOFT;
    yinit.m68kcoretype = M68KCORE_DUMMY;
    yinit.sndcoretype = SNDCORE_DUMMY;
    yinit.cdcoretype = CDCORE_DUMMY;
    yinit.carttype = CART_NONE;
    yinit.regionid = 1;
    yinit.videoformattype = VIDEOFORMATTYPE_NTSC;
    yinit.frameskip = 0;
    yinit.clocksync = 0;
    yinit.skip_load = 1;
    yinit.usethreads = 0;
    yinit.numthreads = 1;

    int r = YabauseInit(&yinit);
    printf("YabauseInit -> %d\n", r);
    if (r != 0) {
        printf("FAIL: YabauseInit returned %d\n", r);
        return 1;
    }
    for (int i = 0; i < 5; i++) {
        YabauseEmulate();
    }
    YabauseDeInit();
    printf("SMOKE_OK\n");
    return 0;
}
