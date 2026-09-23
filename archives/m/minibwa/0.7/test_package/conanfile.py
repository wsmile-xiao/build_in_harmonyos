#!/usr/bin/env python3
"""Consumer test recipe for minibwa 0.7.

Runs the upstream README chrM workflow (index + paired-end map) against
the installed package's CLI, then compiles and runs a C API consumer
against the installed libminibwa.a + minibwa.h (mirrors upstream
api-test/ex-one.c, trimmed to the core mapping assertions).
"""

import os
import sys

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.build import cppstd_flag
from conan.tools.env import Environment
from conan.tools.files import save
from conan.tools.layout import basic_layout


class MinibwaTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def generate(self):
        # One-shot consumer source mirroring upstream api-test/ex-one.c:
        # load the packaged index, map the packaged reads, print PAF-like
        # lines. Written at generate time so the test does not depend on
        # files outside the package and the test folder.
        source = r'''
#include <stdlib.h>
#include <stdio.h>
#include <zlib.h>
#include "minibwa.h"
#include "kseq.h"
KSEQ_INIT(gzFile, gzread)

int main(int argc, char *argv[])
{
	mb_opt_t opt;
	mb_opt_init(&opt);
	if (argc < 3) return 1;
	gzFile f = gzopen(argv[2], "r");
	if (!f) return 2;
	kseq_t *ks = kseq_init(f);
	mb_idx_t *idx = mb_idx_load(argv[1], 0);
	if (!idx) return 3;
	long n_records = 0, n_hits = 0;
	while (kseq_read(ks) >= 0) {
		mb_hit_t *hit;
		int32_t i, j, n_hit = 0;
		++n_records;
		hit = mb_map(&opt, idx, ks->seq.l, ks->seq.s, 0, &n_hit, 0, ks->name.s);
		for (j = 0; j < n_hit; ++j) {
			mb_hit_t *h = &hit[j];
			++n_hits;
			printf("%s\t%lu\t%d\t%d\t%c\t", ks->name.s, ks->seq.l, h->qs, h->qe, "+-"[h->rev]);
			printf("%s\t%ld\t%ld\t%ld\t%ld\t%d\t%d\t%d\n", mb_idx_ctg_name(idx, h->tid), (long)mb_idx_ctg_len(idx, h->tid), (long)h->ts, (long)h->te, h->mlen, h->blen, h->mapq);
			for (i = 0; i < h->p->n_cigar; ++i)
				;
			free(h->p);
		}
		free(hit);
	}
	mb_idx_destroy(idx);
	kseq_destroy(ks);
	gzclose(f);
	fprintf(stderr, "RECORDS=%ld HITS=%ld\n", n_records, n_hits);
	return 0;
}
'''
        save(self, os.path.join(self.build_folder, "mbconsumer.c"), source)

    def test(self):
        if not can_run(self):
            self.output.info("minibwa consumer test skipped: target cannot run")
            return

        # The CI Python env may have no bare clang on PATH, so the consumer
        # compiler must come from the Conan conf (same source as the main
        # recipe build), never from a hardcoded toolchain path.
        compilers = self.conf.get(
            "tools.build:compiler_executables",
            default={},
            check_type=dict,
        ) or {}
        cc = compilers.get("c")

        package = self.dependencies["minibwa"].package_folder
        script = os.path.join(self.recipe_folder, "test_minibwa.py")
        # conanrun (VirtualRunEnv) still applies to the run; MINIBWA_TEST_CC
        # is additive on top of it for the consumer compile inside the script.
        run_env = Environment()
        if cc:
            run_env.define("MINIBWA_TEST_CC", cc)
        with run_env.vars(self, scope="run").apply():
            self.run(
                f'"{sys.executable}" "{script}" "{package}" '
                f'"{self.build_folder}"',
                env="conanrun",
            )
