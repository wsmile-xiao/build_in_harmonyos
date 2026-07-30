# VCFtools 0.1.17 adaptation notes

## Scope

- Upstream release: `v0.1.17`
- Build system: Autotools
- Outputs: the compiled `vcftools` binary, 24 Perl command-line scripts, three Perl modules, and a man page
- Direct link dependency: `zlib/1.3.1`
- Runtime tool dependency: `htslib/1.24-r0` for `bgzip` and `tabix`

## Source and Homebrew alignment

The source URL and SHA256 match Homebrew's `vcftools` formula. Homebrew also
depends on HTSlib because several installed Perl tools execute `bgzip` or
`tabix`; the same runtime relationship is declared here. On Linux, Homebrew's
additional `zlib-ng-compat` dependency supplies the zlib ABI. This recipe uses
the repository's system-safe static `zlib/1.3.1` package instead.

## Upstream tests

The `0.1.17` release tarball contains the example fixtures but omits the
official `src/perl/test.t` file found in the matching Git tag. The recipe
downloads that exact file from the official repository and verifies SHA256
`509a72d46ddb62c1882952ceb82f6bcd3fc2e109096e3458a4673cbdbc2d29d7`.

The suite declares 75 assertions. Two compatibility corrections are applied
before execution without removing or weakening assertions:

1. `Test::Most` is replaced with core `Test::More`; the suite only uses APIs
   provided by `Test::More`.
2. `$path/../examples` is corrected to `$path/../../examples` because `test.t`
   is under `src/perl` while the fixtures are in the repository root.

The suite exercises validation, parsing, statistics, comparison, merge,
intersection, query, shuffle, concatenation, annotation, allele counts,
indel statistics, consensus, contrast, ploidy handling, and Perl APIs.

## Consumer tests

`test_package/test.sh` adds three package-level scenarios:

1. Check `vcftools --version` reports `0.1.17`.
2. Calculate allele frequencies for a two-sample VCF and assert `A:0.25` and
   `G:0.75`.
3. Validate the same VCF with the installed `vcf-validator` Perl tool, which
   also verifies the packaged Perl modules and `PERL5LIB` environment.

## Validation status

- Source archive SHA256: verified on Windows.
- Conan recipe syntax and repository static gates: run locally where possible.
- OHOS aarch64 `conan create`: passed locally, including package creation and
  `test_package` execution.
- Upstream Perl suite: 75/75 assertions passed.
- Consumer package validation: 3/3 scenarios passed (version, allele
  frequency, and `vcf-validator`/`PERL5LIB` checks).
