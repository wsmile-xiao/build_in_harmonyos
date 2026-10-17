# Enca - guess and convert encoding of text files

Enca (Extremely Naive Charset Analyser) consists of two main components:

- **libenca**, an encoding detection library. It currently supports Belarusian,
  Bulgarian, Croatian, Czech, Estonian, Hungarian, Latvian, Lithuanian, Polish,
  Russian, Slovak, Slovene, Ukrainian, Chinese, and some multibyte encodings
  independently on language.
- **enca**, a command line frontend, integrating libenca and several charset
  conversion libraries and tools (GNU recode, UNIX98 iconv, perl Unicode::Map,
  cstocs).

## Homepage

https://github.com/nijel/enca

## License

GPL-2.0-only
