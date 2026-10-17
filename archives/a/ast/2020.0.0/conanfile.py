from conan import ConanFile
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, save, mkdir
from conan.tools.layout import basic_layout
import os


# Compat fts.h content for platforms lacking BSD fts(3) API (e.g., HarmonyOS)
FTS_H_CONTENT = r"""/*
 * Minimal fts.h compatibility header for platforms lacking it (e.g., HarmonyOS).
 * Provides the BSD fts(3) API declarations needed by AST/ksh.
 */
#ifndef _FTS_H
#define _FTS_H

#include <sys/types.h>
#include <sys/stat.h>

typedef struct {
    struct _ftsent *fts_cur;
    struct _ftsent *fts_child;
    struct _ftsent **fts_array;
    dev_t fts_dev;
    int fts_options;
    int (*fts_compar)(const struct _ftsent **, const struct _ftsent **);
} FTS;

typedef struct _ftsent {
    struct _ftsent *fts_cycle;
    struct _ftsent *fts_parent;
    struct _ftsent *fts_link;
    long fts_number;
    void *fts_pointer;
    char *fts_access;
    char *fts_accpath;
    struct stat *fts_statp;
    int fts_errno;
    char *fts_path;
    size_t fts_pathlen;
    char *fts_name;
    unsigned short fts_namelen;
    ino_t fts_ino;
    dev_t fts_dev;
    nlink_t fts_nlink;
    size_t fts_level;
    unsigned short fts_info;
    unsigned short fts_flags;
    int fts_symfd;
    struct _ftsent *fts_child;
    char fts_namebuf[1];
} FTSENT;

#define FTS_COMFOLLOW    0x0001
#define FTS_LOGICAL      0x0002
#define FTS_NOCHDIR      0x0004
#define FTS_PHYSICAL     0x0008
#define FTS_SEEDOT       0x0010
#define FTS_XDEV         0x0020

#define FTS_AGAIN        1
#define FTS_FOLLOW       2
#define FTS_SKIP         3

#define FTS_D            1
#define FTS_DC           2
#define FTS_DEFAULT      3
#define FTS_DNR          4
#define FTS_DOT          5
#define FTS_DP           6
#define FTS_ERR          7
#define FTS_F            8
#define FTS_NS           9
#define FTS_NSOK        10
#define FTS_SL          11
#define FTS_SLNONE     12

#define FTS_NOSTAT      0x0040
#define FTS_OPTIONMASK  0x007f

FTS *fts_open(char * const *path_argv, int options,
              int (*compar)(const FTSENT **, const FTSENT **));
FTSENT *fts_read(FTS *ftsp);
FTSENT *fts_children(FTS *ftsp, int instr);
int fts_set(FTS *ftsp, FTSENT *f, int instr);
int fts_close(FTS *ftsp);

#endif /* _FTS_H */
"""

