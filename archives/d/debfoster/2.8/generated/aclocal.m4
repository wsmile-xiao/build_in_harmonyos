# aclocal.m4 -- placeholder restored for the Conan build (see below).
#
# Upstream's Makefile.am contains a `dist-hook` that deletes the generated
# autotools helper files from the release tarball:
#
#     dist-hook:
#             rm -f $(distdir)/autom4te.cache
#             rm -f $(distdir)/config.guess*
#             rm -f $(distdir)/config.sub*
#             rm -f $(distdir)/aclocal.m4
#             rm -f $(distdir)/missing
#             rm -f $(distdir)/install-sh
#             rm -f $(distdir)/depcomp
#
# debfoster_2.8.orig.tar.xz was produced by `make dist`, so the tarball still
# ships the generated ./configure and the per-directory Makefile.in, but none
# of the files above.  Debian rebuilds them with dh_autoreconf; this recipe
# cannot, because aclocal would additionally need autoconf-archive's
# ax_cflags_warn_all.m4 (AX_CFLAGS_WARN_ALL is used in configure.ac) and the
# CI worker has no autotools at all.
#
# The automake-generated Makefiles nevertheless declare
#
#     $(ACLOCAL_M4): $(am__aclocal_m4_deps)
#             $(am__cd) $(srcdir) && $(ACLOCAL) $(ACLOCAL_AMFLAGS)
#
# so `make` aborts with
#
#     missing: aclocal-1.16: inaccessible or not found
#     make: *** [Makefile:375: aclocal.m4] Error 127
#
# unless the file exists.  This file therefore only exists to satisfy that
# prerequisite.  It is never read: aclocal.m4 is an input of autoconf alone,
# and the recipe pins every autotools input and product (configure.ac, m4/*.m4,
# Makefile.am/in, configure, config.h.in, config.guess, config.sub, install-sh,
# missing, depcomp, aclocal.m4) to one identical mtime, so no maintainer rule
# ever fires and configure is never regenerated.
