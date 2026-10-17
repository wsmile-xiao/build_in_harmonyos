/* Stub implementations for libeconf API on OHOS.
 * SPDX-License-Identifier: MIT */
#include <stdlib.h>

#include "libeconf.h"

econf_err econf_new(econf_file **key_file) {
    if (key_file) *key_file = NULL;
    return ECONF_SUCCESS;
}
econf_err econf_read(econf_file **key_file, const char *usr_conf_dir,
                     const char *etc_conf_dir, const char *project_name,
                     const char *group, const char *extension,
                     const char *suffix) {
    (void) key_file; (void) usr_conf_dir; (void) etc_conf_dir;
    (void) project_name; (void) group; (void) extension; (void) suffix;
    return ECONF_NOFILE;
}
econf_err econf_get(econf_file *key_file, const char *group,
                    const char *key, char **result) {
    (void) key_file; (void) group; (void) key;
    if (result) *result = NULL;
    return ECONF_NOKEY;
}
/* 真实 libeconf.h 中 econf_free 为 _Generic 宏（分派到 econf_freeFile/
 * econf_freeArray）→ 提供这两个函数（替代原 econf_free 实现） */
econf_file *econf_file_free(econf_file *key_file) {
    (void) key_file;
    return NULL;
}
const char *econf_errString(econf_err error) {
    (void) error;
    return "stub";
}

void econf_freeFilep(econf_file **key_file) {
    if (key_file) *key_file = NULL;
}

void econf_freeArrayp(char ***values) {
    if (values && *values) free(*values);
}

