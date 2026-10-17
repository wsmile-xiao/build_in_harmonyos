/* ANSI-C code produced by gperf version 3.1 */
/* Command-line: gperf -L ANSI-C -E -D -K key -H ohcount_hash_cppheader -N ohcount_hash_is_cppheader -t cppheaders.gperf  */
/* Computed positions: -k'1,5,$' */

#if !((' ' == 32) && ('!' == 33) && ('"' == 34) && ('#' == 35) \
      && ('%' == 37) && ('&' == 38) && ('\'' == 39) && ('(' == 40) \
      && (')' == 41) && ('*' == 42) && ('+' == 43) && (',' == 44) \
      && ('-' == 45) && ('.' == 46) && ('/' == 47) && ('0' == 48) \
      && ('1' == 49) && ('2' == 50) && ('3' == 51) && ('4' == 52) \
      && ('5' == 53) && ('6' == 54) && ('7' == 55) && ('8' == 56) \
      && ('9' == 57) && (':' == 58) && (';' == 59) && ('<' == 60) \
      && ('=' == 61) && ('>' == 62) && ('?' == 63) && ('A' == 65) \
      && ('B' == 66) && ('C' == 67) && ('D' == 68) && ('E' == 69) \
      && ('F' == 70) && ('G' == 71) && ('H' == 72) && ('I' == 73) \
      && ('J' == 74) && ('K' == 75) && ('L' == 76) && ('M' == 77) \
      && ('N' == 78) && ('O' == 79) && ('P' == 80) && ('Q' == 81) \
      && ('R' == 82) && ('S' == 83) && ('T' == 84) && ('U' == 85) \
      && ('V' == 86) && ('W' == 87) && ('X' == 88) && ('Y' == 89) \
      && ('Z' == 90) && ('[' == 91) && ('\\' == 92) && (']' == 93) \
      && ('^' == 94) && ('_' == 95) && ('a' == 97) && ('b' == 98) \
      && ('c' == 99) && ('d' == 100) && ('e' == 101) && ('f' == 102) \
      && ('g' == 103) && ('h' == 104) && ('i' == 105) && ('j' == 106) \
      && ('k' == 107) && ('l' == 108) && ('m' == 109) && ('n' == 110) \
      && ('o' == 111) && ('p' == 112) && ('q' == 113) && ('r' == 114) \
      && ('s' == 115) && ('t' == 116) && ('u' == 117) && ('v' == 118) \
      && ('w' == 119) && ('x' == 120) && ('y' == 121) && ('z' == 122) \
      && ('{' == 123) && ('|' == 124) && ('}' == 125) && ('~' == 126))
/* The character set is not based on ISO-646.  */
#error "gperf generated tables don't work with this execution character set. Please report a bug to <bug-gperf@gnu.org>."
#endif

#line 1 "cppheaders.gperf"
struct CppHeaderMap { const char *key; int value; };
/* maximum key range = 166, duplicates = 0 */

#ifdef __GNUC__
__inline
#else
#ifdef __cplusplus
inline
#endif
#endif
static unsigned int
ohcount_hash_cppheader (register const char *str, register size_t len)
{
  static unsigned char asso_values[] =
    {
      174, 174, 174, 174, 174, 174, 174, 174, 174, 174,
      174, 174, 174, 174, 174, 174, 174, 174, 174, 174,
      174, 174, 174, 174, 174, 174, 174, 174, 174, 174,
      174, 174, 174, 174, 174, 174, 174, 174, 174, 174,
      174, 174, 174, 174, 174, 174, 174, 174, 174, 174,
      174, 174, 174, 174,   0, 174, 174, 174, 174, 174,
      174, 174, 174, 174, 174, 174, 174, 174, 174, 174,
      174, 174, 174, 174, 174, 174, 174, 174, 174, 174,
      174, 174, 174, 174, 174, 174, 174, 174, 174, 174,
      174, 174, 174, 174, 174,   0, 174,  20, 100,  20,
       25,  10,  95,  90,  70,  15,  55,   0,  45,   0,
       55,  55,  15,  40,  25,   5,   0,  50,  40,  95,
       30,  50, 174, 174, 174, 174, 174, 174, 174, 174,
      174, 174, 174, 174, 174, 174, 174, 174, 174, 174,
      174, 174, 174, 174, 174, 174, 174, 174, 174, 174,
      174, 174, 174, 174, 174, 174, 174, 174, 174, 174,
      174, 174, 174, 174, 174, 174, 174, 174, 174, 174,
      174, 174, 174, 174, 174, 174, 174, 174, 174, 174,
      174, 174, 174, 174, 174, 174, 174, 174, 174, 174,
      174, 174, 174, 174, 174, 174, 174, 174, 174, 174,
      174, 174, 174, 174, 174, 174, 174, 174, 174, 174,
      174, 174, 174, 174, 174, 174, 174, 174, 174, 174,
      174, 174, 174, 174, 174, 174, 174, 174, 174, 174,
      174, 174, 174, 174, 174, 174, 174, 174, 174, 174,
      174, 174, 174, 174, 174, 174, 174, 174, 174, 174,
      174, 174, 174, 174, 174, 174
    };
  register unsigned int hval = len;

  switch (hval)
    {
      default:
        hval += asso_values[(unsigned char)str[4]];
      /*FALLTHROUGH*/
      case 4:
      case 3:
      case 2:
      case 1:
        hval += asso_values[(unsigned char)str[0]];
        break;
    }
  return hval + asso_values[(unsigned char)str[len - 1]];
}

