/*
 * gss-ntlmssp 1.2.0 — 鸿蒙特有消费者测试（test_package）
 *
 * 对**安装树**里的 GSSAPI NTLMSSP 模块做端到端 NTLM 会话验证（不是仅断言符号存在）：
 *   dlopen 模块 → 关键导出符号 → iconv UTF16LE 平台前提 → 用户名/服务名导入 →
 *   客户端/服务端凭据（NTLM_USER_FILE）→ 四步 init/accept 握手 →
 *   wrap(conf)/unwrap 载荷往返 → get_mic/verify_mic 往返 → 资源释放。
 *
 * ABI 注记：模块的 gss_init_sec_context 是**机制插件 SPI 形态**（cred 在前、
 * 比 RFC2744 多一个 ret_flags 出参，src/gss_spi.c 实测 13 参）——函数指针
 * typedef 按模块实物声明，参数顺序与上游 tests/ntlmssptest.c 的调用面一致。
 *
 * 平台针对性（为什么它是"鸿蒙特有"用例）：
 *   - musl/OHOS 动态加载器对模块 DT_NEEDED（libgssapi_krb5/libkrb5/...）的解析，
 *     依赖 conanrun 的 LD_LIBRARY_PATH（conan 包装下 krb5-config 的 rpath 是 //lib 残链）；
 *   - iconv("UTF16LE","UTF-8") 走 OHOS libc iconv 后端（NTLM Unicode 转换前提）；
 *   - 静态 libunistring/openssl 必须被抽进模块，否则 dlopen 报
 *     undefined symbol（u8_conv_to_encoding）——本测试就是该缺陷的检出器。
 *
 * 用法: gssntlm_probe <gssntlmssp.so 绝对路径> <NTLM 凭据文件绝对路径>
 * 退出码: 0 = 全部断言通过；非 0 = 有断言失败（打印 [FAIL] 行）。
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

#include <dlfcn.h>
#include <iconv.h>
#include <gssapi/gssapi.h>
/* 被测包自身交付头（cpp_info.includedirs=["include"] 面）——必须可编译且宏齐，
 * 否则安装头缺失/损坏在本 PR 不会被发现（W4 轮1 P2）。编译期断言，不增运行断言数。 */
#include <gssapi/gssapi_ntlmssp.h>
#ifndef GSS_NTLMSSP_OID_STRING
#error "gssapi_ntlmssp.h 未提供 GSS_NTLMSSP_OID_STRING — includedirs 交付面损坏"
#endif
#if GSS_NTLMSSP_OID_LENGTH != 10
#error "GSS_NTLMSSP_OID_LENGTH 期望 10（1.3.6.1.4.1.311.2.2.10）— 交付头内容异常"
#endif

#ifndef GSS_QOP_DEFAULT
#define GSS_QOP_DEFAULT 0
#endif

static int g_checks = 0;
static int g_fails = 0;

static int ck(int cond, const char *what)
{
    g_checks++;
    if (cond) {
        printf("[PASS] %s\n", what);
    } else {
        g_fails++;
        printf("[FAIL] %s\n", what);
    }
    return cond;
}

/* 模块导出的 gss_* 入口（src/gss_spi.c，libtool -export-symbols-regex '^gss(spi|)_'） */
typedef OM_uint32 (*p_import_name)(OM_uint32 *, gss_buffer_t, gss_OID, gss_name_t *);
typedef OM_uint32 (*p_release_name)(OM_uint32 *, gss_name_t *);
typedef OM_uint32 (*p_acquire_cred)(OM_uint32 *, gss_name_t, OM_uint32, gss_OID_set,
                                    gss_cred_usage_t, gss_cred_id_t *, gss_OID_set *,
                                    OM_uint32 *);
typedef OM_uint32 (*p_release_cred)(OM_uint32 *, gss_cred_id_t *);
typedef OM_uint32 (*p_init_sec_ctx)(OM_uint32 *, gss_cred_id_t, gss_ctx_id_t *, gss_name_t,
                                    gss_OID, OM_uint32, OM_uint32, gss_channel_bindings_t,
                                    gss_buffer_t, gss_OID *, gss_buffer_t, OM_uint32 *,
                                    OM_uint32 *);
typedef OM_uint32 (*p_accept_sec_ctx)(OM_uint32 *, gss_ctx_id_t *, gss_cred_id_t,
                                      gss_buffer_t, gss_channel_bindings_t, gss_name_t *,
                                      gss_OID *, gss_buffer_t, OM_uint32 *, OM_uint32 *,
                                      gss_cred_id_t *);
typedef OM_uint32 (*p_wrap)(OM_uint32 *, gss_ctx_id_t, int, gss_qop_t, gss_buffer_t, int *,
                            gss_buffer_t);
