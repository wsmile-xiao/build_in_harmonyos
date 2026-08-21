/* Auto-generated stub implementations matching real systemd 261 sd-json.h */
#include <stdint.h>
#include <stddef.h>
#include <stdarg.h>
#include <sys/types.h>
#include "systemd/sd-json.h"

int sd_json_variant_new_string(sd_json_variant **ret, const char *s) {
    (void) ret; (void) s;
    return 0;
}
int sd_json_variant_new_stringn(sd_json_variant **ret, const char *s, size_t n) {
    (void) ret; (void) s; (void) n;
    return 0;
}
int sd_json_variant_new_base64(sd_json_variant **ret, const void *p, size_t n) {
    (void) ret; (void) p; (void) n;
    return 0;
}
int sd_json_variant_new_base32hex(sd_json_variant **ret, const void *p, size_t n) {
    (void) ret; (void) p; (void) n;
    return 0;
}
int sd_json_variant_new_hex(sd_json_variant **ret, const void *p, size_t n) {
    (void) ret; (void) p; (void) n;
    return 0;
}
int sd_json_variant_new_octescape(sd_json_variant **ret, const void *p, size_t n) {
    (void) ret; (void) p; (void) n;
    return 0;
}
int sd_json_variant_new_integer(sd_json_variant **ret, int64_t i) {
    (void) ret; (void) i;
    return 0;
}
int sd_json_variant_new_unsigned(sd_json_variant **ret, uint64_t u) {
    (void) ret; (void) u;
    return 0;
}
int sd_json_variant_new_real(sd_json_variant **ret, double d) {
    (void) ret; (void) d;
    return 0;
}
int sd_json_variant_new_boolean(sd_json_variant **ret, int b) {
    (void) ret; (void) b;
    return 0;
}
int sd_json_variant_new_array(sd_json_variant **ret, sd_json_variant **array, size_t n) {
    (void) ret; (void) array; (void) n;
    return 0;
}
int sd_json_variant_new_array_bytes(sd_json_variant **ret, const void *p, size_t n) {
    (void) ret; (void) p; (void) n;
    return 0;
}
int sd_json_variant_new_array_strv(sd_json_variant **ret, char **l) {
    (void) ret; (void) l;
    return 0;
}
int sd_json_variant_new_object(sd_json_variant **ret, sd_json_variant **array, size_t n) {
    (void) ret; (void) array; (void) n;
    return 0;
}
int sd_json_variant_new_null(sd_json_variant **ret) {
    (void) ret;
    return 0;
}
int sd_json_variant_new_id128(sd_json_variant **ret, sd_id128_t id) {
    (void) ret; (void) id;
    return 0;
}
int sd_json_variant_new_uuid(sd_json_variant **ret, sd_id128_t id) {
    (void) ret; (void) id;
    return 0;
}
void sd_json_variant_unref_many(sd_json_variant **array, size_t n) {
    (void) array; (void) n;
}
int sd_json_variant_boolean(sd_json_variant *v) {
    (void) v;
    return 0;
}
int sd_json_variant_has_type(sd_json_variant *v, sd_json_variant_type_t type) {
    (void) v; (void) type;
    return 0;
}
int sd_json_variant_is_string(sd_json_variant *v) {
    (void) v;
    return 0;
}
int sd_json_variant_is_integer(sd_json_variant *v) {
    (void) v;
    return 0;
}
int sd_json_variant_is_unsigned(sd_json_variant *v) {
    (void) v;
    return 0;
}
int sd_json_variant_is_real(sd_json_variant *v) {
    (void) v;
    return 0;
}
int sd_json_variant_is_number(sd_json_variant *v) {
    (void) v;
    return 0;
}
int sd_json_variant_is_boolean(sd_json_variant *v) {
    (void) v;
    return 0;
}
int sd_json_variant_is_array(sd_json_variant *v) {
    (void) v;
    return 0;
}
int sd_json_variant_is_object(sd_json_variant *v) {
    (void) v;
    return 0;
}
int sd_json_variant_is_null(sd_json_variant *v) {
    (void) v;
    return 0;
}
int sd_json_variant_is_negative(sd_json_variant *v) {
    (void) v;
    return 0;
}
int sd_json_variant_is_blank_object(sd_json_variant *v) {
    (void) v;
    return 0;
}
int sd_json_variant_is_blank_array(sd_json_variant *v) {
    (void) v;
    return 0;
}
int sd_json_variant_is_normalized(sd_json_variant *v) {
    (void) v;
    return 0;
}
int sd_json_variant_is_sorted(sd_json_variant *v) {
    (void) v;
    return 0;
}
size_t sd_json_variant_elements(sd_json_variant *v) {
    (void) v;
    return 0;
}
int sd_json_variant_equal(sd_json_variant *a, sd_json_variant *b) {
    (void) a; (void) b;
    return 0;
}
void sd_json_variant_sensitive(sd_json_variant *v) {
    (void) v;
}
int sd_json_variant_is_sensitive(sd_json_variant *v) {
    (void) v;
    return 0;
}
int sd_json_variant_is_sensitive_recursive(sd_json_variant *v) {
    (void) v;
    return 0;
}
int sd_json_variant_get_source(sd_json_variant *v, const char **ret_source, unsigned *ret_line, unsigned *ret_column) {
    (void) v; (void) ret_source; (void) ret_line; (void) ret_column;
    return 0;
}
int sd_json_variant_format(sd_json_variant *v, sd_json_format_flags_t flags, char **ret) {
    (void) v; (void) flags; (void) ret;
    return 0;
}
int sd_json_variant_dump(sd_json_variant *v, sd_json_format_flags_t flags, FILE *f, const char *prefix) {
    (void) v; (void) flags; (void) f; (void) prefix;
    return 0;
}
int sd_json_variant_filter(sd_json_variant **v, char **to_remove) {
    (void) v; (void) to_remove;
    return 0;
}
int sd_json_variant_set_field(sd_json_variant **v, const char *field, sd_json_variant *value) {
    (void) v; (void) field; (void) value;
    return 0;
}
int sd_json_variant_set_fieldb(sd_json_variant **v, const char *field, ...) {
    (void) v; (void) field;
    return 0;
}
int sd_json_variant_set_field_string(sd_json_variant **v, const char *field, const char *value) {
    (void) v; (void) field; (void) value;
    return 0;
}
int sd_json_variant_set_field_id128(sd_json_variant **v, const char *field, sd_id128_t value) {
    (void) v; (void) field; (void) value;
    return 0;
}
int sd_json_variant_set_field_uuid(sd_json_variant **v, const char *field, sd_id128_t value) {
    (void) v; (void) field; (void) value;
    return 0;
}
int sd_json_variant_set_field_integer(sd_json_variant **v, const char *field, int64_t value) {
    (void) v; (void) field; (void) value;
    return 0;
}
int sd_json_variant_set_field_unsigned(sd_json_variant **v, const char *field, uint64_t value) {
    (void) v; (void) field; (void) value;
    return 0;
}
int sd_json_variant_set_field_boolean(sd_json_variant **v, const char *field, int b) {
    (void) v; (void) field; (void) b;
    return 0;
}
int sd_json_variant_set_field_strv(sd_json_variant **v, const char *field, char **l) {
    (void) v; (void) field; (void) l;
    return 0;
}
int sd_json_variant_append_array(sd_json_variant **v, sd_json_variant *element) {
    (void) v; (void) element;
    return 0;
}
int sd_json_variant_append_arrayb(sd_json_variant **v, ...) {
    (void) v;
    return 0;
}
int sd_json_variant_append_array_nodup(sd_json_variant **v, sd_json_variant *element) {
    (void) v; (void) element;
    return 0;
}
int sd_json_variant_merge_object(sd_json_variant **v, sd_json_variant *m) {
    (void) v; (void) m;
    return 0;
}
int sd_json_variant_merge_objectb(sd_json_variant **v, ...) {
    (void) v;
    return 0;
}
int sd_json_variant_sort(sd_json_variant **v) {
    (void) v;
    return 0;
}
int sd_json_variant_normalize(sd_json_variant **v) {
    (void) v;
    return 0;
}
int sd_json_parse_with_source(const char *string, const char *source, sd_json_parse_flags_t flags, sd_json_variant **ret, unsigned *reterr_line, unsigned *reterr_column) {
    (void) string; (void) source; (void) flags; (void) ret; (void) reterr_line; (void) reterr_column;
    return 0;
}
int sd_json_parse_with_source_continue(const char **p, const char *source, sd_json_parse_flags_t flags, sd_json_variant **ret, unsigned *reterr_line, unsigned *reterr_column) {
    (void) p; (void) source; (void) flags; (void) ret; (void) reterr_line; (void) reterr_column;
    return 0;
}
int sd_json_parse(const char *string, sd_json_parse_flags_t flags, sd_json_variant **ret, unsigned *reterr_line, unsigned *reterr_column) {
    (void) string; (void) flags; (void) ret; (void) reterr_line; (void) reterr_column;
    return 0;
}
int sd_json_parse_continue(const char **p, sd_json_parse_flags_t flags, sd_json_variant **ret, unsigned *reterr_line, unsigned *reterr_column) {
    (void) p; (void) flags; (void) ret; (void) reterr_line; (void) reterr_column;
    return 0;
}
int sd_json_parse_file_at(FILE *f, int dir_fd, const char *path, sd_json_parse_flags_t flags, sd_json_variant **ret, unsigned *reterr_line, unsigned *reterr_column) {
    (void) f; (void) dir_fd; (void) path; (void) flags; (void) ret; (void) reterr_line; (void) reterr_column;
    return 0;
}
int sd_json_parse_file(FILE *f, const char *path, sd_json_parse_flags_t flags, sd_json_variant **ret, unsigned *reterr_line, unsigned *reterr_column) {
    (void) f; (void) path; (void) flags; (void) ret; (void) reterr_line; (void) reterr_column;
    return 0;
}
int sd_json_parse_fd(const char *path, int fd, sd_json_parse_flags_t flags, sd_json_variant **ret, unsigned *reterr_line, unsigned *reterr_column) {
    (void) path; (void) fd; (void) flags; (void) ret; (void) reterr_line; (void) reterr_column;
    return 0;
}
int sd_json_build(sd_json_variant **ret, ...) {
    (void) ret;
    return 0;
}
int sd_json_buildv(sd_json_variant **ret, va_list ap) {
    (void) ret; (void) ap;
    return 0;
}
int sd_json_dispatch_full(sd_json_variant *v, const sd_json_dispatch_field table[], sd_json_dispatch_callback_t bad, sd_json_dispatch_flags_t flags, void *userdata, const char **reterr_bad_field) {
    (void) v; (void) table; (void) bad; (void) flags; (void) userdata; (void) reterr_bad_field;
    return 0;
}
int sd_json_dispatch(sd_json_variant *v, const sd_json_dispatch_field table[], sd_json_dispatch_flags_t flags, void *userdata) {
    (void) v; (void) table; (void) flags; (void) userdata;
    return 0;
}
int sd_json_dispatch_string(const char *name, sd_json_variant *variant, sd_json_dispatch_flags_t flags, void *userdata) {
    (void) name; (void) variant; (void) flags; (void) userdata;
    return 0;
}
int sd_json_dispatch_const_string(const char *name, sd_json_variant *variant, sd_json_dispatch_flags_t flags, void *userdata) {
    (void) name; (void) variant; (void) flags; (void) userdata;
    return 0;
}
int sd_json_dispatch_strv(const char *name, sd_json_variant *variant, sd_json_dispatch_flags_t flags, void *userdata) {
    (void) name; (void) variant; (void) flags; (void) userdata;
    return 0;
}
int sd_json_dispatch_stdbool(const char *name, sd_json_variant *variant, sd_json_dispatch_flags_t flags, void *userdata) {
    (void) name; (void) variant; (void) flags; (void) userdata;
    return 0;
}
int sd_json_dispatch_intbool(const char *name, sd_json_variant *variant, sd_json_dispatch_flags_t flags, void *userdata) {
    (void) name; (void) variant; (void) flags; (void) userdata;
    return 0;
}
int sd_json_dispatch_tristate(const char *name, sd_json_variant *variant, sd_json_dispatch_flags_t flags, void *userdata) {
    (void) name; (void) variant; (void) flags; (void) userdata;
    return 0;
}
int sd_json_dispatch_variant(const char *name, sd_json_variant *variant, sd_json_dispatch_flags_t flags, void *userdata) {
    (void) name; (void) variant; (void) flags; (void) userdata;
    return 0;
}
int sd_json_dispatch_variant_noref(const char *name, sd_json_variant *variant, sd_json_dispatch_flags_t flags, void *userdata) {
    (void) name; (void) variant; (void) flags; (void) userdata;
    return 0;
}
int sd_json_dispatch_int64(const char *name, sd_json_variant *variant, sd_json_dispatch_flags_t flags, void *userdata) {
    (void) name; (void) variant; (void) flags; (void) userdata;
    return 0;
}
int sd_json_dispatch_uint64(const char *name, sd_json_variant *variant, sd_json_dispatch_flags_t flags, void *userdata) {
    (void) name; (void) variant; (void) flags; (void) userdata;
    return 0;
}
int sd_json_dispatch_uint32(const char *name, sd_json_variant *variant, sd_json_dispatch_flags_t flags, void *userdata) {
    (void) name; (void) variant; (void) flags; (void) userdata;
    return 0;
}
int sd_json_dispatch_int32(const char *name, sd_json_variant *variant, sd_json_dispatch_flags_t flags, void *userdata) {
    (void) name; (void) variant; (void) flags; (void) userdata;
    return 0;
}
int sd_json_dispatch_uint16(const char *name, sd_json_variant *variant, sd_json_dispatch_flags_t flags, void *userdata) {
    (void) name; (void) variant; (void) flags; (void) userdata;
    return 0;
}
int sd_json_dispatch_int16(const char *name, sd_json_variant *variant, sd_json_dispatch_flags_t flags, void *userdata) {
    (void) name; (void) variant; (void) flags; (void) userdata;
    return 0;
}
int sd_json_dispatch_int8(const char *name, sd_json_variant *variant, sd_json_dispatch_flags_t flags, void *userdata) {
    (void) name; (void) variant; (void) flags; (void) userdata;
    return 0;
}
int sd_json_dispatch_uint8(const char *name, sd_json_variant *variant, sd_json_dispatch_flags_t flags, void *userdata) {
    (void) name; (void) variant; (void) flags; (void) userdata;
    return 0;
}
int sd_json_dispatch_double(const char *name, sd_json_variant *variant, sd_json_dispatch_flags_t flags, void *userdata) {
    (void) name; (void) variant; (void) flags; (void) userdata;
    return 0;
}
int sd_json_dispatch_uid_gid(const char *name, sd_json_variant *variant, sd_json_dispatch_flags_t flags, void *userdata) {
    (void) name; (void) variant; (void) flags; (void) userdata;
    return 0;
}
int sd_json_dispatch_id128(const char *name, sd_json_variant *variant, sd_json_dispatch_flags_t flags, void *userdata) {
    (void) name; (void) variant; (void) flags; (void) userdata;
    return 0;
}
int sd_json_dispatch_signal(const char *name, sd_json_variant *variant, sd_json_dispatch_flags_t flags, void *userdata) {
    (void) name; (void) variant; (void) flags; (void) userdata;
    return 0;
}
int sd_json_dispatch_unsupported(const char *name, sd_json_variant *variant, sd_json_dispatch_flags_t flags, void *userdata) {
    (void) name; (void) variant; (void) flags; (void) userdata;
    return 0;
}
int sd_json_variant_strv(sd_json_variant *v, char ***ret) {
    (void) v; (void) ret;
    return 0;
}
int sd_json_variant_unbase64(sd_json_variant *v, void **ret, size_t *ret_size) {
    (void) v; (void) ret; (void) ret_size;
    return 0;
}
int sd_json_variant_unhex(sd_json_variant *v, void **ret, size_t *ret_size) {
    (void) v; (void) ret; (void) ret_size;
    return 0;
}

sd_json_variant *sd_json_variant_unref(sd_json_variant *v) { return v; }
