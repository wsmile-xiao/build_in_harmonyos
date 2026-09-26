
#line 1 "modula3.rl"
// modula3.rl, 
// derived from code written by Mitchell Foral. mitchell<att>caladbolg<dott>net


/************************* Required for every parser *************************/
#ifndef OHCOUNT_MODULA3_PARSER_H
#define OHCOUNT_MODULA3_PARSER_H

#include "../parser_macros.h"

// the name of the language
const char *MODULA3_LANG = LANG_MODULA3;

// the languages entities
const char *modula3_entities[] = {
  "space", "comment", "string", "any"
};

// constants associated with the entities
enum {
  MODULA3_SPACE = 0, MODULA3_COMMENT, MODULA3_STRING, MODULA3_ANY
};

/*****************************************************************************/


#line 30 "modula3.h"
static const char _modula3_actions[] = {
	0, 1, 0, 1, 1, 1, 9, 1, 
	10, 1, 12, 1, 13, 1, 14, 1, 
	15, 1, 16, 1, 19, 1, 22, 1, 
	23, 1, 24, 1, 25, 1, 28, 1, 
	29, 1, 30, 1, 31, 2, 1, 18, 
	2, 4, 1, 2, 4, 13, 2, 5, 
	1, 2, 5, 13, 2, 6, 2, 2, 
	7, 2, 2, 8, 2, 2, 10, 20, 
	2, 11, 21, 2, 13, 26, 2, 14, 
	27, 2, 17, 14, 3, 6, 2, 1, 
	3, 7, 2, 0, 3, 7, 2, 19, 
	3, 8, 2, 0, 3, 8, 2, 19, 
	3, 17, 0, 11, 3, 17, 3, 11, 
	3, 17, 3, 13
};

static const char _modula3_cond_offsets[] = {
	0, 0, 0, 0, 0, 0, 1, 2, 
	3, 5, 5, 6, 6, 6, 6, 6, 
	7, 7, 7, 7, 9, 11, 13, 13, 
	15, 18, 18, 18, 18, 18, 18, 18, 
	19, 19, 19, 19, 19
};

static const char _modula3_cond_lengths[] = {
	0, 0, 0, 0, 0, 1, 1, 1, 
	2, 0, 1, 0, 0, 0, 0, 1, 
	0, 0, 0, 2, 2, 2, 0, 2, 
	3, 0, 0, 0, 0, 0, 0, 1, 
	0, 0, 0, 0, 0
};

static const short _modula3_cond_keys[] = {
	42, 42, 42, 42, 42, 42, 41, 41, 
	42, 42, 13, 13, 13, 13, 13, 13, 
	42, 42, 13, 13, 42, 42, 13, 13, 
	42, 42, 13, 13, 42, 42, 13, 13, 
	41, 41, 42, 42, 13, 13, 0
};

static const char _modula3_cond_spaces[] = {
	2, 2, 2, 2, 2, 0, 0, 0, 
	1, 0, 1, 0, 1, 0, 1, 0, 
	1, 1, 0, 0
};

static const char _modula3_key_offsets[] = {
	0, 0, 2, 2, 4, 4, 11, 18, 
	26, 35, 39, 47, 51, 52, 57, 61, 
	69, 73, 74, 79, 94, 109, 124, 125, 
	141, 158, 159, 165, 168, 170, 172, 173, 
	186, 188, 192, 196, 197
};

static const short _modula3_trans_keys[] = {
	34, 92, 39, 92, 40, 1322, 1578, 0, 
	41, 43, 255, 40, 1322, 1578, 0, 41, 
	43, 255, 40, 41, 1322, 1578, 0, 39, 
	43, 255, 40, 1321, 1322, 1577, 1578, 0, 
	39, 43, 255, 9, 32, 34, 92, 10, 
	12, 269, 525, 0, 11, 14, 255, 9, 
	32, 34, 92, 10, 9, 10, 32, 34, 
	92, 9, 32, 39, 92, 10, 12, 269, 
	525, 0, 11, 14, 255, 9, 32, 39, 
	92, 10, 9, 10, 32, 39, 92, 9, 
	10, 12, 32, 40, 269, 525, 810, 1066, 
	0, 8, 14, 41, 43, 255, 9, 10, 
	12, 32, 40, 269, 525, 810, 1066, 0, 
	8, 14, 41, 43, 255, 9, 10, 12, 
	32, 40, 269, 525, 810, 1066, 0, 8, 
	14, 41, 43, 255, 10, 9, 10, 12, 
	32, 40, 41, 269, 525, 810, 1066, 0, 
	8, 14, 39, 43, 255, 9, 10, 12, 
	32, 40, 269, 525, 809, 810, 1065, 1066, 
	0, 8, 14, 39, 43, 255, 10, 32, 
	34, 39, 40, 9, 13, 32, 9, 13, 
	34, 92, 39, 92, 42, 9, 10, 12, 
	32, 34, 39, 40, 269, 525, 0, 8, 
	14, 255, 9, 32, 9, 32, 34, 92, 
	9, 32, 39, 92, 42, 10, 0
};

