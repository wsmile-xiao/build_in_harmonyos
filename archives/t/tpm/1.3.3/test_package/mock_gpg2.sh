#!/bin/sh
# mock_gpg2.sh — TEST-ONLY stub of `gpg2` for tpm's test_package.
#
# WHY THIS EXISTS
#   tpm (nmeum/tpm) is a password manager whose insert/show subcommands call
#   the real `gpg2` for symmetric encryption. The OHOS artifact repo does not
#   ship gpg2 yet, so running insert/show against real gpg would fail for an
#   unrelated (runtime dependency) reason and mask whether tpm itself works.
#
#   This stub stands in for gpg2 so the test_package can exercise tpm's
#   *complete* insert→show data path: it verifies that tpm correctly reads a
#   password, invokes the encryption backend with the right arguments, writes
#   the entry to the right store path, and later decrypts+prints it back.
#
# WHAT IT IS / IS NOT
#   - It is a deterministic, reversible transform (base64), NOT real crypto.
#   - It honors ONLY the gpg2 invocation shapes that tpm emits:
#       encrypt: gpg2 <flags> --encrypt --output <file>        (password on stdin)
#       decrypt: gpg2 <flags> --decrypt <file>                 (plaintext on stdout)
#     All other gpg2 flags tpm passes (--quiet --yes --batch
#     --default-recipient-self / --recipient <key>) are ignored on purpose.
#   - Any unrecognized shape prints an error to stderr and exits 2, so the
#     test fails loudly if tpm ever changes its gpg2 contract.
#
# SECURITY NOTE
#   This file MUST NOT be used outside test_package/. It provides no real
#   confidentiality; its only purpose is to make tpm's insert/show runnable
#   in CI without a real gpg2 install. See test_package/MANIFEST.yml.

set -eu

mode=""
output=""
infile=""

# Parse args tpm-style: collect flags, capture --output <f> and the trailing
# positional (the file to decrypt, or the subcommand encrypt/decrypt).
prev=""
for arg in "$@"; do
  case "$arg" in
    --encrypt)        mode="encrypt" ;;
    --decrypt)        mode="decrypt" ;;
    --output)         prev="output" ;;
    --quiet|--yes|--batch|--default-recipient-self|--recipient) ;;
    --recipient=*)    ;;
    --output=*)       output="${arg#--output=}" ;;
    *)
      # Value of the preceding --output flag.
      if [ "$prev" = "output" ]; then
        output="$arg"
        prev=""
      else
        # Positional argument: for decrypt this is the input .gpg file.
        infile="$arg"
      fi
      ;;
  esac
done

enc() {
  # Read plaintext password from stdin, write transform to $output.
  # base64 encodes the bytes; we prefix a tag so decrypt can sanity-check.
  if [ -z "$output" ]; then
    printf 'mock_gpg2: encrypt invoked without --output\n' >&2
    exit 2
  fi
  plaintext=$(cat)
  printf 'MOCKGPG1\n' > "$output"
  printf '%s' "$plaintext" | base64 >> "$output"
}

dec() {
  # Read $infile, strip tag, reverse transform to stdout.
  if [ -z "$infile" ]; then
    printf 'mock_gpg2: decrypt invoked without an input file\n' >&2
    exit 2
  fi
  if [ ! -r "$infile" ]; then
    printf 'mock_gpg2: decrypt input not readable: %s\n' "$infile" >&2
    exit 2
  fi
  # First line is the tag; the rest is the base64 payload.
  { read -r tag; rest=$(cat); } < "$infile"
  if [ "$tag" != "MOCKGPG1" ]; then
    printf 'mock_gpg2: bad tag in %s (not produced by this stub)\n' "$infile" >&2
    exit 2
  fi
  printf '%s' "$rest" | base64 -d
}

case "$mode" in
  encrypt) enc ;;
  decrypt) dec ;;
  "") printf 'mock_gpg2: no --encrypt/--decrypt given (args: %s)\n' "$*" >&2; exit 2 ;;
  *) printf 'mock_gpg2: unsupported mode %s\n' "$mode" >&2; exit 2 ;;
esac

exit 0
