
#line 1 "lisp.rl"
// lisp.rl written by Mitchell Foral. mitchell<att>caladbolg<dott>net.

/************************* Required for every parser *************************/
#ifndef OHCOUNT_LISP_PARSER_H
#define OHCOUNT_LISP_PARSER_H

#include "../parser_macros.h"

// the name of the language
const char *LISP_LANG = LANG_LISP;

// the languages entities
const char *lisp_entities[] = {
  "space", "comment", "string", "any"
};

// constants associated with the entities
enum {
  LISP_SPACE = 0, LISP_COMMENT, LISP_STRING, LISP_ANY
};

/*****************************************************************************/


#line 28 "lisp.h"
static const char _lisp_actions[] = {
	0, 1, 0, 1, 1, 1, 6, 1, 
	7, 1, 9, 1, 10, 1, 11, 1, 
	12, 1, 15, 1, 18, 1, 19, 1, 
	20, 1, 21, 1, 22, 1, 23, 1, 
	24, 1, 25, 2, 0, 15, 2, 1, 
	8, 2, 1, 14, 2, 3, 2, 2, 
	5, 2, 2, 7, 16, 2, 8, 17, 
	2, 13, 8, 3, 3, 2, 1, 3, 
	4, 0, 15, 3, 5, 2, 0, 3, 
	5, 2, 15
};

static const char _lisp_cond_offsets[] = {
	0, 0, 0, 1, 2, 2, 2, 2, 
	3, 4, 5, 6, 6, 6, 6, 6, 
	6, 7, 7, 7, 7, 7
};

static const char _lisp_cond_lengths[] = {
	0, 0, 1, 1, 0, 0, 0, 1, 
	1, 1, 1, 0, 0, 0, 0, 0, 
	1, 0, 0, 0, 0, 0
};

static const short _lisp_cond_keys[] = {
	13, 13, 13, 13, 13, 13, 13, 13, 
	13, 13, 13, 13, 13, 13, 0
};

static const char _lisp_cond_spaces[] = {
	0, 0, 0, 0, 0, 0, 0, 0
};

static const char _lisp_key_offsets[] = {
	0, 0, 1, 13, 25, 28, 29, 30, 
	41, 52, 63, 74, 75, 76, 80, 83, 
	86, 98, 100, 101, 102, 105
};

static const short _lisp_trans_keys[] = {
	34, 9, 10, 12, 32, 34, 92, 269, 
	525, 0, 11, 14, 255, 9, 10, 12, 
	32, 34, 92, 269, 525, 0, 11, 14, 
	255, 10, 12, 13, 10, 34, 9, 10, 
	12, 32, 34, 269, 525, 0, 11, 14, 
	255, 9, 10, 12, 32, 34, 269, 525, 
	0, 11, 14, 255, 9, 10, 12, 32, 
	34, 269, 525, 0, 11, 14, 255, 9, 
	10, 12, 32, 34, 269, 525, 0, 11, 
	14, 255, 10, 10, 32, 59, 9, 13, 
	32, 9, 13, 10, 12, 13, 9, 10, 
	12, 32, 34, 59, 269, 525, 0, 8, 
	14, 255, 9, 32, 34, 34, 10, 12, 
	13, 10, 0
};

static const char _lisp_single_lengths[] = {
	0, 1, 8, 8, 1, 1, 1, 7, 
	7, 7, 7, 1, 1, 2, 1, 1, 
	8, 2, 1, 1, 1, 1
};

static const char _lisp_range_lengths[] = {
	0, 0, 2, 2, 1, 0, 0, 2, 
	2, 2, 2, 0, 0, 1, 1, 1, 
	2, 0, 0, 0, 1, 0
};

static const char _lisp_index_offsets[] = {
	0, 0, 2, 13, 24, 27, 29, 31, 
	41, 51, 61, 71, 73, 75, 79, 82, 
	85, 96, 99, 101, 103, 106
};

