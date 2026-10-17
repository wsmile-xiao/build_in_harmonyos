#!/data/service/hnp/bin/bash
# gift-regen-config-files.sh — deterministic config.status CONFIG_FILES
# generation for gift-0.1.9 on OHOS/HMDFS.
#
# Why this exists: config.status (autoconf 2.53) generates the 39 Makefiles
# with multi-process sed pipelines; on HMDFS those intermittently deadlock,
# get corrupted by write-after-read garbage bytes, or spin forever in the
# `:t/@var@/!b t` substitution loop when a polluted path inserts a `&` into
# a replacement value. This script replicates config.status's CONFIG_FILES
# logic using short-lived single sed processes with file-based handoff only.
# Behaviour is identical on Linux CI (where it simply regenerates the same
# files deterministically).
#
# Requires GNU sed in PATH (see profile buildenv PATH). Run from the gift
# source root, after configure has created config.status.
set -u
SRC=$(pwd)
TMP="$SRC/.regen-tmp"
rm -rf "$TMP"; mkdir -p "$TMP" || exit 1

FILES="Makefile libMRML/Makefile libMRML/cc/Makefile libMRML/include/Makefile libGIFTQuPerl/Makefile libGIFTQuPerl/cc/Makefile libGIFTQuPerl/include/Makefile libGIFTAcPerl/Makefile libGIFTAcPerl/cc/Makefile libGIFTAcPerl/include/Makefile libGIFTAcURL2FTS/Makefile libGIFTAcURL2FTS/cc/Makefile libGIFTAcURL2FTS/include/Makefile libGIFTAcInvertedFile/Makefile libGIFTAcInvertedFile/cc/Makefile libGIFTAcInvertedFile/include/Makefile libGIFTQuInvertedFile/Makefile libGIFTQuInvertedFile/cc/Makefile libGIFTQuInvertedFile/include/Makefile libGIFTAcHierarchy/Makefile libGIFTAcHierarchy/cc/Makefile libGIFTAcHierarchy/include/Makefile libGIFTQuHierarchy/Makefile libGIFTQuHierarchy/cc/Makefile libGIFTQuHierarchy/include/Makefile libGIFTAcDistanceMatrix/Makefile libGIFTAcDistanceMatrix/cc/Makefile libGIFTAcDistanceMatrix/include/Makefile FeatureExtraction/Makefile libSquirePPM/Makefile scripts/Makefile scripts/emacs-lisp/Makefile scripts/perl/Makefile dtd/Makefile Doc/Makefile Doc/Doxyfile GIFTServer/Makefile GIFTServer/gift-mrml-messages/Makefile GIFTServer/gift-config/Makefile"

INSTALLV="./install-sh -c"

# ---- 1. static substitution block from config.status (between heredoc markers)
awk '/subs\.sed <<\\CEOF/{f=1;next} f&&/^CEOF$/{exit} f' config.status > "$TMP/static.sed"
if [ ! -s "$TMP/static.sed" ]; then echo "FATAL: static sed block extraction failed"; exit 1; fi
echo "static.sed lines: $(wc -l < "$TMP/static.sed")"

# ---- 2. regenerate each CONFIG_FILE
fail=0
for f in $FILES; do
  d=$(dirname "$f")
  if [ "$d" = "." ]; then
    dots=""; top="."; ac_srcdir="."
  else
    dots=$(echo "$d" | awk -F/ '{for(i=1;i<=NF;i++) printf "../"}')
    top="${dots%/}"; ac_srcdir="${dots}."
  fi
  cfg_input="Generated automatically from $(basename "$f").in by configure."
  {
    echo "s,@configure_input@,$cfg_input,;t t"
    echo "s,@srcdir@,$ac_srcdir,;t t"
    echo "s,@top_srcdir@,$top,;t t"
    echo "s,@INSTALL@,$dots$INSTALLV,;t t"
    cat "$TMP/static.sed"
  } | sed 's/,@/@@/; s/@,/@@/; s/,;t t$/@;t t/; /@;t t$/s/[\\&,]/\\&/g;
   s/@@/,@/; s/@@/@,/; s/@;t t$/,;t t/' | sed '1i :t\n/@[a-zA-Z_][a-zA-Z_0-9]*@/!b' > "$TMP/subs.sed"

  # VPATH filter (verbatim from config.status), input file -> $TMP/vin (no pipes)
  sed "/^[ 	]*VPATH[ 	]*=/{
s/:*\$(srcdir):*/:/;
s/:*\${srcdir}:*/:/;
s/:*@srcdir@:*/:/;
s/^\([^=]*=[ 	]*\):*/\1/;
s/:*\$(srcdir):*/:/;
s/:*\${srcdir}:*/:/;
s/:*@srcdir@:*/:/;
s/^\([^=]*=[ 	]*\):*/\1/;
s/:*\$//;
s/^[^=]*=[ 	]*\$//;
}" "$f.in" > "$TMP/vin" || { echo "FAIL(vpath) $f"; fail=1; continue; }

  sed -f "$TMP/subs.sed" "$TMP/vin" > "$TMP/out" || { echo "FAIL(subst) $f"; fail=1; continue; }
  # upstream install-data-hook hardcodes $(includedir) without $(DESTDIR);
  # patch it so conan's DESTDIR-staged install works
  sed -i 's|\$(INSTALL_DATA) \$(srcdir)/gift-config.h \$(includedir)/|$(INSTALL_DATA) $(srcdir)/gift-config.h $(DESTDIR)$(includedir)/|' "$TMP/out"
  cp "$TMP/out" "$f" || { echo "FAIL(cp) $f"; fail=1; continue; }
  echo "created $f"
done

rm -rf "$TMP"
# ---- 3. depfiles (CONFIG_COMMANDS): config.status's depfiles command
# normally creates empty .deps/xxx.Plo placeholder files (the generated
# Makefiles reference them with a plain `include`, which is fatal when
# missing); replicate that here.
for f in $FILES; do
  d=$(dirname "$f"); mkdir -p "$d/.deps"
  grep -o '^include $(DEPDIR)/[A-Za-z0-9_.-]*' "$f" 2>/dev/null | sed 's|.*/||' | while read -r p; do
    [ -f "$d/.deps/$p" ] || echo '# dummy' > "$d/.deps/$p"
  done
done

echo "----"
[ $fail -eq 0 ] && echo "ALL FILES REGENERATED OK" || echo "SOME FILES FAILED"
exit $fail
