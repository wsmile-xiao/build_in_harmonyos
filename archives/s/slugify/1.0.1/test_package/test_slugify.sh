#!/usr/bin/env bash
# test_slugify.sh - functional cases for the packaged slugify, one per usage
# example of the upstream README (slugify 1.0.1 ships no automated tests).
#
# Each case creates real files in a scratch directory, runs the packaged
# script through the interpreter running this driver (bash/5.3) and checks
# the printed report, the resulting directory entries and the file contents.
# Two README lines differ from what the 1.0.1 code prints; the cases follow
# the code (see MANIFEST.yml).
#
# Usage: bash test_slugify.sh <package>/bin/slugify

# No -e: every case has to run and report; failures are counted and the
# final exit status reflects them.
set -uo pipefail
export LC_ALL=C

SLUGIFY=${1:?usage: bash test_slugify.sh <package>/bin/slugify}
ROOT=${SLUGIFY_TEST_ROOT:-$PWD}/slugify-readme.$$
mkdir -p "$ROOT" || exit 1
trap 'rm -rf "$ROOT"' EXIT

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

begin "usage help without arguments"
slug
want_rc 0
want_out "usage: slugify [-acdhintuv] source_file ...
   -a: remove spaces immediately adjacent to dashes
   -c: consolidate consecutive spaces into single space
   -d: replace spaces with dashes (instead of default underscores)
   -h: help
   -i: ignore case
   -n: dry run
   -t: treat existing dashes as spaces
   -u: treat existing underscores as spaces (useful with -a, -c, or -d)
   -v: verbose"
end

begin "escaped or quoted filename keeps both spaces"
mk "My  file.txt"
slug -v My\ \ file.txt
want_out "rename: My  file.txt -> my__file.txt"
want_ls "my__file.txt"
want_cat my__file.txt "My  file.txt"
end

begin "glob argument renames one file and ignores the other"
mk "My file.txt" my_web_friendly_filename.txt
slug -v *.txt
want_out "rename: My file.txt -> my_file.txt
ignore: my_web_friendly_filename.txt"
want_ls "my_file.txt
my_web_friendly_filename.txt"
want_cat my_file.txt "My file.txt"
end

begin "several arguments"
mk "My first file.txt" "My second file.txt"
slug -v "My first file.txt" "My second file.txt"
want_out "rename: My first file.txt -> my_first_file.txt
rename: My second file.txt -> my_second_file.txt"
want_ls "my_first_file.txt
my_second_file.txt"
want_cat my_second_file.txt "My second file.txt"
end

begin "directory"
mkdir "My Directory"
printf inner > "My Directory/Inner File.txt"
slug -v "My Directory"
want_out "rename: My Directory -> my_directory"
want_ls "my_directory/"
want_cat "my_directory/Inner File.txt" inner
end

begin "-c consolidates consecutive spaces"
mk "My    consolidated    file.txt"
slug -vc "My    consolidated    file.txt"
want_out "rename: My    consolidated    file.txt -> my_consolidated_file.txt"
want_ls "my_consolidated_file.txt"
end

begin "-d replaces spaces with dashes"
mk "My dashed file.txt"
slug -vd "My dashed file.txt"
want_out "rename: My dashed file.txt -> my-dashed-file.txt"
want_ls "my-dashed-file.txt"
end

begin "-d replaces each space with a dash"
mk "My  dashed  file.txt"
slug -vd "My  dashed  file.txt"
want_out "rename: My  dashed  file.txt -> my--dashed--file.txt"
want_ls "my--dashed--file.txt"
end

begin "-dc gives a single dash between words"
mk "My  dashed  file.txt"
slug -vdc "My  dashed  file.txt"
want_out "rename: My  dashed  file.txt -> my-dashed-file.txt"
want_ls "my-dashed-file.txt"
end

begin "-i keeps the case"
mk "UPPER CASE FILE.txt"
slug -vi "UPPER CASE FILE.txt"
want_out "rename: UPPER CASE FILE.txt -> UPPER_CASE_FILE.txt"
want_ls "UPPER_CASE_FILE.txt"
end

# README also lists "ignore: web_friendly_filename.txt" here, but 1.0.1 only
# prints ignore lines with -v.
begin "-n dry run leaves the directory untouched"
mk "My file.txt" web_friendly_filename.txt
slug -n *
want_out "--- Begin dry run mode.
rename: My file.txt -> my_file.txt
--- End dry run mode."
want_ls "My file.txt
web_friendly_filename.txt"
end

begin "-n reports a file that does not exist"
slug -n "Ghost File.txt"
want_out "--- Begin dry run mode.
not found: Ghost File.txt
rename: Ghost File.txt -> ghost_file.txt
--- End dry run mode."
want_ls ""
end

begin "dash surrounded by underscores without -a"
mk "The Beatles - Yellow Submarine.mp3"
slug -v "The Beatles - Yellow Submarine.mp3"
want_out "rename: The Beatles - Yellow Submarine.mp3 -> the_beatles_-_yellow_submarine.mp3"
want_ls "the_beatles_-_yellow_submarine.mp3"
end

begin "-a removes spaces adjacent to the dash"
mk "The Beatles - Yellow Submarine.mp3"
slug -va "The Beatles - Yellow Submarine.mp3"
want_out "rename: The Beatles - Yellow Submarine.mp3 -> the_beatles-yellow_submarine.mp3"
want_ls "the_beatles-yellow_submarine.mp3"
end

begin "-a removes only the immediately adjacent space"
mk "The Beatles   -   Yellow Submarine.mp3"
slug -va "The Beatles   -   Yellow Submarine.mp3"
want_out "rename: The Beatles   -   Yellow Submarine.mp3 -> the_beatles__-__yellow_submarine.mp3"
want_ls "the_beatles__-__yellow_submarine.mp3"
end

# README prints the source with single spaces here; 1.0.1 echoes it verbatim.
begin "-ac consolidates, then removes the adjacent spaces"
mk "The Beatles   -   Yellow Submarine.mp3"
slug -vac "The Beatles   -   Yellow Submarine.mp3"
want_out "rename: The Beatles   -   Yellow Submarine.mp3 -> the_beatles-yellow_submarine.mp3"
want_ls "the_beatles-yellow_submarine.mp3"
end

begin "-ud converts underscores to dashes"
mk "Spaces Dashes-And_Underscores.txt"
slug -vud "Spaces Dashes-And_Underscores.txt"
want_out "rename: Spaces Dashes-And_Underscores.txt -> spaces-dashes-and-underscores.txt"
want_ls "spaces-dashes-and-underscores.txt"
end

begin "-t converts dashes to underscores"
mk "Spaces Dashes-And_Underscores.txt"
slug -vt "Spaces Dashes-And_Underscores.txt"
want_out "rename: Spaces Dashes-And_Underscores.txt -> spaces_dashes_and_underscores.txt"
want_ls "spaces_dashes_and_underscores.txt"
want_cat spaces_dashes_and_underscores.txt "Spaces Dashes-And_Underscores.txt"
end

echo "README usage cases: $pass/$n passed"
[ $fail -eq 0 ]