static const char _lisp_indicies[] = {
	2, 1, 3, 4, 4, 3, 5, 6, 
	7, 4, 1, 1, 0, 9, 10, 10, 
	9, 11, 12, 13, 10, 8, 8, 0, 
	0, 0, 1, 4, 0, 15, 14, 16, 
	17, 17, 16, 18, 19, 17, 15, 15, 
	0, 21, 22, 22, 21, 23, 24, 22, 
	20, 20, 0, 16, 17, 17, 16, 25, 
	19, 17, 15, 15, 0, 16, 17, 17, 
	16, 26, 19, 17, 15, 15, 0, 17, 
	0, 27, 28, 30, 31, 30, 29, 30, 
	30, 32, 33, 33, 31, 35, 27, 27, 
	35, 36, 37, 38, 39, 34, 34, 28, 
	35, 35, 40, 43, 42, 45, 44, 44, 
	44, 46, 27, 47, 0
};

static const char _lisp_trans_targs[] = {
	16, 2, 16, 2, 3, 16, 4, 5, 
	2, 2, 3, 16, 4, 5, 16, 7, 
	7, 8, 9, 11, 7, 7, 8, 9, 
	11, 10, 19, 16, 0, 13, 14, 15, 
	13, 13, 16, 17, 18, 20, 12, 21, 
	16, 16, 1, 6, 16, 16, 20, 16
};

static const char _lisp_trans_actions[] = {
	27, 1, 35, 0, 0, 17, 0, 0, 
	67, 47, 47, 71, 47, 47, 63, 3, 
	0, 0, 3, 0, 59, 44, 44, 59, 
	44, 3, 3, 50, 0, 29, 9, 11, 
	31, 33, 53, 5, 56, 38, 7, 7, 
	19, 25, 0, 0, 21, 41, 0, 23
};

static const char _lisp_to_state_actions[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 13, 0, 0, 
	13, 0, 0, 0, 0, 0
};

static const char _lisp_from_state_actions[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 15, 0, 0, 
	15, 0, 0, 0, 0, 0
};

static const char _lisp_eof_trans[] = {
	0, 1, 1, 1, 1, 1, 1, 1, 
	1, 1, 1, 1, 0, 0, 33, 34, 
	0, 41, 42, 45, 45, 48
};

static const int lisp_start = 13;
static const int lisp_first_final = 13;
static const int lisp_error = 0;

static const int lisp_en_lisp_line = 16;
static const int lisp_en_lisp_entity = 13;


#line 100 "lisp.rl"


/* Parses a string buffer with Lisp code.
 *
 * @param *buffer The string to parse.
 * @param length The length of the string to parse.
 * @param count Integer flag specifying whether or not to count lines. If yes,
 *   uses the Ragel machine optimized for counting. Otherwise uses the Ragel
 *   machine optimized for returning entity positions.
 * @param *callback Callback function. If count is set, callback is called for
 *   every line of code, comment, or blank with 'lcode', 'lcomment', and
 *   'lblank' respectively. Otherwise callback is called for each entity found.
 */
