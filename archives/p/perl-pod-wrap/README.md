# perl-pod-wrap

Pod::Wrap - Wrap pod paragraphs, leaving verbatim text and code alone.

This is a Pod::Parser subclass that parses perl files, wrapping pod text,
and leaving everything else intact. It uses Text::Wrap to wrap regular
POD paragraphs while preserving verbatim text (indented), POD commands
(=head1, =over, etc.), and Perl code outside POD sections.

## Versions

- 0.01: published (2026-06-25)

## Dependencies

- Perl 5.42.0 (system)
- Pod::Parser 1.67 (installed to ~/usr/local)
- Text::Wrap (Perl core module)

## Environment

```bash
export PERL5LIB="$HOME/usr/local/lib/site_perl/5.42.0:$HOME/usr/local/lib/5.42.0"
```

## Quality Status

- Submit check: 6/6 PASS
- Quality gates: G0-G4 all PASS
- Official tests: 77/77 PASS
- Functional tests: 39/39 PASS
- Ready for production use on HarmonyOS ✅