# Compat fts.c implementation
FTS_C_CONTENT = r"""/*
 * fts.c - Implementation of the BSD fts(3) API for platforms lacking it.
 */
#include <sys/types.h>
#include <sys/stat.h>
#include <dirent.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <errno.h>
#include "fts.h"

#define FTS_ENT_ALLOC_SIZE(name_len) (sizeof(FTSENT) + (name_len))

typedef struct _fts_private {
    FTS fts;
    FTSENT *cur;
    FTSENT *head;
    FTSENT **tail;
    FTSENT *parent_root;
} FTS_PRIVATE;

static FTSENT *fts_alloc(FTS *sp, const char *name, size_t namelen);
static unsigned short fts_stat(FTS *sp, FTSENT *p, int follow);

FTS *
fts_open(char * const *argv, int options,
         int (*compar)(const FTSENT **, const FTSENT **))
{
    FTS_PRIVATE *priv;
    FTS *sp;
    FTSENT *root, *parent;
    size_t nitems;
    char * const *argv_save;

    if (options & ~FTS_OPTIONMASK) { errno = EINVAL; return NULL; }

    priv = calloc(1, sizeof(FTS_PRIVATE));
    if (!priv) return NULL;
    sp = (FTS *)priv;
    sp->fts_options = options | FTS_NOCHDIR;
    sp->fts_compar = (int (*)(const struct _ftsent **, const struct _ftsent **))compar;

    nitems = 0;
    for (argv_save = argv; *argv_save; ++argv_save) nitems++;

    parent = fts_alloc(sp, "", 0);
    if (!parent) goto fail;
    parent->fts_level = 0;
    priv->parent_root = parent;

    root = fts_alloc(sp, "", 0);
    if (!root) { free(parent); goto fail; }
    root->fts_level = 0;
    root->fts_parent = parent;

    priv->head = NULL;
    priv->tail = &priv->head;

    for (int i = 0; i < (int)nitems; i++) {
        FTSENT *fp;
        struct stat st;
        size_t len = strlen(argv[i]);
        fp = fts_alloc(sp, argv[i], len);
        if (!fp) continue;
        fp->fts_path = strdup(argv[i]);
        fp->fts_pathlen = len;
        fp->fts_level = 0;
        fp->fts_parent = parent;
        if (lstat(argv[i], &st) == 0) {
            fp->fts_statp = malloc(sizeof(struct stat));
            if (fp->fts_statp) memcpy(fp->fts_statp, &st, sizeof(struct stat));
            if (S_ISDIR(st.st_mode)) fp->fts_info = FTS_D;
            else if (S_ISLNK(st.st_mode)) fp->fts_info = FTS_SL;
            else fp->fts_info = FTS_F;
        } else { fp->fts_info = FTS_NS; }
        *(priv->tail) = fp;
        priv->tail = &fp->fts_link;
    }
    priv->cur = priv->head;
    return sp;
fail:
    free(priv);
    return NULL;
}

static FTSENT *
fts_alloc(FTS *sp, const char *name, size_t namelen)
{
    FTSENT *p;
    size_t len = FTS_ENT_ALLOC_SIZE(namelen);
    p = calloc(1, len + namelen + 1);
    if (!p) return NULL;
    p->fts_name = (char *)(p + 1);
    if (namelen > 0) memcpy(p->fts_name, name, namelen);
    p->fts_name[namelen] = '\0';
    p->fts_namelen = (unsigned short)namelen;
    return p;
}

static unsigned short
fts_stat(FTS *sp, FTSENT *p, int follow)
{
    struct stat *sb;
    int saved_errno;
    char *path;
    (void)sp;
    if (!p->fts_statp) {
        sb = malloc(sizeof(struct stat));
        if (!sb) return FTS_ERR;
        p->fts_statp = sb;
    } else { sb = p->fts_statp; }
    path = p->fts_path ? p->fts_path : p->fts_name;
    if (follow ? stat(path, sb) : lstat(path, sb)) {
        saved_errno = errno;
        free(sb);
        p->fts_statp = NULL;
        errno = saved_errno;
        return FTS_NS;
    }
    if (S_ISDIR(sb->st_mode)) return FTS_D;
    if (S_ISLNK(sb->st_mode)) return FTS_SL;
    return FTS_F;
}

FTSENT *
fts_read(FTS *sp)
{
    FTS_PRIVATE *priv = (FTS_PRIVATE *)sp;
    FTSENT *p;
    if (!priv->cur) return NULL;
    p = priv->cur;
    priv->cur = p->fts_link;
    if (p->fts_info == FTS_D) {
        DIR *dirp;
        struct dirent *dp;
        char pathbuf[4096];
        if (p->fts_path) snprintf(pathbuf, sizeof(pathbuf), "%s", p->fts_path);
        else snprintf(pathbuf, sizeof(pathbuf), "%s", p->fts_name);
        dirp = opendir(pathbuf);
        if (!dirp) { p->fts_info = FTS_DNR; return p; }
        p->fts_child = NULL;
        FTSENT **tail = &p->fts_child;
        while ((dp = readdir(dirp)) != NULL) {
            FTSENT *child;
            size_t d_namlen = strlen(dp->d_name);
            if (dp->d_name[0] == '.' && (d_namlen == 1 || (d_namlen == 2 && dp->d_name[1] == '.'))) continue;
            child = fts_alloc(sp, dp->d_name, d_namlen);
            if (!child) continue;
            child->fts_parent = p;
            child->fts_level = p->fts_level + 1;
            snprintf(pathbuf, sizeof(pathbuf), "%s/%s", p->fts_path ? p->fts_path : p->fts_name, dp->d_name);
            child->fts_path = strdup(pathbuf);
            child->fts_pathlen = strlen(pathbuf);
            child->fts_info = fts_stat(sp, child, (sp->fts_options & FTS_LOGICAL) != 0);
            *tail = child;
            tail = &child->fts_link;
        }
        closedir(dirp);
    }
    return p;
}

FTSENT *
fts_children(FTS *sp, int instr)
{
    FTS_PRIVATE *priv = (FTS_PRIVATE *)sp;
    (void)instr;
    if (!priv->cur) return NULL;
    return priv->cur->fts_child;
}

int
fts_set(FTS *sp, FTSENT *p, int instr)
{
    (void)sp; (void)p; (void)instr;
    return 0;
}

int
fts_close(FTS *sp)
{
    FTS_PRIVATE *priv = (FTS_PRIVATE *)sp;
    FTSENT *p, *next;
    if (!sp) { errno = EINVAL; return -1; }
    p = priv->head;
    while (p) {
        next = p->fts_link;
        if (p->fts_statp) free(p->fts_statp);
        if (p->fts_path) free(p->fts_path);
        free(p);
        p = next;
    }
    if (priv->parent_root) free(priv->parent_root);
    free(priv);
    return 0;
}
"""