/* Auto-generated from real libeconf.h */
#include <stdbool.h>
#include <stdint.h>
econf_err econf_readFile(econf_file **result, const char *file_name,
				    const char *delim, const char *comment) {
    (void) result; (void) file_name; (void) delim; (void) comment;
    return ECONF_SUCCESS;
}
econf_err econf_mergeFiles(econf_file **merged_file,
				       econf_file *usr_file, econf_file *etc_file) {
    (void) merged_file; (void) usr_file; (void) etc_file;
    return ECONF_SUCCESS;
}
econf_err econf_readDirs(econf_file **key_file,
					  const char *usr_conf_dir,
					  const char *etc_conf_dir,
					  const char *project_name,
					  const char *config_suffix,
					  const char *delim,
					  const char *comment) {
    (void) key_file; (void) usr_conf_dir; (void) etc_conf_dir; (void) project_name; (void) config_suffix; (void) delim; (void) comment;
    return ECONF_SUCCESS;
}
econf_err econf_newKeyFile(econf_file **result, char delimiter, char comment) {
    (void) result; (void) delimiter; (void) comment;
    return ECONF_SUCCESS;
}
econf_err econf_newIniFile(econf_file **result) {
    (void) result;
    return ECONF_SUCCESS;
}
econf_err econf_writeFile(econf_file *key_file, const char *save_to_dir,
				      const char *file_name) {
    (void) key_file; (void) save_to_dir; (void) file_name;
    return ECONF_SUCCESS;
}
econf_err econf_getGroups(econf_file *kf, size_t *length, char ***groups) {
    (void) kf; (void) length; (void) groups;
    return ECONF_SUCCESS;
}
econf_err econf_getKeys(econf_file *kf, const char *group, size_t *length, char ***keys) {
    (void) kf; (void) group; (void) length; (void) keys;
    return ECONF_SUCCESS;
}
econf_err econf_getIntValue(econf_file *kf, const char *group, const char *key, int32_t *result) {
    (void) kf; (void) group; (void) key; (void) result;
    return ECONF_SUCCESS;
}
econf_err econf_getInt64Value(econf_file *kf, const char *group, const char *key, int64_t *result) {
    (void) kf; (void) group; (void) key; (void) result;
    return ECONF_SUCCESS;
}
econf_err econf_getUIntValue(econf_file *kf, const char *group, const char *key, uint32_t *result) {
    (void) kf; (void) group; (void) key; (void) result;
    return ECONF_SUCCESS;
}
econf_err econf_getUInt64Value(econf_file *kf, const char *group, const char *key, uint64_t *result) {
    (void) kf; (void) group; (void) key; (void) result;
    return ECONF_SUCCESS;
}
econf_err econf_getFloatValue(econf_file *kf, const char *group, const char *key, float *result) {
    (void) kf; (void) group; (void) key; (void) result;
    return ECONF_SUCCESS;
}
econf_err econf_getDoubleValue(econf_file *kf, const char *group, const char *key, double *result) {
    (void) kf; (void) group; (void) key; (void) result;
    return ECONF_SUCCESS;
}
econf_err econf_getStringValue(econf_file *kf, const char *group, const char *key, char **result) {
    (void) kf; (void) group; (void) key; (void) result;
    return ECONF_SUCCESS;
}
econf_err econf_getBoolValue(econf_file *kf, const char *group, const char *key, bool *result) {
    (void) kf; (void) group; (void) key; (void) result;
    return ECONF_SUCCESS;
}
econf_err econf_getIntValueDef(econf_file *kf, const char *group, const char *key, int32_t *result, int32_t def) {
    (void) kf; (void) group; (void) key; (void) result; (void) def;
    return ECONF_SUCCESS;
}
econf_err econf_getInt64ValueDef(econf_file *kf, const char *group, const char *key, int64_t *result, int64_t def) {
    (void) kf; (void) group; (void) key; (void) result; (void) def;
    return ECONF_SUCCESS;
}
econf_err econf_getUIntValueDef(econf_file *kf, const char *group, const char *key, uint32_t *result, uint32_t def) {
    (void) kf; (void) group; (void) key; (void) result; (void) def;
    return ECONF_SUCCESS;
}
econf_err econf_getUInt64ValueDef(econf_file *kf, const char *group, const char *key, uint64_t *result, uint64_t def) {
    (void) kf; (void) group; (void) key; (void) result; (void) def;
    return ECONF_SUCCESS;
}
econf_err econf_getFloatValueDef(econf_file *kf, const char *group, const char *key, float *result, float def) {
    (void) kf; (void) group; (void) key; (void) result; (void) def;
    return ECONF_SUCCESS;
}
econf_err econf_getDoubleValueDef(econf_file *kf, const char *group, const char *key, double *result, double def) {
    (void) kf; (void) group; (void) key; (void) result; (void) def;
    return ECONF_SUCCESS;
}
econf_err econf_getStringValueDef(econf_file *kf, const char *group, const char *key, char **result, char *def) {
    (void) kf; (void) group; (void) key; (void) result; (void) def;
    return ECONF_SUCCESS;
}
econf_err econf_getBoolValueDef(econf_file *kf, const char *group, const char *key, bool *result, bool def) {
    (void) kf; (void) group; (void) key; (void) result; (void) def;
    return ECONF_SUCCESS;
}
econf_err econf_setIntValue(econf_file *kf, const char *group, const char *key, int32_t value) {
    (void) kf; (void) group; (void) key; (void) value;
    return ECONF_SUCCESS;
}
econf_err econf_setInt64Value(econf_file *kf, const char *group, const char *key, int64_t value) {
    (void) kf; (void) group; (void) key; (void) value;
    return ECONF_SUCCESS;
}
econf_err econf_setUIntValue(econf_file *kf, const char *group, const char *key, uint32_t value) {
    (void) kf; (void) group; (void) key; (void) value;
    return ECONF_SUCCESS;
}
econf_err econf_setUInt64Value(econf_file *kf, const char *group, const char *key, uint64_t value) {
    (void) kf; (void) group; (void) key; (void) value;
    return ECONF_SUCCESS;
}
econf_err econf_setFloatValue(econf_file *kf, const char *group, const char *key, float value) {
    (void) kf; (void) group; (void) key; (void) value;
    return ECONF_SUCCESS;
}
econf_err econf_setDoubleValue(econf_file *kf, const char *group, const char *key, double value) {
    (void) kf; (void) group; (void) key; (void) value;
    return ECONF_SUCCESS;
}
econf_err econf_setStringValue(econf_file *kf, const char *group, const char *key, const char *value) {
    (void) kf; (void) group; (void) key; (void) value;
    return ECONF_SUCCESS;
}
econf_err econf_setBoolValue(econf_file *kf, const char *group, const char *key, const char *value) {
    (void) kf; (void) group; (void) key; (void) value;
    return ECONF_SUCCESS;
}
void econf_freeFile(econf_file *kf) { (void) kf; }

econf_err econf_readConfig(econf_file **result, const char *usr_conf_dir,
                           const char *etc_conf_dir, const char *project_name,
                           const char *group, const char *extension,
                           const char *suffix) {
    (void) result; (void) usr_conf_dir; (void) etc_conf_dir;
    (void) project_name; (void) group; (void) extension; (void) suffix;
    return ECONF_NOFILE;
}

econf_err econf_newKeyFile_with_options(econf_file **result, char delimiter,
                                        char comment, const char *delimiter_value) {
    (void) result; (void) delimiter; (void) comment; (void) delimiter_value;
    return ECONF_SUCCESS;
}
