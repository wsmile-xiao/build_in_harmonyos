
#line 1 "pascal.rl"
// pascal.rl written by Mitchell Foral. mitchell<att>caladbolg<dott>net

/************************* Required for every parser *************************/
#ifndef OHCOUNT_PASCAL_PARSER_H
#define OHCOUNT_PASCAL_PARSER_H

#include "../parser_macros.h"

// the name of the language
const char *PASCAL_LANG = LANG_PASCAL;

// the languages entities
const char *pascal_entities[] = {
  "space", "comment", "string", "any"
};

// constants associated with the entities
enum {
  PASCAL_SPACE = 0, PASCAL_COMMENT, PASCAL_STRING, PASCAL_ANY
};

/*****************************************************************************/


#line 28 "pascal.h"
static const char _pascal_actions[] = {
	0, 1, 0, 1, 1, 1, 6, 1, 
	7, 1, 8, 1, 9, 1, 10, 1, 
	11, 1, 12, 1, 14, 1, 15, 1, 
	18, 1, 19, 1, 20, 1, 21, 1, 
	22, 1, 24, 1, 25, 1, 26, 1, 
	27, 1, 28, 2, 3, 2, 2, 4, 
	2, 2, 5, 2, 2, 7, 16, 2, 
	8, 17, 2, 10, 23, 2, 13, 8, 
	2, 13, 10, 3, 3, 2, 0, 3, 
	4, 2, 1, 3, 4, 2, 14, 3, 
	5, 2, 0, 3, 5, 2, 15, 3, 
	13, 0, 8, 3, 13, 1, 8
};

static const char _pascal_cond_offsets[] = {
	0, 0, 0, 0, 0, 1, 2, 2, 
	2, 3, 4, 5, 5, 6, 7, 7, 
	7, 7, 7, 7, 7, 7, 7, 8, 
	8, 9, 9, 9, 9, 10
};

static const char _pascal_cond_lengths[] = {
	0, 0, 0, 0, 1, 1, 0, 0, 
	1, 1, 1, 0, 1, 1, 0, 0, 
	0, 0, 0, 0, 0, 0, 1, 0, 
	1, 0, 0, 0, 1, 0
};

static const short _pascal_cond_keys[] = {
	13, 13, 13, 13, 13, 13, 13, 13, 
	13, 13, 13, 13, 13, 13, 13, 13, 
	13, 13, 13, 13, 0
};

static const char _pascal_cond_spaces[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0
};

static const char _pascal_key_offsets[] = {
	0, 0, 1, 3, 4, 16, 28, 31, 
	32, 43, 54, 66, 67, 78, 89, 90, 
	91, 97, 100, 101, 102, 105, 106, 120, 
	122, 134, 135, 136, 139, 150
};

static const short _pascal_trans_keys[] = {
	42, 41, 42, 125, 9, 10, 12, 32, 
	39, 92, 269, 525, 0, 11, 14, 255, 
	9, 10, 12, 32, 39, 92, 269, 525, 
	0, 11, 14, 255, 10, 12, 13, 10, 
	9, 10, 12, 32, 42, 269, 525, 0, 
	11, 14, 255, 9, 10, 12, 32, 42, 
	269, 525, 0, 11, 14, 255, 9, 10, 
	12, 32, 41, 42, 269, 525, 0, 11, 
	14, 255, 10, 9, 10, 12, 32, 125, 
	269, 525, 0, 11, 14, 255, 9, 10, 
	12, 32, 125, 269, 525, 0, 11, 14, 
	255, 10, 10, 32, 40, 47, 123, 9, 
	13, 32, 9, 13, 42, 47, 10, 12, 
	13, 125, 9, 10, 12, 32, 39, 40, 
	47, 123, 269, 525, 0, 8, 14, 255, 
	9, 32, 9, 10, 12, 32, 39, 92, 
	269, 525, 0, 11, 14, 255, 42, 47, 
	10, 12, 13, 9, 10, 12, 32, 125, 
	269, 525, 0, 11, 14, 255, 10, 0
};

static const char _pascal_single_lengths[] = {
	0, 1, 2, 1, 8, 8, 1, 1, 
	7, 7, 8, 1, 7, 7, 1, 1, 
	4, 1, 1, 1, 1, 1, 10, 2, 
	8, 1, 1, 1, 7, 1
};

static const char _pascal_range_lengths[] = {
	0, 0, 0, 0, 2, 2, 1, 0, 
	2, 2, 2, 0, 2, 2, 0, 0, 
	1, 1, 0, 0, 1, 0, 2, 0, 
	2, 0, 0, 1, 2, 0
};

static const char _pascal_index_offsets[] = {
	0, 0, 2, 5, 7, 18, 29, 32, 
	34, 44, 54, 65, 67, 77, 87, 89, 
	91, 97, 100, 102, 104, 107, 109, 122, 
	125, 136, 138, 140, 143, 153
};