class AstConan(ConanFile):
    name = "ast"
    version = "2020.0.0"
    description = "AT&T Software Technology toolkit — includes ksh (KornShell), shcomp, and AST libraries"
    license = "EPL-1.0"
    homepage = "https://github.com/att/ast"
    url = "https://github.com/att/ast"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        tc.project_options["build-api-tests"] = "false"
        tc.project_options["warnings-are-errors"] = "false"
        tc.generate()

        # Set LD_LIBRARY_PATH so lld can find libxml2.so.16 at link time
        # (must be in generate() so it's in buildenv scripts sourced by self.run())
        cc_dict = self.conf.get("tools.build:compiler_executables", check_type=dict) or {}
        cc = cc_dict.get("c")
        if cc:
            import pathlib
            import re
            sdk_bin = os.path.dirname(cc)
            sdk_lib = os.path.normpath(os.path.join(sdk_bin, "..", "lib"))
            # Add LD_LIBRARY_PATH via Environment() so it's in buildenv scripts
            if os.path.isdir(sdk_lib):
                env = Environment()
                env.define("LD_LIBRARY_PATH", sdk_lib)
                env.vars(self).save_script("ast_ld_path")
            # Add ar, ld, ranlib to the meson native file
            native_file = pathlib.Path(self.build_folder) / "conan" / "conan_meson_native.ini"
            if native_file.exists():
                content = native_file.read_text()
                # Add ar, ld, ranlib to [binaries] section after the cpp line
                extra = (f"\nar = '{os.path.join(sdk_bin, 'llvm-ar')}'\n"
                         f"ld = '{os.path.join(sdk_bin, 'ld.lld')}'\n"
                         f"ranlib = '{os.path.join(sdk_bin, 'llvm-ranlib')}'")
                # Insert after the last binary entry in [binaries] section
                content = re.sub(
                    r'(\[binaries\][^\[]*?cpp\s*=\s*[^\n]+)',
                    r'\1' + extra,
                    content,
                    count=1,
                    flags=re.DOTALL
                )
                native_file.write_text(content)

    def build(self):
        # R32: Support both Linux and OHOS
        if self.settings.os not in ("Linux", "OHOS"):
            raise Exception(f"Unsupported OS: {self.settings.os}")
        apply_conandata_patches(self)

        # Create compat fts.h/fts.c for platforms lacking BSD fts(3) (e.g., HarmonyOS)
        compat_dir = os.path.join(self.source_folder, "src", "compat")
        mkdir(self, compat_dir)
        save(self, os.path.join(compat_dir, "fts.h"), FTS_H_CONTENT)
        save(self, os.path.join(compat_dir, "fts.c"), FTS_C_CONTENT)

        # Set LD_LIBRARY_PATH (also set in generate() via Environment for buildenv)
        cc_dict = self.conf.get("tools.build:compiler_executables", check_type=dict) or {}
        cc = cc_dict.get("c")
        if cc:
            sdk_lib = os.path.join(os.path.dirname(os.path.dirname(cc)), "lib")
            if os.path.isdir(sdk_lib):
                current = os.environ.get("LD_LIBRARY_PATH", "")
                if sdk_lib not in current:
                    os.environ["LD_LIBRARY_PATH"] = sdk_lib + (":" + current if current else "")

        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        meson = Meson(self)
        meson.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.includedirs = ["include"]

        # R32: OS check must include OHOS
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["dl", "m"]
