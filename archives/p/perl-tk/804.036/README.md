# perl-tk 804.036

Perl Tk GUI toolkit module (CPAN distribution: Tk-804.036).

## Build Information
- Build system: Perl MakeMaker (Makefile.PL)
- Build date: 2026-06-04
- Platform: aarch64-linux (OpenHarmony)
- Perl version: 5.42.0

## Build Steps
1. `perl Makefile.PL X11LIB=~/usr/local/lib X11INC=~/usr/local/include`
2. `make`
3. `make install DESTDIR=$TEST_PREFIX`

## Known Issues
- llvm-ar requires `rcs` operation flags in PNG/zlib/Makefile (patch applied)
- make test requires X11 display server (skipped for headless builds)
- Perl module needs PERL5LIB set to find installed module path

## Dependencies
- perl 5.42.0
- libX11 6.4.0
- libXau 6.0.0
- xorgproto 2024.1
- libXext 6.4.0
