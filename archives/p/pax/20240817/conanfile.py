#!/usr/bin/env python3
"""Conan recipe for pax (paxmirabilis) 20240817.

pax is a POSIX archive interchange tool supporting tar, cpio, and
pax formats. It uses a custom Build.sh script (not autotools).

OHOS lacks fts.h (BSD file tree traversal), so we provide a portable
implementation. OHOS also has large uids that don't fit in ustar headers.
"""
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, save
from conan.tools.layout import basic_layout


# Portable fts.h implementation for non-BSD systems
FTS_H = """\
#ifndef _FTS_H
#define _FTS_H

#include <sys/types.h>
#include <sys/stat.h>

struct _ftsent {
	struct stat st_stat;
	struct stat *fts_statp;
	char *fts_name;
	char *fts_path;
	int fts_errno;
	int fts_info;
	int fts_level;
	int fts_flags;
	short fts_namelen;
	short fts_pathlen;
	void *fts_cycle;
	struct _ftsent *fts_parent;
	struct _ftsent *fts_link;
	long fts_number;
	void *fts_pointer;
};

typedef struct _ftsent FTSENT;
typedef struct _fts FTS;

#define FTS_COMFOLLOW	0x0001
#define FTS_LOGICAL	0x0002
#define FTS_NOCHDIR	0x0004
#define FTS_NOSTAT	0x0008
#define FTS_PHYSICAL	0x0010
#define FTS_XDEV	0x0020
#define FTS_OPTIONMASK	0x003f

#define FTS_AGAIN	0x0001
#define FTS_FOLLOW	0x0002
#define FTS_SKIP	0x0004

#define FTS_D		1
#define FTS_DC		2
#define FTS_DEFAULT	3
#define FTS_DNR		4
#define FTS_DOT		5
#define FTS_DP		6
#define FTS_ERR		7
#define FTS_F		8
#define FTS_NS		9
#define FTS_NSOK	10
#define FTS_SL		11
#define FTS_SLNONE	12

#define FTS_NAMEONLY	0

FTS	*fts_open(char * const *argv, int options,
	    int (*compar)(const FTSENT **, const FTSENT **));
FTSENT	*fts_read(FTS *ftsp);
int	 fts_set(FTS *ftsp, FTSENT *f, int option);
FTSENT	*fts_children(FTS *ftsp, int option);
int	 fts_close(FTS *ftsp);

#endif
"""