static const char _modula3_single_lengths[] = {
	0, 2, 0, 2, 0, 3, 3, 4, 
	5, 4, 4, 4, 1, 5, 4, 4, 
	4, 1, 5, 9, 9, 9, 1, 10, 
	11, 1, 4, 1, 2, 2, 1, 9, 
	2, 4, 4, 1, 1
};

static const char _modula3_range_lengths[] = {
	0, 0, 0, 0, 0, 2, 2, 2, 
	2, 0, 2, 0, 0, 0, 0, 2, 
	0, 0, 0, 3, 3, 3, 0, 3, 
	3, 0, 1, 1, 0, 0, 0, 2, 
	0, 0, 0, 0, 0
};

static const char _modula3_index_offsets[] = {
	0, 0, 3, 4, 7, 8, 14, 20, 
	27, 35, 40, 47, 52, 54, 60, 65, 
	72, 77, 79, 85, 98, 111, 124, 126, 
	140, 155, 157, 163, 166, 169, 172, 174, 
	186, 189, 194, 199, 201
};

static const char _modula3_indicies[] = {
	2, 3, 1, 1, 2, 5, 4, 4, 
	7, 8, 9, 6, 6, 0, 7, 10, 
	11, 6, 6, 0, 7, 12, 8, 9, 
	6, 6, 0, 7, 12, 8, 13, 9, 
	6, 6, 0, 16, 16, 17, 18, 15, 
	19, 19, 20, 21, 15, 15, 14, 23, 
	23, 24, 25, 22, 19, 14, 23, 26, 
	23, 24, 25, 22, 28, 28, 17, 29, 
	27, 30, 30, 31, 32, 27, 27, 14, 
	34, 34, 35, 36, 33, 30, 14, 34, 
	37, 34, 35, 36, 33, 39, 40, 40, 
	39, 41, 42, 40, 43, 44, 38, 38, 
	38, 14, 46, 47, 47, 46, 48, 49, 
	47, 50, 51, 45, 45, 45, 14, 39, 
	40, 40, 39, 41, 42, 40, 52, 53, 
	38, 38, 38, 14, 40, 14, 39, 40, 
	40, 39, 41, 54, 42, 40, 43, 44, 
	38, 38, 38, 14, 39, 40, 40, 39, 
	41, 42, 40, 54, 43, 55, 44, 38, 
	38, 38, 14, 56, 57, 59, 60, 61, 
	62, 59, 58, 59, 59, 63, 2, 3, 
	1, 2, 5, 4, 6, 64, 66, 56, 
	56, 66, 67, 68, 69, 70, 71, 65, 
	65, 57, 66, 66, 72, 16, 16, 17, 
	18, 15, 28, 28, 17, 29, 27, 38, 
	73, 56, 74, 0
};

static const char _modula3_trans_targs[] = {
	26, 1, 26, 2, 3, 4, 5, 6, 
	7, 8, 7, 8, 5, 26, 31, 9, 
	9, 31, 10, 11, 12, 13, 9, 9, 
	31, 10, 11, 14, 14, 15, 16, 17, 
	18, 14, 14, 31, 15, 16, 19, 19, 
	20, 21, 22, 23, 24, 19, 19, 20, 
	21, 22, 23, 24, 23, 24, 19, 31, 
	31, 0, 26, 27, 28, 29, 30, 26, 
	26, 31, 32, 33, 34, 35, 25, 36, 
	31, 31, 31
};

