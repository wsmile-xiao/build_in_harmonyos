#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <radcli/radcli.h>

static int failures = 0;

#define CHECK(cond, msg) do { \
    if (!(cond)) { \
        fprintf(stderr, "FAIL %d: %s\n", __LINE__, msg); \
        failures++; \
    } else { \
        printf("ok %d: %s\n", __LINE__, msg); \
    } \
} while (0)

static const char *min_dict =
    "ATTRIBUTE\tUser-Name\t\t1\tstring\n"
    "ATTRIBUTE\tUser-Password\t\t2\tstring\n"
    "ATTRIBUTE\tFramed-Protocol\t\t7\tinteger\n"
    "ATTRIBUTE\tFramed-IP-Address\t8\tipv4addr\n"
    "ATTRIBUTE\tSession-Timeout\t\t27\tinteger\n"
    "ATTRIBUTE\tIdle-Timeout\t\t28\tinteger\n"
    "ATTRIBUTE\tFramed-IPv6-Address\t168\tipv6addr\n"
    "VALUE\t\tFramed-Protocol\t\tPPP\t\t\t1\n";

int main(void)
{
    rc_handle *rh = rc_new();
    CHECK(rh != NULL, "rc_new returns handle");
    if (rh == NULL) {
        return 1;
    }

    /* Dictionary from buffer: new API in 1.2.11 (#24). */
    CHECK(rc_read_dictionary_from_buffer(rh, min_dict, strlen(min_dict)) == 0,
          "rc_read_dictionary_from_buffer loads minimal dict");

    DICT_ATTR *da = rc_dict_findattr(rh, "User-Name");
    CHECK(da != NULL && da->value == PW_USER_NAME && da->type == PW_TYPE_STRING,
          "rc_dict_findattr User-Name=1/string");

    da = rc_dict_getattr(rh, PW_SESSION_TIMEOUT);
    CHECK(da != NULL && da->type == PW_TYPE_INTEGER,
          "rc_dict_getattr Session-Timeout is integer");

    DICT_VALUE *dv = rc_dict_findval(rh, "PPP");
    CHECK(dv != NULL, "rc_dict_findval PPP exists");

    /* AVPair encode/decode offline (distilled from upstream avpair.c). */
    VALUE_PAIR *list = NULL;
    CHECK(rc_avpair_parse(rh, "User-Name=testuser", &list) == 0,
          "rc_avpair_parse User-Name");
    CHECK(rc_avpair_parse(rh, "Session-Timeout=55", &list) == 0,
          "rc_avpair_parse Session-Timeout");
    CHECK(rc_avpair_parse(rh, "Framed-Protocol=PPP", &list) == 0,
          "rc_avpair_parse Framed-Protocol");
    CHECK(rc_avpair_parse(rh, "Framed-IP-Address=192.168.1.1", &list) == 0,
          "rc_avpair_parse Framed-IP-Address");
    CHECK(rc_avpair_parse(rh, "Framed-IPv6-Address=::1", &list) == 0,
          "rc_avpair_parse Framed-IPv6-Address");

    VALUE_PAIR *vp = rc_avpair_get(list, PW_USER_NAME, 0);
    CHECK(vp != NULL, "rc_avpair_get User-Name found");
    if (vp != NULL) {
        char *raw = NULL;
        unsigned raw_len = 0;
        unsigned atype = 0, aid = 0;
        rc_avpair_get_attr(vp, &atype, &aid);
        CHECK(atype == PW_TYPE_STRING && aid == (unsigned)PW_USER_NAME,
              "rc_avpair_get_attr User-Name type/id");
        CHECK(rc_avpair_get_raw(vp, &raw, &raw_len) == 0 && raw_len == 8 &&
              memcmp(raw, "testuser", 8) == 0,
              "rc_avpair_get_raw User-Name=testuser");
    }

    vp = rc_avpair_get(list, PW_SESSION_TIMEOUT, 0);
    CHECK(vp != NULL, "rc_avpair_get Session-Timeout found");
    if (vp != NULL) {
        uint32_t u = 0;
        CHECK(rc_avpair_get_uint32(vp, &u) == 0 && u == 55,
              "rc_avpair_get_uint32 Session-Timeout=55");
    }

    vp = rc_avpair_get(list, PW_FRAMED_IP_ADDRESS, 0);
    CHECK(vp != NULL, "rc_avpair_get Framed-IP-Address found");
    if (vp != NULL) {
        uint32_t u = 0;
        /* 192.168.1.1 in host byte order = 3232235777. */
        CHECK(rc_avpair_get_uint32(vp, &u) == 0 && u == 3232235777u,
              "rc_avpair_get_uint32 Framed-IP-Address=192.168.1.1");
    }

    /* Walk with the new iterator API and count nodes. */
    {
        int n = 0;
        VALUE_PAIR *it = list;
        while (it != NULL) {
            n++;
            it = rc_avpair_next(it);
        }
        CHECK(n == 5, "rc_avpair_next walks 5 nodes");
    }

    /* Remove head and verify the list shrinks. */
    {
        int head_attr = list->attribute;
        rc_avpair_remove(&list, head_attr, 0);
        int n = 0;
        VALUE_PAIR *it = list;
        while (it != NULL) {
            n++;
            it = it->next;
        }
        CHECK(n == 4, "rc_avpair_remove shrinks list to 4");
    }

    rc_avpair_free(list);
    rc_destroy(rh);

    if (failures != 0) {
        fprintf(stderr, "test_radcli: %d check(s) FAILED\n", failures);
        return 1;
    }
    printf("test_radcli: ALL CHECKS PASSED\n");
    return 0;
}