# Portable fts.c implementation
FTS_C = r"""#include "fts.h"
#include <sys/types.h>
#include <sys/stat.h>
#include <dirent.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#define ST_NEW	0
#define ST_PRE	1
#define ST_POST	2

struct stack_entry {
	FTSENT *entry;
	int state;
};

struct _fts {
	int options;
	int (*compar)(const FTSENT **, const FTSENT **);
	char **paths;
	int npaths;
	int started;
	struct stack_entry *stack;
	int stack_size;
	int stack_cap;
};

static FTSENT *make_entry(const char *path, const char *name, int level) {
	FTSENT *e = calloc(1, sizeof(*e));
	if (!e) return NULL;
	e->fts_statp = &e->st_stat;
	e->fts_level = level;
	if (name) { e->fts_name = strdup(name); if (!e->fts_name) { free(e); return NULL; } e->fts_namelen = strlen(name); }
	e->fts_path = strdup(path); if (!e->fts_path) { free(e->fts_name); free(e); return NULL; } e->fts_pathlen = strlen(path);
	return e;
}
static void free_entry(FTSENT *e) { if (!e) return; free(e->fts_name); free(e->fts_path); free(e); }
static void push(struct _fts *ftsp, FTSENT *e, int state) {
	if (ftsp->stack_size >= ftsp->stack_cap) { int nc = ftsp->stack_cap ? ftsp->stack_cap*2 : 64; struct stack_entry *ns = realloc(ftsp->stack, nc*sizeof(*ns)); if (!ns) return; ftsp->stack = ns; ftsp->stack_cap = nc; }
	ftsp->stack[ftsp->stack_size].entry = e; ftsp->stack[ftsp->stack_size].state = state; ftsp->stack_size++;
}
static struct stack_entry *pop(struct _fts *ftsp) { if (ftsp->stack_size == 0) return NULL; return &ftsp->stack[--ftsp->stack_size]; }
static FTSENT *read_dir_children(struct _fts *ftsp, FTSENT *parent) {
	DIR *dirp; struct dirent *dp; FTSENT *head=NULL, *tail=NULL, *e; char path[4096];
	int level = parent->fts_level + 1;
	int physical = !(ftsp->options & FTS_LOGICAL);
	int follow = (ftsp->options & (FTS_COMFOLLOW | FTS_LOGICAL));
	dirp = opendir(parent->fts_path);
	if (!dirp) { parent->fts_errno = errno; parent->fts_info = FTS_DNR; return NULL; }
	while ((dp = readdir(dirp)) != NULL) {
		char *dname = dp->d_name;
		if (dname[0] == '.' && (dname[1] == '\0' || (dname[1] == '.' && dname[2] == '\0'))) continue;
		snprintf(path, sizeof(path), "%s/%s", parent->fts_path, dname);
		e = make_entry(path, dname, level); if (!e) continue; e->fts_parent = parent;
		if (physical) {
			if (lstat(e->fts_path, &e->st_stat) == -1) { e->fts_errno = errno; e->fts_info = FTS_NS; }
			else if (S_ISDIR(e->st_stat.st_mode)) e->fts_info = FTS_D;
			else if (S_ISLNK(e->st_stat.st_mode)) { if (follow) { struct stat sb; if (stat(e->fts_path, &sb) == 0) { e->st_stat = sb; e->fts_info = S_ISDIR(sb.st_mode) ? FTS_D : FTS_F; } else e->fts_info = FTS_SLNONE; } else e->fts_info = FTS_SL; }
			else e->fts_info = FTS_F;
		} else {
			if (stat(e->fts_path, &e->st_stat) == -1) { if (lstat(e->fts_path, &e->st_stat) == 0) e->fts_info = FTS_SLNONE; else { e->fts_errno = errno; e->fts_info = FTS_NS; } }
			else if (S_ISDIR(e->st_stat.st_mode)) e->fts_info = FTS_D;
			else if (S_ISLNK(e->st_stat.st_mode)) e->fts_info = FTS_SL;
			else e->fts_info = FTS_F;
		}
		if (!head) { head = e; tail = e; } else { tail->fts_link = e; tail = e; }
	}
	closedir(dirp);
	if (ftsp->compar && head) {
		int i, count=0; FTSENT *p, **arr;
		for (p=head; p; p=p->fts_link) count++;
		arr = malloc(count*sizeof(*arr)); if (arr) {
			i=0; for (p=head; p; p=p->fts_link) arr[i++]=p;
			qsort(arr, count, sizeof(*arr), (int(*)(const void*,const void*))ftsp->compar);
			head = arr[0]; for (i=0; i<count-1; i++) arr[i]->fts_link = arr[i+1]; arr[count-1]->fts_link = NULL; free(arr);
		}
	}
	return head;
}
static void push_children(struct _fts *ftsp, FTSENT *parent) {
	FTSENT *children, *c, *arr[4096]; int n=0, i;
	children = read_dir_children(ftsp, parent); if (!children) return;
	for (c=children; c && n<4096; c=c->fts_link) arr[n++]=c;
	for (i=n-1; i>=0; i--) push(ftsp, arr[i], ST_NEW);
}
FTS *fts_open(char * const *argv, int options, int (*compar)(const FTSENT **, const FTSENT **)) {
	struct _fts *ftsp; int i;
	if (!argv || !*argv) { errno = EINVAL; return NULL; }
	ftsp = calloc(1, sizeof(*ftsp)); if (!ftsp) return NULL;
	ftsp->options = options; ftsp->compar = compar; ftsp->started = 0;
	for (i=0; argv[i]; i++); ftsp->npaths = i;
	ftsp->paths = malloc(i*sizeof(char*)); if (!ftsp->paths) { free(ftsp); return NULL; }
	for (i=0; i<ftsp->npaths; i++) ftsp->paths[i] = argv[i];
	return (FTS *)ftsp;
}
FTSENT *fts_read(FTS *ftsp_untyped) {
	struct _fts *ftsp = (struct _fts *)ftsp_untyped;
	struct stack_entry *se; FTSENT *e;
	int physical, follow;
	if (!ftsp) return NULL;
	physical = !(ftsp->options & FTS_LOGICAL);
	follow = (ftsp->options & (FTS_COMFOLLOW | FTS_LOGICAL));
	if (!ftsp->started) {
		int i; FTSENT *head=NULL, *tail=NULL;
		ftsp->started = 1;
		for (i=0; i<ftsp->npaths; i++) {
			char *p = ftsp->paths[i]; e = make_entry(p, p, 0); if (!e) continue;
			if (physical && !follow) {
				if (lstat(p, &e->st_stat) == -1) { e->fts_errno = errno; e->fts_info = FTS_NS; }
				else if (S_ISDIR(e->st_stat.st_mode)) e->fts_info = FTS_D;
				else if (S_ISLNK(e->st_stat.st_mode)) e->fts_info = FTS_SL;
				else e->fts_info = FTS_F;
			} else {
				if (stat(p, &e->st_stat) == -1) { if (lstat(p, &e->st_stat) == 0) e->fts_info = FTS_SLNONE; else { e->fts_errno = errno; e->fts_info = FTS_NS; } }
				else if (S_ISDIR(e->st_stat.st_mode)) e->fts_info = FTS_D;
				else if (S_ISLNK(e->st_stat.st_mode)) e->fts_info = FTS_SL;
				else e->fts_info = FTS_F;
			}
			{ char *bn = strrchr(p, '/'); if (bn) { free(e->fts_name); e->fts_name = strdup(bn+1); e->fts_namelen = strlen(bn+1); } }
			if (!head) { head = e; tail = e; } else { tail->fts_link = e; tail = e; }
		}
		if (ftsp->compar && head) {
			int j, count=0; FTSENT *p, **arr;
			for (p=head; p; p=p->fts_link) count++;
			arr = malloc(count*sizeof(*arr)); if (arr) {
				j=0; for (p=head; p; p=p->fts_link) arr[j++]=p;
				qsort(arr, count, sizeof(*arr), (int(*)(const void*,const void*))ftsp->compar);
				head = arr[0]; for (j=0; j<count-1; j++) arr[j]->fts_link = arr[j+1]; arr[count-1]->fts_link = NULL; free(arr);
			}
		}
		{ FTSENT *arr[256]; int n=0; for (e=head; e && n<256; e=e->fts_link) arr[n++]=e; for (i=n-1; i>=0; i--) push(ftsp, arr[i], ST_NEW); }
	}
	while ((se = pop(ftsp)) != NULL) {
		e = se->entry;
		if (se->state == ST_NEW) { if (e->fts_info == FTS_D) { push(ftsp, e, ST_PRE); return e; } return e; }
		if (se->state == ST_PRE) {
			if (e->fts_flags & FTS_SKIP) { push(ftsp, e, ST_POST); } else { push(ftsp, e, ST_POST); push_children(ftsp, e); }
			continue;
		}
		if (se->state == ST_POST) { e->fts_info = FTS_DP; return e; }
	}
	errno = 0; return NULL;
}
int fts_set(FTS *ftsp, FTSENT *f, int option) { if (!ftsp || !f) return -1; f->fts_flags |= option; return 0; }
FTSENT *fts_children(FTS *ftsp, int option) { (void)ftsp; (void)option; return NULL; }
int fts_close(FTS *ftsp_untyped) {
	struct _fts *ftsp = (struct _fts *)ftsp_untyped; if (!ftsp) return -1;
	while (ftsp->stack_size > 0) { struct stack_entry *se = pop(ftsp); free_entry(se->entry); }
	free(ftsp->stack); free(ftsp->paths); free(ftsp); return 0;
}
"""