typedef OM_uint32 (*p_unwrap)(OM_uint32 *, gss_ctx_id_t, gss_buffer_t, gss_buffer_t, int *,
                              gss_qop_t *);
typedef OM_uint32 (*p_get_mic)(OM_uint32 *, gss_ctx_id_t, gss_qop_t, gss_buffer_t,
                               gss_buffer_t);
typedef OM_uint32 (*p_verify_mic)(OM_uint32 *, gss_ctx_id_t, gss_buffer_t, gss_buffer_t,
                                  gss_qop_t *);
typedef OM_uint32 (*p_delete_ctx)(OM_uint32 *, gss_ctx_id_t *, gss_buffer_t);
typedef OM_uint32 (*p_import_cred)(OM_uint32 *, gss_buffer_t, gss_cred_id_t *);
typedef OM_uint32 (*p_export_cred)(OM_uint32 *, gss_cred_id_t, gss_buffer_t);

int main(int argc, char **argv)
{
    const char *module_path;
    const char *cred_file;
    void *dso;
    char *err;

    p_import_name d_import_name;
    p_release_name d_release_name;
    p_acquire_cred d_acquire_cred;
    p_release_cred d_release_cred;
    p_init_sec_ctx d_init_sec_ctx;
    p_accept_sec_ctx d_accept_sec_ctx;
    p_wrap d_wrap;
    p_unwrap d_unwrap;
    p_get_mic d_get_mic;
    p_verify_mic d_verify_mic;
    p_delete_ctx d_delete_ctx;
    p_import_cred d_import_cred;
    p_export_cred d_export_cred;

    gss_name_t user_name = GSS_C_NO_NAME;
    gss_name_t srv_name = GSS_C_NO_NAME;
    gss_cred_id_t cli_cred = GSS_C_NO_CREDENTIAL;
    gss_cred_id_t srv_cred = GSS_C_NO_CREDENTIAL;
    gss_ctx_id_t cli_ctx = GSS_C_NO_CONTEXT;
    gss_ctx_id_t srv_ctx = GSS_C_NO_CONTEXT;
    gss_buffer_desc cli_tok = GSS_C_EMPTY_BUFFER;
    gss_buffer_desc srv_tok = GSS_C_EMPTY_BUFFER;
    gss_buffer_desc exp_tok = GSS_C_EMPTY_BUFFER;
    gss_buffer_desc mic_tok = GSS_C_EMPTY_BUFFER;
    gss_OID actual_mech = GSS_C_NO_OID;
    OM_uint32 maj;
    OM_uint32 min;
    int conf_state = 0;
    gss_qop_t qop = GSS_QOP_DEFAULT;

    gss_buffer_desc nbuf;
    gss_buffer_desc msg;
    const char *payload = "harmonyos gss-ntlmssp consumer e2e payload";
    const char *username = "TESTDOM\\testuser";
    const char *srvname = "test@testserver";
    OM_uint32 req_flags = GSS_C_CONF_FLAG | GSS_C_INTEG_FLAG;

    if (argc != 3) {
        fprintf(stderr, "usage: %s <gssntlmssp.so> <ntlm_user_file>\n", argv[0]);
        return 2;
    }
    module_path = argv[1];
    cred_file = argv[2];
    printf("GSSNTLM_PROBE module=%s cred=%s\n", module_path, cred_file);

    /* ── 1. musl/OHOS 动态加载安装的机制模块（RTLD_NOW 解析其全部 DT_NEEDED） ── */
    dso = dlopen(module_path, RTLD_NOW | RTLD_LOCAL);
    if (!dso) {
        err = dlerror();
        printf("[FAIL] dlopen(%s): %s\n", module_path, err ? err : "(null)");
        printf("GSSNTLM_PROBE_RESULT checks=%d fails=%d\n", g_checks + 1, g_fails + 1);
        return 1;
    }
    ck(dso != NULL, "dlopen installed gssntlmssp module (musl/OHOS loader)");

    /* ── 2. 关键导出符号（含 configure 硬校验的 gss_import_cred/gss_export_cred） ── */
    d_import_name  = (p_import_name)dlsym(dso, "gss_import_name");
    d_release_name = (p_release_name)dlsym(dso, "gss_release_name");
    d_acquire_cred = (p_acquire_cred)dlsym(dso, "gss_acquire_cred");
    d_release_cred = (p_release_cred)dlsym(dso, "gss_release_cred");
    d_init_sec_ctx = (p_init_sec_ctx)dlsym(dso, "gss_init_sec_context");
    d_accept_sec_ctx = (p_accept_sec_ctx)dlsym(dso, "gss_accept_sec_context");
    d_wrap         = (p_wrap)dlsym(dso, "gss_wrap");
    d_unwrap       = (p_unwrap)dlsym(dso, "gss_unwrap");
    d_get_mic      = (p_get_mic)dlsym(dso, "gss_get_mic");
    d_verify_mic   = (p_verify_mic)dlsym(dso, "gss_verify_mic");
    d_delete_ctx   = (p_delete_ctx)dlsym(dso, "gss_delete_sec_context");
    d_import_cred  = (p_import_cred)dlsym(dso, "gss_import_cred");
    d_export_cred  = (p_export_cred)dlsym(dso, "gss_export_cred");

    ck(d_import_name && d_release_name && d_acquire_cred && d_release_cred &&
       d_init_sec_ctx && d_accept_sec_ctx && d_wrap && d_unwrap && d_get_mic &&
       d_verify_mic && d_delete_ctx,
       "resolve 11 core gss_* entry points via dlsym");
    ck(d_import_cred != NULL && d_export_cred != NULL,
       "resolve configure-required pair gss_import_cred/gss_export_cred");

    /* ── 3. iconv UTF16LE 平台前提（NTLM Unicode 转换走 OHOS libc iconv 后端） ── */
    {
        iconv_t cd = iconv_open("UTF16LE", "UTF-8");
        ck(cd != (iconv_t)-1, "iconv_open(\"UTF16LE\",\"UTF-8\") on OHOS libc");
        if (cd != (iconv_t)-1) {
            char in[] = "AB";
            char out[16];
            char *ip = in, *op = out;
            size_t il = 2, ol = sizeof(out);
            size_t r = iconv(cd, &ip, &il, &op, &ol);
            size_t wrote = sizeof(out) - ol;
            ck(r != (size_t)-1 && wrote == 4 && out[0] == 'A' && out[1] == '\0' &&
               out[2] == 'B' && out[3] == '\0',
               "iconv UTF-8 -> UTF16LE emits 4 bytes (NTLM unicode layout)");
            iconv_close(cd);
        }
    }

    /* ── 4. 用户名导入（GSS_C_NT_USER_NAME，OID 符号来自 libgssapi_krb5） ── */
    nbuf.value = (void *)username;
    nbuf.length = strlen(username);
    maj = d_import_name(&min, &nbuf, GSS_C_NT_USER_NAME, &user_name);
    ck(maj == GSS_S_COMPLETE && user_name != GSS_C_NO_NAME,
       "gss_import_name(GSS_C_NT_USER_NAME, \"TESTDOM\\\\testuser\")");

    if (setenv("NTLM_USER_FILE", cred_file, 1) == 0) {
        g_checks++;
        printf("[PASS] setenv(NTLM_USER_FILE)=%s\n", cred_file);
    } else {
        g_checks++;
        g_fails++;
        printf("[FAIL] setenv(NTLM_USER_FILE)\n");
    }

    /* ── 5. 客户端凭据获取（凭据文件 = 端到端前提，非内存内自造） ── */
    maj = d_acquire_cred(&min, user_name, GSS_C_INDEFINITE, GSS_C_NO_OID_SET,
                         GSS_C_INITIATE, &cli_cred, NULL, NULL);
    ck(maj == GSS_S_COMPLETE && cli_cred != GSS_C_NO_CREDENTIAL,
       "gss_acquire_cred(GSS_C_INITIATE) from NTLM_USER_FILE");

    /* ── 6. 服务名导入 + 服务端凭据 ── */
    nbuf.value = (void *)srvname;
    nbuf.length = strlen(srvname);
    maj = d_import_name(&min, &nbuf, GSS_C_NT_HOSTBASED_SERVICE, &srv_name);
    ck(maj == GSS_S_COMPLETE && srv_name != GSS_C_NO_NAME,
       "gss_import_name(GSS_C_NT_HOSTBASED_SERVICE, \"test@testserver\")");

    maj = d_acquire_cred(&min, srv_name, GSS_C_INDEFINITE, GSS_C_NO_OID_SET,
                         GSS_C_ACCEPT, &srv_cred, NULL, NULL);
    ck(maj == GSS_S_COMPLETE && srv_cred != GSS_C_NO_CREDENTIAL,
       "gss_acquire_cred(GSS_C_ACCEPT) for acceptor");

    /* ── 7. 四步 NTLM 握手（init <-> accept，各步断言 token 非空） ── */
    maj = d_init_sec_ctx(&min, cli_cred, &cli_ctx, srv_name, GSS_C_NO_OID,
                         req_flags, 0, GSS_C_NO_CHANNEL_BINDINGS,
                         GSS_C_NO_BUFFER, &actual_mech, &cli_tok, NULL, NULL);
    ck(maj == GSS_S_CONTINUE_NEEDED && cli_tok.length > 0,
       "step1 gss_init_sec_context -> CONTINUE_NEEDED with token");

    maj = d_accept_sec_ctx(&min, &srv_ctx, srv_cred, &cli_tok,
                           GSS_C_NO_CHANNEL_BINDINGS, NULL, &actual_mech,
                           &srv_tok, NULL, NULL, NULL);
    ck(maj == GSS_S_CONTINUE_NEEDED && srv_tok.length > 0,
       "step2 gss_accept_sec_context -> CONTINUE_NEEDED with token");
    gss_release_buffer(&min, &cli_tok);

    maj = d_init_sec_ctx(&min, cli_cred, &cli_ctx, srv_name, GSS_C_NO_OID,
                         req_flags, 0, GSS_C_NO_CHANNEL_BINDINGS,
                         &srv_tok, &actual_mech, &cli_tok, NULL, NULL);
    ck(maj == GSS_S_COMPLETE && cli_tok.length > 0,
       "step3 gss_init_sec_context -> COMPLETE with token");
    gss_release_buffer(&min, &srv_tok);

    maj = d_accept_sec_ctx(&min, &srv_ctx, srv_cred, &cli_tok,
                           GSS_C_NO_CHANNEL_BINDINGS, NULL, &actual_mech,
                           &srv_tok, NULL, NULL, NULL);
    /* 上游 tests/ntlmssptest.c inner_setup_channel 只断言 maj==GSS_S_COMPLETE，
     * 不查末步输出 token 长度——NTLM 第三腿（Authenticate）处理完后服务端没有
     * 追加消息可发，空 token 合法。此处对齐上游判据，另打一行长度留痕。 */
    printf("INFO step4 maj=0x%08x min=%u srv_token=%zu bytes\n",
           (unsigned)maj, (unsigned)min, (size_t)srv_tok.length);
    ck(maj == GSS_S_COMPLETE,
       "step4 gss_accept_sec_context -> COMPLETE (末步 token 允许为空，同上游 inner_setup_channel 判据)");
    gss_release_buffer(&min, &cli_tok);
    gss_release_buffer(&min, &srv_tok);
    ck(cli_ctx != GSS_C_NO_CONTEXT && srv_ctx != GSS_C_NO_CONTEXT,
       "both security contexts established");

    /* ── 8. wrap(conf)/unwrap 载荷往返 ── */
    msg.value = (void *)payload;
    msg.length = strlen(payload);
    maj = d_wrap(&min, cli_ctx, 1 /* conf */, GSS_QOP_DEFAULT, &msg, &conf_state,
                 &exp_tok);
    ck(maj == GSS_S_COMPLETE && exp_tok.length > msg.length && conf_state == 1,
       "gss_wrap(conf=1) produces sealed token");

    {
        gss_buffer_desc dec = GSS_C_EMPTY_BUFFER;
        int dec_conf = 0;
        maj = d_unwrap(&min, srv_ctx, &exp_tok, &dec, &dec_conf, &qop);
        ck(maj == GSS_S_COMPLETE && dec_conf == 1 && dec.length == msg.length &&
           memcmp(dec.value, msg.value, msg.length) == 0,
           "gss_unwrap restores plaintext payload byte-for-byte (conf=1)");
        gss_release_buffer(&min, &dec);
    }
    gss_release_buffer(&min, &exp_tok);

    /* ── 9. get_mic/verify_mic 往返 ── */
    maj = d_get_mic(&min, cli_ctx, GSS_QOP_DEFAULT, &msg, &mic_tok);
    ck(maj == GSS_S_COMPLETE && mic_tok.length > 0,
       "gss_get_mic(client) produces MIC");
    {
        OM_uint32 vmaj = d_verify_mic(&min, srv_ctx, &msg, &mic_tok, &qop);
        ck(vmaj == GSS_S_COMPLETE, "gss_verify_mic(server) accepts MIC");
    }
    gss_release_buffer(&min, &mic_tok);

    /* ── 10. 资源释放（全部 COMPLETE、句柄归零） ── */
    {
        int clean = 1;
        if (d_delete_ctx(&min, &cli_ctx, GSS_C_NO_BUFFER) != GSS_S_COMPLETE) clean = 0;
        if (d_delete_ctx(&min, &srv_ctx, GSS_C_NO_BUFFER) != GSS_S_COMPLETE) clean = 0;
        if (d_release_cred(&min, &cli_cred) != GSS_S_COMPLETE) clean = 0;
        if (d_release_cred(&min, &srv_cred) != GSS_S_COMPLETE) clean = 0;
        if (d_release_name(&min, &user_name) != GSS_S_COMPLETE) clean = 0;
        if (d_release_name(&min, &srv_name) != GSS_S_COMPLETE) clean = 0;
        ck(clean, "release all contexts/creds/names");
    }

    dlclose(dso);
    printf("GSSNTLM_PROBE_RESULT checks=%d fails=%d\n", g_checks, g_fails);
    return g_fails ? 1 : 0;
}
