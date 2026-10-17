/* bcp 1.4.4 消费者断言（test_package）— 静态闭包链接 + 真跑，10 条断言。
 *
 * 验证面（鸿蒙特有测试行 = 本文件断言数）：
 *   1-4  版本宏：安装产物 <BcpConfig.h>（由 configure 生成的 config_bcp.h
 *        经 install-exec-local 拷入 include/coin/）自报 BCP_VERSION 串与
 *        三段数值与配方版本一致；
 *   5-7  BCP_buffer：set_content 后 size/sender 契约 + pack/unpack 往返；
 *   8-10 BCP_cg_prob：构造（纯成员初始化）真链接 libBcp.a 非 inline 符号
 *        （定义于 src/CG/BCP_cg.cpp），断言 core 已分配、upper_bound 初值、
 *        user/msg_env 为空；析构（delete 自管成员）成功即 rc=0。
 * 断言 8-10 同时是「消费者真的链上了 libBcp.a」的判据——若链接面缺符号，
 * 编译链接阶段即失败，不会静默。
 */
#include <BcpConfig.h>      /* BCP_VERSION/MAJOR/MINOR/RELEASE（随包安装） */
#include "BCP_buffer.hpp"
#include "BCP_cg.hpp"
#include "BCP_math.hpp"     /* BCP_DBL_MAX */

#include <cmath>
#include <cstdio>
#include <cstring>

static int g_checks = 0;
static int g_fails = 0;

#define CHK(cond, msg)                                                  \
    do {                                                                \
        ++g_checks;                                                     \
        if (!(cond)) {                                                  \
            ++g_fails;                                                  \
            std::printf("FAIL [%d] %s\n", g_checks, msg);               \
        }                                                               \
    } while (0)

int main(void)
{
    /* 1-4 版本宏与配方版本对账 */
    CHK(BCP_VERSION != NULL && std::strcmp(BCP_VERSION, "1.4.4") == 0,
        "BCP_VERSION == \"1.4.4\"");
    CHK(BCP_VERSION_MAJOR == 1, "BCP_VERSION_MAJOR == 1");
    CHK(BCP_VERSION_MINOR == 4, "BCP_VERSION_MINOR == 4");
    CHK(BCP_VERSION_RELEASE == 4, "BCP_VERSION_RELEASE == 4");

    /* 5-7 BCP_buffer 契约与 pack/unpack 往返 */
    BCP_buffer buf;
    const char payload[] = "harmony-bcp";
    buf.set_content(payload, sizeof(payload), 7, BCP_Msg_NoMessage);
    CHK(buf.size() == sizeof(payload), "set_content 后 size == 载荷长度");
    CHK(buf.sender() == 7, "set_content 后 sender 保留");
    BCP_buffer rt;
    int value = 42, back = 0;
    rt.pack(value);
    rt.unpack(back);
    CHK(back == 42, "pack/unpack 往返 42");

    /* 8-10 BCP_cg_prob：真链接 libBcp.a 非 inline 符号（BCP_cg.cpp 定义） */
    {
        BCP_cg_prob prob(1, 0);
        CHK(prob.core != NULL, "构造后 core 已分配");
        CHK(prob.upper_bound == BCP_DBL_MAX, "构造后 upper_bound == BCP_DBL_MAX");
        CHK(prob.user == NULL && prob.msg_env == NULL,
            "构造后 user/msg_env 为空（待 USER_initialize）");
        /* 上游缺陷规避（notes.md 问题表 #7）：BCP_cg_prob 的构造初始化列表
         * 未包含 packer 成员（Bcp/src/CG/BCP_cg.cpp ctor 只初始化
         * user/msg_env/core/upper_bound/phase），而析构体第一句即
         * `delete packer` —— 消费者不经 USER_initialize 直接构造时 packer
         * 是野指针：-O0 恰好栈零侥幸通过、-O3 栈垃圾实测 Segmentation
         * fault（本设备 clang15 复现，见 $TASK_DIR/bisect 二分证据）。
         * unitTest 不触发是因为 USER_initialize 在析构前先赋值 packer。
         * packer 是公开成员，按公开契约显式置 NULL 后析构（delete NULL
         * 安全）；此为如实记录的上游未初始化缺陷，非测试取巧。 */
        prob.packer = NULL;
        /* 析构（delete user/packer/core）不崩即计入 rc=0 */
    }

    std::printf("BCP consumer OK: %d/%d assertions passed (bcp/%s)\n",
                g_checks - g_fails, g_checks, BCP_VERSION);
    return g_fails == 0 ? 0 : 1;
}