class PaxConan(ConanFile):
    name = "pax"
    version = "20240817"
    description = "POSIX archive interchange tool (paxmirabilis) supporting tar, cpio and pax formats"
    license = "GPL-3.0"
    homepage = "https://launchpad.net/pax"
    url = ""
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # Write portable fts.h and fts.c (OHOS lacks BSD fts API)
        save(self, os.path.join(self.source_folder, "fts.h"), FTS_H)
        save(self, os.path.join(self.source_folder, "fts.c"), FTS_C)

        # Apply patches for Build.sh (add fts.c to SRCS) and tar.c (uid/gid fallback)
        apply_conandata_patches(self)

        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = compilers.get("c")
        if not cc:
            cc = "clang" if str(self.settings.compiler) == "clang" else "gcc"

        build_type_flags = {
            "Debug": "-O0 -g",
            "Release": "-O2 -DNDEBUG",
            "RelWithDebInfo": "-O2 -g -DNDEBUG",
            "MinSizeRel": "-Os -DNDEBUG",
        }
        cflags = (
            f"{build_type_flags.get(str(self.settings.build_type), '-O2 -DNDEBUG')} "
            "-fPIC -Wall -fwrapv"
        )

        self.run(
            f'cd "{self.source_folder}" && CC="{cc}" CFLAGS="{cflags}" sh Build.sh -r',
            env="conanbuild",
        )

    def package(self):
        copy(self, "paxpax", src=self.source_folder, dst=os.path.join(self.package_folder, "bin"))
        copy(self, "pax", src=self.source_folder, dst=os.path.join(self.package_folder, "bin"))
        copy(self, "cpio", src=self.source_folder, dst=os.path.join(self.package_folder, "bin"))
        copy(self, "tar", src=self.source_folder, dst=os.path.join(self.package_folder, "bin"))
        mans_dir = os.path.join(self.source_folder, "mans")
        if os.path.isdir(mans_dir):
            copy(self, "*.1", src=mans_dir, dst=os.path.join(self.package_folder, "share", "man", "man1"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
