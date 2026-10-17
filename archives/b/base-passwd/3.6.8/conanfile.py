import os
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy

MUSL_COMPAT_H = r'''/* musl-compat.h — OHOS/musl compatibility shims for update-passwd */
#ifndef MUSL_COMPAT_H
#define MUSL_COMPAT_H
#ifndef PACKAGE_VERSION
#define PACKAGE_VERSION "3.6.8"
#endif
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <pwd.h>
#include <grp.h>
#include <shadow.h>
#include <errno.h>
static struct passwd *compat_fgetpwent(FILE *stream)
{
    static char line[4096]; static struct passwd pw; char *fields[8], *p, *end; int i;
    if (!stream || !fgets(line, sizeof(line), stream)) return NULL;
    p = strchr(line, '\n'); if (p) *p = '\0'; fields[0] = line;
    for (i = 1; i < 8; i++) { fields[i] = NULL; p = fields[i-1] ? strchr(fields[i-1], ':') : NULL; if (p) { *p = '\0'; fields[i] = p + 1; } }
    if (!fields[0] || !fields[1] || !fields[2] || !fields[3]) return NULL;
    pw.pw_name = fields[0]; pw.pw_passwd = fields[1];
    pw.pw_uid = (uid_t)strtoul(fields[2], &end, 10); if (*end) return NULL;
    pw.pw_gid = (gid_t)strtoul(fields[3], &end, 10); if (*end) return NULL;
    pw.pw_gecos = fields[4] ?: ""; pw.pw_dir = fields[5] ?: ""; pw.pw_shell = fields[6] ?: "";
    return &pw;
}
static struct group *compat_fgetgrent(FILE *stream)
{
    static char line[4096], members[4096], *gr_mem_ptrs[256]; static struct group gr; char *p, *end; int n;
    if (!stream || !fgets(line, sizeof(line), stream)) return NULL;
    p = strchr(line, '\n'); if (p) *p = '\0';
    char *name = line; p = strchr(name, ':'); if (!p) return NULL; *p++ = '\0';
    char *passwd = p; p = strchr(passwd, ':'); if (!p) return NULL; *p++ = '\0';
    char *gidstr = p; p = strchr(gidstr, ':'); if (!p) return NULL; *p++ = '\0';
    char *memstr = p;
    gr.gr_name = name; gr.gr_passwd = passwd;
    gr.gr_gid = (gid_t)strtoul(gidstr, &end, 10); if (*end) return NULL;
    if (memstr && *memstr) {
        strncpy(members, memstr, sizeof(members)-1); members[sizeof(members)-1] = '\0';
        n = 0; gr_mem_ptrs[n++] = members;
        for (p = members; *p && n < 255; p++) { if (*p == ',') { *p = '\0'; gr_mem_ptrs[n++] = p+1; } }
        gr_mem_ptrs[n] = NULL;
    } else { gr_mem_ptrs[0] = NULL; }
    gr.gr_mem = gr_mem_ptrs;
    return &gr;
}
static struct spwd *compat_fgetspent(FILE *stream)
{
    static char line[4096]; static struct spwd sp; char *fields[10], *p; int i;
    if (!stream || !fgets(line, sizeof(line), stream)) return NULL;
    p = strchr(line, '\n'); if (p) *p = '\0'; fields[0] = line;
    for (i = 1; i < 10; i++) { fields[i] = NULL; p = fields[i-1] ? strchr(fields[i-1], ':') : NULL; if (p) { *p = '\0'; fields[i] = p+1; } }
    if (!fields[0]) return NULL;
    sp.sp_namp = fields[0]; sp.sp_pwdp = fields[1] ?: "";
    sp.sp_lstchg = fields[2] && *fields[2] ? atol(fields[2]) : -1; sp.sp_min = fields[3] && *fields[3] ? atol(fields[3]) : -1;
    sp.sp_max = fields[4] && *fields[4] ? atol(fields[4]) : -1; sp.sp_warn = fields[5] && *fields[5] ? atol(fields[5]) : -1;
    sp.sp_inact = fields[6] && *fields[6] ? atol(fields[6]) : -1; sp.sp_expire = fields[7] && *fields[7] ? atol(fields[7]) : -1;
    sp.sp_flag = fields[8] && *fields[8] ? strtoul(fields[8], NULL, 10) : ~0UL;
    return &sp;
}
static int compat_putspent(const struct spwd *sp, FILE *f)
{
    if (!sp || !f) return -1;
    return (fprintf(f, "%s:%s:%ld:%ld:%ld:%ld:%ld:%ld:%lu\n",
        sp->sp_namp ?: "", sp->sp_pwdp ?: "", sp->sp_lstchg, sp->sp_min,
        sp->sp_max, sp->sp_warn, sp->sp_inact, sp->sp_expire, sp->sp_flag) < 0) ? -1 : 0;
}
static int compat_lckpwdf(void)  { return 0; }
static int compat_ulckpwdf(void) { return 0; }
#define fgetpwent(s) compat_fgetpwent(s)
#define fgetgrent(s) compat_fgetgrent(s)
#define fgetspent(s) compat_fgetspent(s)
#define putspent(sp,f) compat_putspent(sp,f)
#define lckpwdf() compat_lckpwdf()
#define ulckpwdf() compat_ulckpwdf()
#endif
'''

class BasePasswdConan(ConanFile):
    name = "base-passwd"
    version = "3.6.8"
    description = "Debian base system master password and group files"
    license = "GPL-2.0-only"
    homepage = "https://salsa.debian.org/debian/base-passwd"
    url = ""
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"OS {self.settings.os} not supported")
    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # Write musl-compat.h into source folder (r02-r05 verified approach)
        with open(os.path.join(self.source_folder, "musl-compat.h"), "w") as f:
            f.write(MUSL_COMPAT_H)
    def layout(self):
        self.folders.build = "."
        self.folders.generators = "."
    def build(self):
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = compilers.get("c", "clang")
        if not os.path.isfile(cc): cc = "clang"
        config_h = os.path.join(self.build_folder, "config.h")
        with open(config_h, "w") as f:
            f.write("/* config.h - generated by conan recipe */\n")
            f.write("#define _GNU_SOURCE 1\n")
        compat_h = os.path.join(self.build_folder, "musl-compat.h")
        # layout(): build_folder == source_folder, musl-compat.h written by source()
        cflags = f"-O2 -DHAVE_CONFIG_H -D_GNU_SOURCE -include {compat_h}"
        src = os.path.join(self.build_folder, "update-passwd.c")
        out = os.path.join(self.build_folder, "update-passwd")
        self.run(f"{cc} {cflags} -I{self.build_folder} -o {out} {src}", ignore_errors=True)
        if not os.path.isfile(out):
            self.run(f"{cc} {cflags} -I{self.build_folder} -o {out} {src}")
    def package(self):
        copy(self, "update-passwd", src=self.build_folder, dst=os.path.join(self.package_folder, "sbin"))
        copy(self, "passwd.master", src=self.build_folder, dst=os.path.join(self.package_folder, "share", "base-passwd"))
        copy(self, "group.master", src=self.build_folder, dst=os.path.join(self.package_folder, "share", "base-passwd"))
    def package_info(self):
        self.cpp_info.libs = []; self.cpp_info.includedirs = []; self.cpp_info.libdirs = []; self.cpp_info.bindirs = ["sbin"]