static const char _pascal_indicies[] = {
	2, 1, 3, 2, 1, 3, 4, 7, 
	8, 8, 7, 9, 10, 11, 8, 6, 
	6, 5, 13, 14, 14, 13, 15, 16, 
	17, 14, 12, 12, 5, 5, 5, 6, 
	8, 5, 19, 20, 20, 19, 21, 22, 
	20, 18, 18, 5, 24, 25, 25, 24, 
	26, 27, 25, 23, 23, 5, 19, 20, 
	20, 19, 28, 21, 22, 20, 18, 18, 
	5, 20, 5, 30, 31, 31, 30, 28, 
	32, 31, 29, 29, 5, 34, 35, 35, 
	34, 36, 37, 35, 33, 33, 5, 31, 
	5, 38, 39, 41, 42, 43, 44, 41, 
	40, 41, 41, 45, 1, 46, 47, 46, 
	48, 48, 47, 3, 4, 50, 38, 38, 
	50, 51, 52, 53, 54, 55, 56, 49, 
	49, 39, 50, 50, 57, 7, 8, 8, 
	7, 9, 10, 11, 8, 6, 6, 58, 
	59, 58, 60, 58, 61, 61, 62, 30, 
	31, 31, 30, 28, 32, 31, 29, 29, 
	58, 38, 63, 0
};

static const char _pascal_trans_targs[] = {
	16, 1, 2, 16, 3, 22, 4, 4, 
	5, 22, 6, 7, 4, 4, 5, 22, 
	6, 7, 8, 8, 9, 10, 11, 8, 
	8, 9, 10, 11, 22, 12, 12, 13, 
	14, 12, 12, 13, 22, 14, 22, 0, 
	16, 17, 18, 19, 21, 16, 16, 20, 
	16, 22, 23, 24, 25, 26, 28, 15, 
	29, 22, 22, 8, 27, 22, 27, 22
};

static const char _pascal_trans_actions[] = {
	41, 13, 13, 58, 13, 31, 1, 0, 
	0, 21, 0, 0, 79, 49, 49, 83, 
	49, 49, 1, 0, 0, 1, 0, 67, 
	43, 43, 67, 43, 19, 3, 0, 0, 
	0, 71, 46, 46, 75, 46, 52, 0, 
	33, 11, 64, 13, 64, 35, 39, 13, 
	37, 55, 5, 87, 61, 9, 91, 7, 
	7, 23, 29, 3, 3, 25, 0, 27
};

static const char _pascal_to_state_actions[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	15, 0, 0, 0, 0, 0, 15, 0, 
	0, 0, 0, 0, 0, 0
};

static const char _pascal_from_state_actions[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	17, 0, 0, 0, 0, 0, 17, 0, 
	0, 0, 0, 0, 0, 0
};

static const char _pascal_eof_trans[] = {
	0, 1, 1, 1, 6, 6, 6, 6, 
	6, 6, 6, 6, 6, 6, 6, 0, 
	0, 46, 47, 47, 49, 47, 0, 58, 
	59, 59, 59, 62, 59, 64
};

static const int pascal_start = 16;
static const int pascal_first_final = 16;
static const int pascal_error = 0;

static const int pascal_en_pascal_line = 22;
static const int pascal_en_pascal_entity = 16;


#line 105 "pascal.rl"


/************************* Required for every parser *************************/

