// SPDX-License-Identifier: Apache-2.0
/* test_package 消费者测试：真实调用 libvarlink 公开 API（R34/PF3 防空壳）。
 * 覆盖：varlink_object_new / set_* / to_json / new_from_json / get_* 往返，
 * 验证序列化 JSON 非空且字段值一致（同时覆盖 OHOS open_memstream 修复路径）。
 */
#include <varlink.h>

#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(void) {
        VarlinkObject *o = NULL, *p = NULL;
        VarlinkArray *arr = NULL;
        char *json = NULL;
        const char *name = NULL;
        int64_t version = 0;
        bool ok = false;
        long r;

        r = varlink_object_new(&o);
        assert(r == 0);
        r = varlink_object_set_string(o, "name", "libvarlink");
        assert(r == 0);
        r = varlink_object_set_int(o, "version", 24001);
        assert(r == 0);
        r = varlink_object_set_bool(o, "ok", true);
        assert(r == 0);
        r = varlink_array_new(&arr);
        assert(r == 0);
        r = varlink_array_append_string(arr, "consumer");
        assert(r == 0);
        r = varlink_object_set_array(o, "tags", arr);
        assert(r == 0);

        r = varlink_object_to_json(o, &json);
        assert(r > 0 && json && strlen(json) > 0);
        printf("serialized: %s\n", json);

        r = varlink_object_new_from_json(&p, json);
        assert(r == 0);
        r = varlink_object_get_string(p, "name", &name);
        assert(r == 0 && strcmp(name, "libvarlink") == 0);
        r = varlink_object_get_int(p, "version", &version);
        assert(r == 0 && version == 24001);
        r = varlink_object_get_bool(p, "ok", &ok);
        assert(r == 0 && ok);

        printf("libvarlink %lld roundtrip OK\n", (long long) version);
        varlink_object_unref(o);
        varlink_object_unref(p);
        varlink_array_unref(arr);
        free(json);
        return 0;
}