struct CppHeaderMap *
ohcount_hash_is_cppheader (register const char *str, register size_t len)
{
  enum
    {
      TOTAL_KEYWORDS = 89,
      MIN_WORD_LENGTH = 3,
      MAX_WORD_LENGTH = 17,
      MIN_HASH_VALUE = 8,
      MAX_HASH_VALUE = 173
    };

  static struct CppHeaderMap wordlist[] =
    {
#line 51 "cppheaders.gperf"
      {"set", 1},
#line 53 "cppheaders.gperf"
      {"stack", 1},
#line 59 "cppheaders.gperf"
      {"type_traits", 1},
#line 43 "cppheaders.gperf"
      {"map", 1},
#line 87 "cppheaders.gperf"
      {"tr1/tuple", 1},
#line 88 "cppheaders.gperf"
      {"tr1/type_traits", 1},
#line 52 "cppheaders.gperf"
      {"sstream", 1},
#line 35 "cppheaders.gperf"
      {"ios", 1},
#line 58 "cppheaders.gperf"
      {"tuple", 1},
#line 13 "cppheaders.gperf"
      {"ciso646", 1},
#line 70 "cppheaders.gperf"
      {"tr1/cfloat", 1},
#line 77 "cppheaders.gperf"
      {"tr1/cstdint", 1},
#line 38 "cppheaders.gperf"
      {"istream", 1},
#line 12 "cppheaders.gperf"
      {"cinttypes", 1},
#line 85 "cppheaders.gperf"
      {"tr1/random", 1},
#line 72 "cppheaders.gperf"
      {"tr1/climits", 1},
#line 6 "cppheaders.gperf"
      {"cassert", 1},
#line 71 "cppheaders.gperf"
      {"tr1/cinttypes", 1},
#line 81 "cppheaders.gperf"
      {"tr1/ctime", 1},
#line 68 "cppheaders.gperf"
      {"tr1/cctype", 1},
#line 83 "cppheaders.gperf"
      {"tr1/cwctype", 1},
#line 22 "cppheaders.gperf"
      {"cstdint", 1},
#line 54 "cppheaders.gperf"
      {"stdexcept", 1},
#line 27 "cppheaders.gperf"
      {"ctime", 1},
#line 11 "cppheaders.gperf"
      {"cfloat", 1},
#line 14 "cppheaders.gperf"
      {"climits", 1},
#line 37 "cppheaders.gperf"
      {"iostream", 1},
#line 41 "cppheaders.gperf"
      {"list", 1},
#line 30 "cppheaders.gperf"
      {"deque", 1},
#line 8 "cppheaders.gperf"
      {"cctype", 1},
#line 57 "cppheaders.gperf"
      {"system_error", 1},
#line 3 "cppheaders.gperf"
      {"algorithm", 1},
#line 82 "cppheaders.gperf"
      {"tr1/cwchar", 1},
#line 40 "cppheaders.gperf"
      {"limits", 1},
#line 15 "cppheaders.gperf"
      {"clocale", 1},
#line 84 "cppheaders.gperf"
      {"tr1/memory", 1},
#line 74 "cppheaders.gperf"
      {"tr1/complex", 1},
#line 67 "cppheaders.gperf"
      {"tr1/ccomplex", 1},
#line 86 "cppheaders.gperf"
      {"tr1/regex", 1},
#line 48 "cppheaders.gperf"
      {"queue", 1},
#line 90 "cppheaders.gperf"
      {"tr1/unordered_set", 1},
#line 39 "cppheaders.gperf"
      {"iterator", 1},
#line 69 "cppheaders.gperf"
      {"tr1/cfenv", 1},
#line 28 "cppheaders.gperf"
      {"cwchar", 1},
#line 47 "cppheaders.gperf"
      {"ostream", 1},
#line 7 "cppheaders.gperf"
      {"ccomplex", 1},
#line 76 "cppheaders.gperf"
      {"tr1/cstdbool", 1},
#line 60 "cppheaders.gperf"
      {"typeinfo", 1},
#line 66 "cppheaders.gperf"
      {"tr1/array", 1},
#line 44 "cppheaders.gperf"
      {"memory", 1},
#line 89 "cppheaders.gperf"
      {"tr1/unordered_map", 1},
#line 78 "cppheaders.gperf"
      {"tr1/cstdio", 1},
#line 49 "cppheaders.gperf"
      {"random", 1},
#line 29 "cppheaders.gperf"
      {"cwctype", 1},
#line 62 "cppheaders.gperf"
      {"unordered_set", 1},
#line 31 "cppheaders.gperf"
      {"exception", 1},
#line 50 "cppheaders.gperf"
      {"regex", 1},
#line 34 "cppheaders.gperf"
      {"iomanip", 1},
#line 23 "cppheaders.gperf"
      {"cstdio", 1},
#line 17 "cppheaders.gperf"
      {"csetjmp", 1},
#line 73 "cppheaders.gperf"
      {"tr1/cmath", 1},
#line 80 "cppheaders.gperf"
      {"tr1/ctgmath", 1},
#line 61 "cppheaders.gperf"
      {"unordered_map", 1},
#line 10 "cppheaders.gperf"
      {"cfenv", 1},
#line 42 "cppheaders.gperf"
      {"locale", 1},
#line 46 "cppheaders.gperf"
      {"numeric", 1},
#line 91 "cppheaders.gperf"
      {"tr1/utility", 1},
#line 32 "cppheaders.gperf"
      {"fstream", 1},
#line 5 "cppheaders.gperf"
      {"bitset", 1},
#line 26 "cppheaders.gperf"
      {"ctgmath", 1},
#line 75 "cppheaders.gperf"
      {"tr1/cstdarg", 1},
#line 63 "cppheaders.gperf"
      {"utility", 1},
#line 64 "cppheaders.gperf"
      {"valarray", 1},
#line 4 "cppheaders.gperf"
      {"array", 1},
#line 65 "cppheaders.gperf"
      {"vector", 1},
#line 18 "cppheaders.gperf"
      {"csignal", 1},
#line 55 "cppheaders.gperf"
      {"streambuf", 1},
#line 79 "cppheaders.gperf"
      {"tr1/cstdlib", 1},
#line 25 "cppheaders.gperf"
      {"cstring", 1},
#line 9 "cppheaders.gperf"
      {"cerrno", 1},
#line 19 "cppheaders.gperf"
      {"cstdarg", 1},
#line 36 "cppheaders.gperf"
      {"iosfwd", 1},
#line 21 "cppheaders.gperf"
      {"cstddef", 1},
#line 33 "cppheaders.gperf"
      {"functional", 1},
#line 45 "cppheaders.gperf"
      {"new", 1},
#line 56 "cppheaders.gperf"
      {"string", 1},
#line 16 "cppheaders.gperf"
      {"cmath", 1},
#line 24 "cppheaders.gperf"
      {"cstdlib", 1},
#line 20 "cppheaders.gperf"
      {"cstdbool", 1}
    };

  static signed char lookup[] =
    {
      -1, -1, -1, -1, -1, -1, -1, -1,  0, -1,  1, -1, -1, -1,
      -1, -1,  2, -1,  3,  4,  5, -1,  6,  7, -1,  8, -1,  9,
      -1, -1, 10, 11, 12, -1, 13, 14, 15, 16, 17, 18, 19, 20,
      21, -1, 22, 23, 24, 25, 26, 27, 28, 29, 30, -1, 31, 32,
      33, 34, -1, -1, 35, 36, 37, -1, 38, 39, -1, 40, 41, 42,
      -1, 43, 44, 45, -1, -1, -1, 46, 47, 48, -1, 49, 50, -1,
      -1, 51, 52, 53, 54, 55, 56, -1, 57, -1, -1, -1, 58, 59,
      -1, 60, -1, 61, -1, 62, -1, 63, 64, 65, -1, -1, -1, 66,
      67, -1, -1, -1, 68, 69, -1, -1, -1, 70, 71, 72, -1, 73,
      74, 75, -1, 76, -1, 77, 78, -1, -1, -1, 79, 80, -1, -1,
      -1, 81, -1, -1, -1, -1, -1, 82, -1, -1, 83, -1, -1, 84,
      -1, -1, 85, -1, -1, -1, -1, -1, -1, -1, -1, 86, -1, -1,
      -1, -1, -1, -1, 87, 88
    };

  if (len <= MAX_WORD_LENGTH && len >= MIN_WORD_LENGTH)
    {
      register unsigned int key = ohcount_hash_cppheader (str, len);

      if (key <= MAX_HASH_VALUE)
        {
          register int index = lookup[key];

          if (index >= 0)
            {
              register const char *s = wordlist[index].key;

              if (*str == *s && !strcmp (str + 1, s + 1))
                return &wordlist[index];
            }
        }
    }
  return 0;
}