/* Parses a string buffer with Pascal code.
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
void parse_pascal(char *buffer, int length, int count,
                  void (*callback) (const char *lang, const char *entity, int s,
                                    int e, void *udata),
                  void *userdata
  ) {
  init

  
#line 217 "pascal.h"
	{
	cs = pascal_start;
	ts = 0;
	te = 0;
	act = 0;
	}

#line 128 "pascal.rl"
  cs = (count) ? pascal_en_pascal_line : pascal_en_pascal_entity;
  
#line 228 "pascal.h"
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
	_acts = _pascal_actions + _pascal_from_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 12:
#line 1 "NONE"
	{ts = p;}
	break;
#line 250 "pascal.h"
		}
	}

	_widec = (*p);
	_klen = _pascal_cond_lengths[cs];
	_keys = _pascal_cond_keys + (_pascal_cond_offsets[cs]*2);
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
				switch ( _pascal_cond_spaces[_pascal_cond_offsets[cs] + ((_mid - _keys)>>1)] ) {
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

	_keys = _pascal_trans_keys + _pascal_key_offsets[cs];
	_trans = _pascal_index_offsets[cs];

	_klen = _pascal_single_lengths[cs];
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

	_klen = _pascal_range_lengths[cs];
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
	_trans = _pascal_indicies[_trans];
_eof_trans:
	cs = _pascal_trans_targs[_trans];

	if ( _pascal_trans_actions[_trans] == 0 )
		goto _again;

	_acts = _pascal_actions + _pascal_trans_actions[_trans];
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
#line 31 "pascal.rl"
	{
    switch(entity) {
    case PASCAL_SPACE:
      ls
      break;
    case PASCAL_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(PASCAL_LANG)
      break;
    case NEWLINE:
      std_newline(PASCAL_LANG)
    }
  }
	break;
	case 3:
#line 50 "pascal.rl"
	{ entity = INTERNAL_NL; }
	break;
	case 4:
#line 58 "pascal.rl"
	{ entity = INTERNAL_NL; }
	break;
	case 5:
#line 69 "pascal.rl"
	{ entity = INTERNAL_NL; }
	break;
	case 6:
#line 79 "pascal.rl"
	{ entity = PASCAL_SPACE; }
	break;
	case 7:
#line 82 "pascal.rl"
	{ entity = NEWLINE;      }
	break;
	case 8:
#line 83 "pascal.rl"
	{ entity = PASCAL_ANY;   }
	break;
	case 9:
#line 100 "pascal.rl"
	{ entity = PASCAL_SPACE;   }
	break;
	case 10:
#line 101 "pascal.rl"
	{ entity = PASCAL_COMMENT; }
	break;
	case 13:
#line 1 "NONE"
	{te = p+1;}
	break;
	case 14:
#line 80 "pascal.rl"
	{te = p+1;}
	break;
	case 15:
#line 81 "pascal.rl"
	{te = p+1;}
	break;
	case 16:
#line 31 "pascal.rl"
	{te = p+1;{
    switch(entity) {
    case PASCAL_SPACE:
      ls
      break;
    case PASCAL_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(PASCAL_LANG)
      break;
    case NEWLINE:
      std_newline(PASCAL_LANG)
    }
  }}
	break;
	case 17:
#line 31 "pascal.rl"
	{te = p+1;{
    switch(entity) {
    case PASCAL_SPACE:
      ls
      break;
    case PASCAL_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(PASCAL_LANG)
      break;
    case NEWLINE:
      std_newline(PASCAL_LANG)
    }
  }}
	break;
	case 18:
#line 31 "pascal.rl"
	{te = p;p--;{
    switch(entity) {
    case PASCAL_SPACE:
      ls
      break;
    case PASCAL_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(PASCAL_LANG)
      break;
    case NEWLINE:
      std_newline(PASCAL_LANG)
    }
  }}
	break;
	case 19:
#line 80 "pascal.rl"
	{te = p;p--;}
	break;
	case 20:
#line 31 "pascal.rl"
	{te = p;p--;{
    switch(entity) {
    case PASCAL_SPACE:
      ls
      break;
    case PASCAL_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(PASCAL_LANG)
      break;
    case NEWLINE:
      std_newline(PASCAL_LANG)
    }
  }}
	break;
	case 21:
#line 31 "pascal.rl"
	{te = p;p--;{
    switch(entity) {
    case PASCAL_SPACE:
      ls
      break;
    case PASCAL_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(PASCAL_LANG)
      break;
    case NEWLINE:
      std_newline(PASCAL_LANG)
    }
  }}
	break;
	case 22:
#line 31 "pascal.rl"
	{{p = ((te))-1;}{
    switch(entity) {
    case PASCAL_SPACE:
      ls
      break;
    case PASCAL_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(PASCAL_LANG)
      break;
    case NEWLINE:
      std_newline(PASCAL_LANG)
    }
  }}
	break;
	case 23:
#line 88 "pascal.rl"
	{te = p+1;{
    callback(PASCAL_LANG, pascal_entities[entity], cint(ts), cint(te),
             userdata);
  }}
	break;
	case 24:
#line 103 "pascal.rl"
	{te = p+1;}
	break;
	case 25:
#line 88 "pascal.rl"
	{te = p;p--;{
    callback(PASCAL_LANG, pascal_entities[entity], cint(ts), cint(te),
             userdata);
  }}
	break;
	case 26:
#line 88 "pascal.rl"
	{te = p;p--;{
    callback(PASCAL_LANG, pascal_entities[entity], cint(ts), cint(te),
             userdata);
  }}
	break;
	case 27:
#line 103 "pascal.rl"
	{te = p;p--;}
	break;
	case 28:
#line 103 "pascal.rl"
	{{p = ((te))-1;}}
	break;
#line 570 "pascal.h"
		}
	}

_again:
	_acts = _pascal_actions + _pascal_to_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 11:
#line 1 "NONE"
	{ts = 0;}
	break;
#line 583 "pascal.h"
		}
	}

	if ( cs == 0 )
		goto _out;
	if ( ++p != pe )
		goto _resume;
	_test_eof: {}
	if ( p == eof )
	{
	if ( _pascal_eof_trans[cs] > 0 ) {
		_trans = _pascal_eof_trans[cs] - 1;
		goto _eof_trans;
	}
	}

	_out: {}
	}

#line 130 "pascal.rl"

  // if no newline at EOF; callback contents of last line
  if (count) { process_last_line(PASCAL_LANG) }
}

#endif

/*****************************************************************************/
