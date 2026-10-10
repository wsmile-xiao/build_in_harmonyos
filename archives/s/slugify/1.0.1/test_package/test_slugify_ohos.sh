#!/usr/bin/env bash
# test_slugify_ohos.sh - HarmonyOS PC specific end-to-end consumer cases.
#
# The consumer finds slugify on the PATH of the conanrun environment without
# relying on the exec bit (HMDFS normalises permissions) and runs it through
# an explicit interpreter, bash/5.3 (the bash running this driver): HarmonyOS
# refuses to exec #! scripts from user storage and has no /usr/bin/env.
#
# HarmonyOS PC user storage (/storage/Users/currentUser, HMDFS) is
# case-insensitive: the lower-case target of a case-only rename
# (README.md -> readme.md) resolves to the source itself, so upstream 1.0.1
# reports "conflict" and never renames. patches/0001-slugify.patch treats such
# a target as an alias of the source and renames through a temporary name.
# HC-1, HC-2, HC-3 and HC-5 expect the same end state on every filesystem:
# case-insensitive storage runs the patched alias path, a case-sensitive
# filesystem the plain rename path (printed below). HC-4 checks that the alias
# handling never swallows a real conflict; on a case-sensitive filesystem it
# also drives the patch's restore branch (hard link / symlink under the
# target name).
#
# Usage: bash test_slugify_ohos.sh <package>/bin/slugify
# SLUGIFY_TEST_ROOT=<dir> runs the cases below <dir> (e.g. HMDFS storage or a
# case-insensitive mount) instead of the current directory.

# No -e: every case has to run and report; failures are counted and the
# final exit status reflects them.
set -uo pipefail
export LC_ALL=C

PKG_SLUGIFY=${1:?usage: bash test_slugify_ohos.sh <package>/bin/slugify}

find_on_path() {
  local d IFS=:
  set -f
  for d in $PATH; do
    if [ -f "${d:-.}/slugify" ]; then set +f; printf '%s\n' "${d:-.}/slugify"; return 0; fi
  done
  set +f
  return 1
}
SLUGIFY=$(find_on_path)
if [ -z "$SLUGIFY" ] || [ ! "$SLUGIFY" -ef "$PKG_SLUGIFY" ]; then
  echo "FAIL: consumer PATH resolves '${SLUGIFY:-<none>}', expected $PKG_SLUGIFY"
  exit 1
fi

ROOT=${SLUGIFY_TEST_ROOT:-$PWD}/slugify-ohos.$$
mkdir -p "$ROOT" || exit 1
trap 'rm -rf "$ROOT"' EXIT

: > "$ROOT/CaseProbe" || exit 1
if [ -e "$ROOT/caseprobe" ]; then case_insensitive=1; else case_insensitive=0; fi
rm -f "$ROOT/CaseProbe"

echo "# slugify     : $SLUGIFY"
echo "# interpreter : $BASH ($BASH_VERSION, $MACHTYPE)"
if [ $case_insensitive -eq 1 ]; then
  echo "# filesystem  : case-insensitive (HMDFS-like) -> patched alias path"
else
  echo "# filesystem  : case-sensitive -> plain rename path"
fi

pass=0 fail=0 n=0 err=0 name=
OUT= RC=0

begin() { n=$((n + 1)); name=$1; err=0; mkdir "$ROOT/c$n" && cd "$ROOT/c$n" || exit 1; }
end() {
  if [ $err -eq 0 ]; then pass=$((pass + 1)); echo "PASS [$n] $name"
  else fail=$((fail + 1)); echo "FAIL [$n] $name"; fi
  cd "$ROOT" || exit 1
}
bad() { echo "    $*"; err=1; }
mk() { local f; for f; do printf '%s' "$f" > "$f"; done; }
slug() { OUT=$("$BASH" "$SLUGIFY" "$@" 2>&1); RC=$?; }
listing() {
  local e
  shopt -s nullglob dotglob
  for e in *; do [ -d "$e" ] && e="$e/"; printf '%s\n' "$e"; done
  shopt -u nullglob dotglob
}
want_rc() { [ "$RC" -eq "$1" ] || bad "exit code $RC, want $1"; }
want_out() { [ "$OUT" == "$1" ] || bad "output:"$'\n'"$OUT"$'\n'"    want:"$'\n'"$1"; }
want_ls() { local got; got=$(listing); [ "$got" == "$1" ] || bad "entries:"$'\n'"$got"$'\n'"    want:"$'\n'"$1"; }
want_cat() { [ "$(cat -- "$1" 2>/dev/null)" == "$2" ] || bad "content of '$1' is not '$2'"; }