void parse_lisp(char *buffer, int length, int count,
                void (*callback) (const char *lang, const char *entity, int s,
                                  int e, void *udata),
                void *userdata
  ) {
  init

  
#line 187 "lisp.h"
	{
	cs = lisp_start;
	ts = 0;
	te = 0;
	act = 0;
	}

#line 121 "lisp.rl"
  cs = (count) ? lisp_en_lisp_line : lisp_en_lisp_entity;
  
#line 198 "lisp.h"
	{
	int _klen;
	unsigned int _trans;
	short _widec;
	const char *_acts;
	unsigned int _nacts;
	const short *_keys;

	if ( p == pe )
		goto _test_eof;
	if ( cs == 0 )
		goto _out;
_resume:
	_acts = _lisp_actions + _lisp_from_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 12:
#line 1 "NONE"
	{ts = p;}
	break;
#line 220 "lisp.h"
		}
	}

	_widec = (*p);
	_klen = _lisp_cond_lengths[cs];
	_keys = _lisp_cond_keys + (_lisp_cond_offsets[cs]*2);
	if ( _klen > 0 ) {
		const short *_lower = _keys;
		const short *_mid;
		const short *_upper = _keys + (_klen<<1) - 2;
		while (1) {
			if ( _upper < _lower )
				break;

			_mid = _lower + (((_upper-_lower) >> 1) & ~1);
			if ( _widec < _mid[0] )
				_upper = _mid - 2;
			else if ( _widec > _mid[1] )
				_lower = _mid + 2;
			else {
				switch ( _lisp_cond_spaces[_lisp_cond_offsets[cs] + ((_mid - _keys)>>1)] ) {
	case 0: {
		_widec = (short)(256 + ((*p) - 0));
		if ( 
#line 9 "common.rl"
 p+1 < pe && *(p+1) != '\n'  ) _widec += 256;
		break;
	}
				}
				break;
			}
		}
	}

	_keys = _lisp_trans_keys + _lisp_key_offsets[cs];
	_trans = _lisp_index_offsets[cs];

	_klen = _lisp_single_lengths[cs];
	if ( _klen > 0 ) {
		const short *_lower = _keys;
		const short *_mid;
		const short *_upper = _keys + _klen - 1;
		while (1) {
			if ( _upper < _lower )
				break;

			_mid = _lower + ((_upper-_lower) >> 1);
			if ( _widec < *_mid )
				_upper = _mid - 1;
			else if ( _widec > *_mid )
				_lower = _mid + 1;
			else {
				_trans += (unsigned int)(_mid - _keys);
				goto _match;
			}
		}
		_keys += _klen;
		_trans += _klen;
	}

	_klen = _lisp_range_lengths[cs];
	if ( _klen > 0 ) {
		const short *_lower = _keys;
		const short *_mid;
		const short *_upper = _keys + (_klen<<1) - 2;
		while (1) {
			if ( _upper < _lower )
				break;

			_mid = _lower + (((_upper-_lower) >> 1) & ~1);
			if ( _widec < _mid[0] )
				_upper = _mid - 2;
			else if ( _widec > _mid[1] )
				_lower = _mid + 2;
			else {
				_trans += (unsigned int)((_mid - _keys)>>1);
				goto _match;
			}
		}
		_trans += _klen;
	}

_match:
	_trans = _lisp_indicies[_trans];