static const char _modula3_trans_actions[] = {
	35, 13, 70, 13, 13, 13, 11, 11, 
	11, 11, 43, 43, 49, 67, 27, 1, 
	0, 19, 0, 0, 0, 0, 88, 58, 
	92, 58, 88, 1, 0, 0, 0, 0, 
	0, 80, 55, 84, 55, 80, 3, 0, 
	0, 3, 0, 3, 3, 76, 52, 52, 
	76, 52, 76, 76, 40, 40, 46, 37, 
	61, 0, 29, 9, 73, 73, 104, 31, 
	33, 64, 5, 96, 96, 100, 7, 7, 
	21, 25, 23
};

static const char _modula3_to_state_actions[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 15, 0, 0, 0, 0, 15, 
	0, 0, 0, 0, 0
};

static const char _modula3_from_state_actions[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 17, 0, 0, 0, 0, 17, 
	0, 0, 0, 0, 0
};

static const char _modula3_eof_trans[] = {
	0, 1, 1, 1, 1, 1, 1, 1, 
	1, 15, 15, 15, 15, 15, 15, 15, 
	15, 15, 15, 15, 15, 15, 15, 15, 
	15, 0, 0, 64, 65, 65, 65, 0, 
	73, 74, 74, 74, 75
};

static const int modula3_start = 26;
static const int modula3_first_final = 26;
static const int modula3_error = 0;

static const int modula3_en_modula3_line = 31;
static const int modula3_en_modula3_entity = 26;


#line 131 "modula3.rl"


/************************* Required for every parser *************************/

