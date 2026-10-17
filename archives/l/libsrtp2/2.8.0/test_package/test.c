#include <srtp2/srtp.h>

#include <stdio.h>
#include <string.h>


int main(void)
{
    unsigned char key[30] = { 0 };
    srtp_policy_t policy;
    srtp_t session = NULL;

    if (srtp_init() != srtp_err_status_ok) {
        return 1;
    }

    memset(&policy, 0, sizeof(policy));
    srtp_crypto_policy_set_rtp_default(&policy.rtp);
    srtp_crypto_policy_set_rtcp_default(&policy.rtcp);
    policy.ssrc.type = ssrc_any_inbound;
    policy.key = key;
    policy.window_size = 128;

    if (srtp_create(&session, &policy) != srtp_err_status_ok) {
        srtp_shutdown();
        return 2;
    }
    if (srtp_dealloc(session) != srtp_err_status_ok) {
        srtp_shutdown();
        return 3;
    }
    if (srtp_shutdown() != srtp_err_status_ok) {
        return 4;
    }

    printf("libSRTP %s session lifecycle passed\n", srtp_get_version_string());
    return 0;
}