begin "HC-1 case-only renames of files"
mk README.md Photo.JPG notes.txt
slug -v README.md Photo.JPG notes.txt
want_rc 0
want_out "rename: README.md -> readme.md
rename: Photo.JPG -> photo.jpg
ignore: notes.txt"
want_ls "notes.txt
photo.jpg
readme.md"
want_cat readme.md README.md
want_cat photo.jpg Photo.JPG
end

begin "HC-2 case-only rename of a directory given with a trailing slash"
mkdir Photos
printf one > Photos/One.txt
printf two > "Photos/Two Words.txt"
slug -v Photos/
want_out "rename: Photos/ -> photos/"
want_ls "photos/"
want_cat photos/One.txt one
want_cat "photos/Two Words.txt" two
end

begin "HC-3 dry run previews a case-only rename and changes nothing"
mk README.md
slug -n README.md
want_out "--- Begin dry run mode.
rename: README.md -> readme.md
--- End dry run mode."
want_ls "README.md"
want_cat README.md README.md
end

begin "HC-4 a real conflict is never swallowed by the alias handling"
mk "My File.txt"
printf other > my_file.txt
slug -v "My File.txt"
want_out "conflict: My File.txt"
want_ls "My File.txt
my_file.txt"
want_cat "My File.txt" "My File.txt"
want_cat my_file.txt other
mkdir links && cd links || exit 1
mk README.md Link.txt
# A second entry under the target name that is the same file: only
# constructible where README.md and readme.md are different entries (and
# hard links exist - HMDFS has none).
if [ $case_insensitive -eq 0 ] && ln README.md readme.md 2>/dev/null &&
   ln -s Link.txt link.txt 2>/dev/null; then
  slug -v README.md Link.txt
  want_out "conflict: README.md
conflict: Link.txt"
  want_ls "Link.txt
README.md
link.txt
readme.md"
  want_cat README.md README.md
  [ -L link.txt ] || bad "link.txt is no longer a symlink"
else
  echo "    (hard link / symlink sub-step needs a case-sensitive filesystem with hard links)"
fi
cd .. || exit 1
end

begin "HC-5 web publishing pipeline consumes the slugified names"
mkdir downloads site
cd downloads || exit 1
mk "Team Photo.JPG" README.md "Q3 Report - Final.PDF"
mkdir "Meeting Notes"
printf agenda > "Meeting Notes/agenda.txt"
slug -ac *
want_rc 0
want_out ""
# Consumer step 1: build the site index from the names actually stored.
{
  echo "<ul>"
  for e in *; do
    [ -d "$e" ] && e="$e/"
    echo "<li><a href=\"$e\">$e</a></li>"
  done
  echo "</ul>"
} > ../site/index.html
cd .. || exit 1
# Consumer step 2: publish - every link must be URL safe and match a stored
# entry exactly (case-sensitive, as a web server resolves URLs).
hrefs=
while IFS= read -r line; do
  [[ $line =~ href=\"([^\"]*)\" ]] || continue
  href=${BASH_REMATCH[1]}
  hrefs+="$href "
  [[ $href =~ ^[a-z0-9._-]+/?$ ]] || bad "link '$href' is not web friendly"
  found=0
  for e in downloads/*; do [ "${e#downloads/}" == "${href%/}" ] && found=1; done
  [ $found -eq 1 ] || bad "link '$href' has no exact entry"
done < site/index.html
[ "$hrefs" == "meeting_notes/ q3_report-final.pdf readme.md team_photo.jpg " ] ||
  bad "published links: $hrefs"
want_cat downloads/readme.md README.md
want_cat downloads/team_photo.jpg "Team Photo.JPG"
want_cat downloads/q3_report-final.pdf "Q3 Report - Final.PDF"
want_cat downloads/meeting_notes/agenda.txt agenda
end

echo "HarmonyOS-specific consumer cases: $pass/$n passed"
[ $fail -eq 0 ]