/* Parses a string buffer with Modula-3 code.
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
void parse_modula3(char *buffer, int length, int count,
                  void (*callback) (const char *lang, const char *entity, int s,
                                    int e, void *udata),
                  void *userdata
  ) {
  init

  int nest_count = 0;

  
#line 251 "modula3.h"
	{
	cs = modula3_start;
	ts = 0;
	te = 0;
	act = 0;
	}

#line 156 "modula3.rl"
  cs = (count) ? modula3_en_modula3_line : modula3_en_modula3_entity;
  
#line 262 "modula3.h"
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
	_acts = _modula3_actions + _modula3_from_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 16:
#line 1 "NONE"
	{ts = p;}
	break;
#line 284 "modula3.h"
		}
	}

	_widec = (*p);
	_klen = _modula3_cond_lengths[cs];
	_keys = _modula3_cond_keys + (_modula3_cond_offsets[cs]*2);
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
				switch ( _modula3_cond_spaces[_modula3_cond_offsets[cs] + ((_mid - _keys)>>1)] ) {
	case 0: {
		_widec = (short)(256 + ((*p) - 0));
		if ( 
#line 9 "common.rl"
 p+1 < pe && *(p+1) != '\n'  ) _widec += 256;
		break;
	}
	case 1: {
		_widec = (short)(768 + ((*p) - 0));
		if ( 
#line 67 "modula3.rl"
 nest_count == 0  ) _widec += 256;
		break;
	}
	case 2: {
		_widec = (short)(1280 + ((*p) - 0));
		if ( 
#line 119 "modula3.rl"
 nest_count == 0  ) _widec += 256;
		break;
	}
				}
				break;
			}
		}
	}

	_keys = _modula3_trans_keys + _modula3_key_offsets[cs];
	_trans = _modula3_index_offsets[cs];

	_klen = _modula3_single_lengths[cs];
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

	_klen = _modula3_range_lengths[cs];
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
	_trans = _modula3_indicies[_trans];
_eof_trans:
	cs = _modula3_trans_targs[_trans];

	if ( _modula3_trans_actions[_trans] == 0 )
		goto _again;

	_acts = _modula3_actions + _modula3_trans_actions[_trans];
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
#line 33 "modula3.rl"
	{
    switch(entity) {
    case MODULA3_SPACE:
      ls
      break;
    case MODULA3_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(MODULA3_LANG)
      break;
    case NEWLINE:
      std_newline(MODULA3_LANG)
    }
  }
	break;
	case 3:
#line 52 "modula3.rl"
	{ nest_count = 0; }
	break;
	case 4:
#line 53 "modula3.rl"
	{ nest_count++; }
	break;
	case 5:
#line 54 "modula3.rl"
	{ nest_count--; }
	break;
	case 6:
#line 58 "modula3.rl"
	{ entity = INTERNAL_NL; }
	break;
	case 7:
#line 74 "modula3.rl"
	{ entity = INTERNAL_NL; }
	break;
	case 8:
#line 84 "modula3.rl"
	{ entity = INTERNAL_NL; }
	break;
	case 9:
#line 98 "modula3.rl"
	{ entity = MODULA3_SPACE; }
	break;
	case 10:
#line 101 "modula3.rl"
	{ entity = NEWLINE;       }
	break;
	case 11:
#line 102 "modula3.rl"
	{ entity = MODULA3_ANY;   }
	break;
	case 12:
#line 125 "modula3.rl"
	{ entity = MODULA3_SPACE;   }
	break;
	case 13:
#line 126 "modula3.rl"
	{ entity = MODULA3_COMMENT; }
	break;
	case 14:
#line 127 "modula3.rl"
	{ entity = MODULA3_STRING;  }
	break;
	case 17:
#line 1 "NONE"
	{te = p+1;}
	break;
	case 18:
#line 99 "modula3.rl"
	{te = p+1;}
	break;
	case 19:
#line 100 "modula3.rl"
	{te = p+1;}
	break;
	case 20:
#line 33 "modula3.rl"
	{te = p+1;{
    switch(entity) {
    case MODULA3_SPACE:
      ls
      break;
    case MODULA3_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(MODULA3_LANG)
      break;
    case NEWLINE:
      std_newline(MODULA3_LANG)
    }
  }}
	break;
	case 21:
#line 33 "modula3.rl"
	{te = p+1;{
    switch(entity) {
    case MODULA3_SPACE:
      ls
      break;
    case MODULA3_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(MODULA3_LANG)
      break;
    case NEWLINE:
      std_newline(MODULA3_LANG)
    }
  }}
	break;
	case 22:
#line 33 "modula3.rl"
	{te = p;p--;{
    switch(entity) {
    case MODULA3_SPACE:
      ls
      break;
    case MODULA3_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(MODULA3_LANG)
      break;
    case NEWLINE:
      std_newline(MODULA3_LANG)
    }
  }}
	break;
	case 23:
#line 33 "modula3.rl"
	{te = p;p--;{
    switch(entity) {
    case MODULA3_SPACE:
      ls
      break;
    case MODULA3_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(MODULA3_LANG)
      break;
    case NEWLINE:
      std_newline(MODULA3_LANG)
    }
  }}
	break;
	case 24:
#line 33 "modula3.rl"
	{te = p;p--;{
    switch(entity) {
    case MODULA3_SPACE:
      ls
      break;
    case MODULA3_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(MODULA3_LANG)
      break;
    case NEWLINE:
      std_newline(MODULA3_LANG)
    }
  }}
	break;
	case 25:
#line 33 "modula3.rl"
	{{p = ((te))-1;}{
    switch(entity) {
    case MODULA3_SPACE:
      ls
      break;
    case MODULA3_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(MODULA3_LANG)
      break;
    case NEWLINE:
      std_newline(MODULA3_LANG)
    }
  }}
	break;
	case 26:
#line 108 "modula3.rl"
	{te = p+1;{
    callback(MODULA3_LANG, modula3_entities[entity], cint(ts), cint(te),
             userdata);
  }}
	break;
	case 27:
#line 108 "modula3.rl"
	{te = p+1;{
    callback(MODULA3_LANG, modula3_entities[entity], cint(ts), cint(te),
             userdata);
  }}
	break;
	case 28:
#line 129 "modula3.rl"
	{te = p+1;}
	break;
	case 29:
#line 108 "modula3.rl"
	{te = p;p--;{
    callback(MODULA3_LANG, modula3_entities[entity], cint(ts), cint(te),
             userdata);
  }}
	break;
	case 30:
#line 129 "modula3.rl"
	{te = p;p--;}
	break;
	case 31:
#line 129 "modula3.rl"
	{{p = ((te))-1;}}
	break;
#line 630 "modula3.h"
		}
	}

_again:
	_acts = _modula3_actions + _modula3_to_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 15:
#line 1 "NONE"
	{ts = 0;}
	break;
#line 643 "modula3.h"
		}
	}

	if ( cs == 0 )
		goto _out;
	if ( ++p != pe )
		goto _resume;
	_test_eof: {}
	if ( p == eof )
	{
	if ( _modula3_eof_trans[cs] > 0 ) {
		_trans = _modula3_eof_trans[cs] - 1;
		goto _eof_trans;
	}
	}

	_out: {}
	}

#line 158 "modula3.rl"

  // if no newline at EOF; callback contents of last line
  if (count) { process_last_line(MODULA3_LANG) }
}

#endif

/*****************************************************************************/