_eof_trans:
	cs = _lisp_trans_targs[_trans];

	if ( _lisp_trans_actions[_trans] == 0 )
		goto _again;

	_acts = _lisp_actions + _lisp_trans_actions[_trans];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 )
	{
		switch ( *_acts++ )
		{
	case 0:
#line 53 "common.rl"
	{
  if (!line_contains_code && !line_start) line_start = ts;
  line_contains_code = 1;
}
	break;
	case 1:
#line 58 "common.rl"
	{
  if (!line_contains_code) {
    whole_line_comment = 1;
    if (!line_start) line_start = ts;
  }
}
	break;
	case 2:
#line 31 "lisp.rl"
	{
    switch(entity) {
    case LISP_SPACE:
      ls
      break;
    case LISP_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(LISP_LANG)
      break;
    case NEWLINE:
      std_newline(LISP_LANG)
    }
  }
	break;
	case 3:
#line 48 "lisp.rl"
	{ entity = INTERNAL_NL; }
	break;
	case 4:
#line 60 "lisp.rl"
	{p--;}
	break;
	case 5:
#line 67 "lisp.rl"
	{ entity = INTERNAL_NL; }
	break;
	case 6:
#line 79 "lisp.rl"
	{ entity = LISP_SPACE; }
	break;
	case 7:
#line 82 "lisp.rl"
	{ entity = NEWLINE;    }
	break;
	case 8:
#line 83 "lisp.rl"
	{ entity = LISP_ANY;   }
	break;
	case 9:
#line 95 "lisp.rl"
	{ entity = LISP_SPACE;   }
	break;
	case 10:
#line 96 "lisp.rl"
	{ entity = LISP_COMMENT; }
	break;
	case 13:
#line 1 "NONE"
	{te = p+1;}
	break;
	case 14:
#line 80 "lisp.rl"
	{te = p+1;}
	break;
	case 15:
#line 81 "lisp.rl"
	{te = p+1;}
	break;
	case 16:
#line 31 "lisp.rl"
	{te = p+1;{
    switch(entity) {
    case LISP_SPACE:
      ls
      break;
    case LISP_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(LISP_LANG)
      break;
    case NEWLINE:
      std_newline(LISP_LANG)
    }
  }}
	break;
	case 17:
#line 31 "lisp.rl"
	{te = p+1;{
    switch(entity) {
    case LISP_SPACE:
      ls
      break;
    case LISP_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(LISP_LANG)
      break;
    case NEWLINE:
      std_newline(LISP_LANG)
    }
  }}
	break;
	case 18:
#line 31 "lisp.rl"
	{te = p;p--;{
    switch(entity) {
    case LISP_SPACE:
      ls
      break;
    case LISP_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(LISP_LANG)
      break;
    case NEWLINE:
      std_newline(LISP_LANG)
    }
  }}
	break;
	case 19:
#line 80 "lisp.rl"
	{te = p;p--;}
	break;
	case 20:
#line 31 "lisp.rl"
	{te = p;p--;{
    switch(entity) {
    case LISP_SPACE:
      ls
      break;
    case LISP_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(LISP_LANG)
      break;
    case NEWLINE:
      std_newline(LISP_LANG)
    }
  }}
	break;
	case 21:
#line 31 "lisp.rl"
	{te = p;p--;{
    switch(entity) {
    case LISP_SPACE:
      ls
      break;
    case LISP_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(LISP_LANG)
      break;
    case NEWLINE:
      std_newline(LISP_LANG)
    }
  }}
	break;
	case 22:
#line 31 "lisp.rl"
	{{p = ((te))-1;}{
    switch(entity) {
    case LISP_SPACE:
      ls
      break;
    case LISP_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(LISP_LANG)
      break;
    case NEWLINE:
      std_newline(LISP_LANG)
    }
  }}
	break;
	case 23:
#line 98 "lisp.rl"
	{te = p+1;}
	break;
	case 24:
#line 88 "lisp.rl"
	{te = p;p--;{
    callback(LISP_LANG, lisp_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 25:
#line 88 "lisp.rl"
	{te = p;p--;{
    callback(LISP_LANG, lisp_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
#line 523 "lisp.h"
		}
	}

_again:
	_acts = _lisp_actions + _lisp_to_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 11:
#line 1 "NONE"
	{ts = 0;}
	break;
#line 536 "lisp.h"
		}
	}

	if ( cs == 0 )
		goto _out;
	if ( ++p != pe )
		goto _resume;
	_test_eof: {}
	if ( p == eof )
	{
	if ( _lisp_eof_trans[cs] > 0 ) {
		_trans = _lisp_eof_trans[cs] - 1;
		goto _eof_trans;
	}
	}

	_out: {}
	}

#line 123 "lisp.rl"

  // if no newline at EOF; callback contents of last line
  if (count) { process_last_line(LISP_LANG) }
}

const char *ELISP_LANG = LANG_EMACSLISP;
const char *ORIG_LISP_LANG = LANG_LISP;
void parse_emacslisp(char *buffer, int length, int count,
                     void (*callback) (const char *lang, const char *entity,
                                       int s, int e, void *udata),
                     void *userdata
  ) {
  LISP_LANG = ELISP_LANG;
  parse_lisp(buffer, length, count, callback, userdata);
  LISP_LANG = ORIG_LISP_LANG;
}

const char *SCHEME_LANG = LANG_SCHEME;
void parse_scheme(char *buffer, int length, int count,
                  void (*callback) (const char *lang, const char *entity, int s,
                                    int e, void *udata),
                  void *userdata
  ) {
  LISP_LANG = SCHEME_LANG;
  parse_lisp(buffer, length, count, callback, userdata);
  LISP_LANG = ORIG_LISP_LANG;
}

const char *CLOJURE_LANG = LANG_CLOJURE;
void parse_clojure(char *buffer, int length, int count,
                   void (*callback) (const char *lang, const char *entity, int s,
                                     int e, void *udata),
                   void *userdata
  ) {
  LISP_LANG = CLOJURE_LANG;
  parse_lisp(buffer, length, count, callback, userdata);
  LISP_LANG = ORIG_LISP_LANG;
}

const char *RACKET_LANG = LANG_RACKET;
void parse_racket(char *buffer, int length, int count,
                   void (*callback) (const char *lang, const char *entity, int s,
                                     int e, void *udata),
                   void *userdata
  ) {
  LISP_LANG = RACKET_LANG;
  parse_lisp(buffer, length, count, callback, userdata);
  LISP_LANG = ORIG_LISP_LANG;
}


#endif
