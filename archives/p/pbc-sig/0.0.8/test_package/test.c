#include <stdio.h>
#include <string.h>
#include <pbc/pbc.h>
#include <pbc/pbc_sig.h>

/* Type A pairing parameters (512-bit q) */
static const char param_str[] =
    "type a\n"
    "q 878317218232726904041696822913875451541267648736421576020979191100551295340320314690132987282159324094609256366281\n"
    "r 730750818665451629363306266956548137694116550193\n"
    "h 1\n"
    "exp2 215\n"
    "exp1 107\n"
    "sign1 1\n"
    "sign0 0\n";

int main(void)
{
    pairing_t pairing;
    bls_sys_param_t param;
    bls_public_key_t pk;
    bls_private_key_t sk;
    unsigned char *sig;

    if (pairing_init_set_buf(pairing, param_str, sizeof(param_str))) {
        fprintf(stderr, "FAIL: pairing init failed\n");
        return 1;
    }

    bls_gen_sys_param(param, pairing);
    bls_gen(pk, sk, param);

    sig = (unsigned char *)pbc_malloc(param->signature_length);

    bls_sign(sig, 11, (unsigned char *)"hello world", sk);

    int ok = bls_verify(sig, 11, (unsigned char *)"hello world", pk);
    if (ok) {
        printf("OK: BLS signature verifies\n");
    } else {
        fprintf(stderr, "FAIL: BLS signature does not verify\n");
    }

    pbc_free(sig);
    bls_clear_public_key(pk);
    bls_clear_private_key(sk);
    bls_clear_sys_param(param);
    pairing_clear(pairing);

    return ok ? 0 : 1;
}
