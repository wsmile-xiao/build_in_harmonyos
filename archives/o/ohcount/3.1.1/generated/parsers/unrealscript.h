
#line 1 "unrealscript.rl"
// unrealscript.rl derived from code written by Mitchell Foral. mitchell<att>caladbolg<dott>net.

/************************* Required for every parser *************************/
#ifndef OHCOUNT_UNREALSCRIPT_PARSER_H
#define OHCOUNT_UNREALSCRIPT_PARSER_H

#include "../parser_macros.h"

// the name of the language
const char *UNREALSCRIPT_LANG = LANG_UNREALSCRIPT;

// the languages entities
const char *unrealscript_entities[] = {
  "space", "comment", "string", "any"
};

// constants associated with the entities
enum {
  UNREALSCRIPT_SPACE = 0, UNREALSCRIPT_COMMENT, UNREALSCRIPT_STRING, UNREALSCRIPT_ANY
};

/*****************************************************************************/


#line 28 "unrealscript.h"
static const char _unrealscript_actions[] = {
	0, 1, 0, 1, 1, 1, 6, 1, 
	7, 1, 9, 1, 10, 1, 11, 1, 
	12, 1, 14, 1, 15, 1, 18, 1, 
	19, 1, 20, 1, 21, 1, 22, 1, 
	24, 1, 25, 1, 26, 1, 27, 1, 
	28, 2, 3, 2, 2, 4, 2, 2, 
	5, 2, 2, 7, 16, 2, 8, 17, 
	2, 10, 23, 2, 13, 8, 2, 13, 
	10, 3, 3, 2, 1, 3, 4, 2, 
	0, 3, 4, 2, 15, 3, 5, 2, 
	0, 3, 5, 2, 15, 3, 13, 0, 
	8
};

static const char _unrealscript_cond_offsets[] = {
	0, 0, 0, 0, 0, 1, 1, 1, 
	1, 1, 2, 2, 2, 2, 3, 4, 
	5, 5, 5, 5, 5, 5, 5, 6, 
	6, 6, 6, 6, 6
};

static const char _unrealscript_cond_lengths[] = {
	0, 0, 0, 0, 1, 0, 0, 0, 
	0, 1, 0, 0, 0, 1, 1, 1, 
	0, 0, 0, 0, 0, 0, 1, 0, 
	0, 0, 0, 0, 0
};

static const short _unrealscript_cond_keys[] = {
	13, 13, 13, 13, 13, 13, 13, 13, 
	13, 13, 13, 13, 0
};

static const char _unrealscript_cond_spaces[] = {
	0, 0, 0, 0, 0, 0, 0
};

static const char _unrealscript_key_offsets[] = {
	0, 0, 1, 3, 7, 15, 19, 20, 
	25, 29, 37, 41, 42, 47, 58, 69, 
	81, 82, 83, 87, 90, 92, 95, 108, 
	110, 114, 118, 120, 123
};

static const short _unrealscript_trans_keys[] = {
	42, 42, 47, 9, 32, 34, 92, 10, 
	12, 269, 525, 0, 11, 14, 255, 9, 
	32, 34, 92, 10, 9, 10, 32, 34, 
	92, 9, 32, 39, 92, 10, 12, 269, 
	525, 0, 11, 14, 255, 9, 32, 39, 
	92, 10, 9, 10, 32, 39, 92, 9, 
	10, 12, 32, 42, 269, 525, 0, 11, 
	14, 255, 9, 10, 12, 32, 42, 269, 
	525, 0, 11, 14, 255, 9, 10, 12, 
	32, 42, 47, 269, 525, 0, 11, 14, 
	255, 10, 10, 32, 47, 9, 13, 32, 
	9, 13, 42, 47, 10, 12, 13, 9, 
	10, 12, 32, 34, 39, 47, 269, 525, 
	0, 8, 14, 255, 9, 32, 9, 32, 
	34, 92, 9, 32, 39, 92, 42, 47, 
	10, 12, 13, 10, 0
};

static const char _unrealscript_single_lengths[] = {
	0, 1, 2, 4, 4, 4, 1, 5, 
	4, 4, 4, 1, 5, 7, 7, 8, 
	1, 1, 2, 1, 2, 1, 9, 2, 
	4, 4, 2, 1, 1
};

static const char _unrealscript_range_lengths[] = {
	0, 0, 0, 0, 2, 0, 0, 0, 
	0, 2, 0, 0, 0, 2, 2, 2, 
	0, 0, 1, 1, 0, 1, 2, 0, 
	0, 0, 0, 1, 0
};

static const char _unrealscript_index_offsets[] = {
	0, 0, 2, 5, 10, 17, 22, 24, 
	30, 35, 42, 47, 49, 55, 65, 75, 
	86, 88, 90, 94, 97, 100, 103, 115, 
	118, 123, 128, 131, 134
};

static const char _unrealscript_indicies[] = {
	2, 1, 2, 3, 1, 6, 6, 7, 
	8, 5, 9, 9, 10, 11, 5, 5, 
	4, 13, 13, 14, 15, 12, 9, 4, 
	13, 16, 13, 14, 15, 12, 18, 18, 
	7, 19, 17, 20, 20, 21, 22, 17, 
	17, 4, 24, 24, 25, 26, 23, 20, 
	4, 24, 27, 24, 25, 26, 23, 29, 
	30, 30, 29, 31, 32, 30, 28, 28, 
	4, 34, 35, 35, 34, 36, 37, 35, 
	33, 33, 4, 29, 30, 30, 29, 31, 
	38, 32, 30, 28, 28, 4, 30, 4, 
	39, 40, 42, 43, 42, 41, 42, 42, 
	44, 1, 46, 45, 47, 47, 46, 49, 
	39, 39, 49, 50, 51, 52, 53, 54, 
	48, 48, 40, 49, 49, 55, 6, 6, 
	7, 8, 5, 18, 18, 7, 19, 17, 
	28, 57, 56, 58, 58, 59, 39, 60, 
	0
};

static const char _unrealscript_trans_targs[] = {
	18, 1, 2, 18, 22, 3, 3, 22, 
	4, 5, 6, 7, 3, 3, 22, 4, 
	5, 8, 8, 9, 10, 11, 12, 8, 
	8, 22, 9, 10, 13, 13, 14, 15, 
	16, 13, 13, 14, 15, 16, 22, 22, 
	0, 18, 19, 20, 18, 18, 21, 18, 
	22, 23, 24, 25, 26, 17, 28, 22, 
	22, 27, 22, 27, 22
};

static const char _unrealscript_trans_actions[] = {
	39, 11, 11, 56, 29, 1, 0, 19, 
	0, 0, 0, 0, 77, 47, 81, 47, 
	77, 1, 0, 0, 0, 0, 0, 69, 
	44, 73, 44, 69, 3, 0, 0, 3, 
	0, 65, 41, 41, 65, 41, 17, 50, 
	0, 31, 9, 62, 33, 37, 11, 35, 
	53, 5, 85, 85, 59, 7, 7, 21, 
	27, 3, 23, 0, 25
};

static const char _unrealscript_to_state_actions[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 13, 0, 0, 0, 13, 0, 
	0, 0, 0, 0, 0
};

static const char _unrealscript_from_state_actions[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 15, 0, 0, 0, 15, 0, 
	0, 0, 0, 0, 0
};

static const char _unrealscript_eof_trans[] = {
	0, 1, 1, 5, 5, 5, 5, 5, 
	5, 5, 5, 5, 5, 5, 5, 5, 
	5, 0, 0, 45, 46, 48, 0, 56, 
	57, 57, 57, 59, 61
};

static const int unrealscript_start = 18;
static const int unrealscript_first_final = 18;
static const int unrealscript_error = 0;

static const int unrealscript_en_unrealscript_line = 22;
static const int unrealscript_en_unrealscript_entity = 18;


#line 104 "unrealscript.rl"


/************************* Required for every parser *************************/

/* Parses a string buffer with UnrealScript code.
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
void parse_unrealscript(char *buffer, int length, int count,
             void (*callback) (const char *lang, const char *entity, int s,
                               int e, void *udata),
             void *userdata
  ) {
  init

  
#line 210 "unrealscript.h"
	{
	cs = unrealscript_start;
	ts = 0;
	te = 0;
	act = 0;
	}

#line 127 "unrealscript.rl"
  cs = (count) ? unrealscript_en_unrealscript_line : unrealscript_en_unrealscript_entity;
  
#line 221 "unrealscript.h"
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
	_acts = _unrealscript_actions + _unrealscript_from_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 12:
#line 1 "NONE"
	{ts = p;}
	break;
#line 243 "unrealscript.h"
		}
	}

	_widec = (*p);
	_klen = _unrealscript_cond_lengths[cs];
	_keys = _unrealscript_cond_keys + (_unrealscript_cond_offsets[cs]*2);
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
				switch ( _unrealscript_cond_spaces[_unrealscript_cond_offsets[cs] + ((_mid - _keys)>>1)] ) {
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

	_keys = _unrealscript_trans_keys + _unrealscript_key_offsets[cs];
	_trans = _unrealscript_index_offsets[cs];

	_klen = _unrealscript_single_lengths[cs];
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

	_klen = _unrealscript_range_lengths[cs];
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
	_trans = _unrealscript_indicies[_trans];
_eof_trans:
	cs = _unrealscript_trans_targs[_trans];

	if ( _unrealscript_trans_actions[_trans] == 0 )
		goto _again;

	_acts = _unrealscript_actions + _unrealscript_trans_actions[_trans];
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
#line 31 "unrealscript.rl"
	{
    switch(entity) {
    case UNREALSCRIPT_SPACE:
      ls
      break;
    case UNREALSCRIPT_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(UNREALSCRIPT_LANG)
      break;
    case NEWLINE:
      std_newline(UNREALSCRIPT_LANG)
    }
  }
	break;
	case 3:
#line 50 "unrealscript.rl"
	{ entity = INTERNAL_NL; }
	break;
	case 4:
#line 60 "unrealscript.rl"
	{ entity = INTERNAL_NL; }
	break;
	case 5:
#line 70 "unrealscript.rl"
	{ entity = INTERNAL_NL; }
	break;
	case 6:
#line 81 "unrealscript.rl"
	{ entity = UNREALSCRIPT_SPACE; }
	break;
	case 7:
#line 84 "unrealscript.rl"
	{ entity = NEWLINE;            }
	break;
	case 8:
#line 85 "unrealscript.rl"
	{ entity = UNREALSCRIPT_ANY;   }
	break;
	case 9:
#line 99 "unrealscript.rl"
	{ entity = UNREALSCRIPT_SPACE;   }
	break;
	case 10:
#line 100 "unrealscript.rl"
	{ entity = UNREALSCRIPT_COMMENT; }
	break;
	case 13:
#line 1 "NONE"
	{te = p+1;}
	break;
	case 14:
#line 82 "unrealscript.rl"
	{te = p+1;}
	break;
	case 15:
#line 83 "unrealscript.rl"
	{te = p+1;}
	break;
	case 16:
#line 31 "unrealscript.rl"
	{te = p+1;{
    switch(entity) {
    case UNREALSCRIPT_SPACE:
      ls
      break;
    case UNREALSCRIPT_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(UNREALSCRIPT_LANG)
      break;
    case NEWLINE:
      std_newline(UNREALSCRIPT_LANG)
    }
  }}
	break;
	case 17:
#line 31 "unrealscript.rl"
	{te = p+1;{
    switch(entity) {
    case UNREALSCRIPT_SPACE:
      ls
      break;
    case UNREALSCRIPT_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(UNREALSCRIPT_LANG)
      break;
    case NEWLINE:
      std_newline(UNREALSCRIPT_LANG)
    }
  }}
	break;
	case 18:
#line 31 "unrealscript.rl"
	{te = p;p--;{
    switch(entity) {
    case UNREALSCRIPT_SPACE:
      ls
      break;
    case UNREALSCRIPT_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(UNREALSCRIPT_LANG)
      break;
    case NEWLINE:
      std_newline(UNREALSCRIPT_LANG)
    }
  }}
	break;
	case 19:
#line 82 "unrealscript.rl"
	{te = p;p--;}
	break;
	case 20:
#line 31 "unrealscript.rl"
	{te = p;p--;{
    switch(entity) {
    case UNREALSCRIPT_SPACE:
      ls
      break;
    case UNREALSCRIPT_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(UNREALSCRIPT_LANG)
      break;
    case NEWLINE:
      std_newline(UNREALSCRIPT_LANG)
    }
  }}
	break;
	case 21:
#line 31 "unrealscript.rl"
	{te = p;p--;{
    switch(entity) {
    case UNREALSCRIPT_SPACE:
      ls
      break;
    case UNREALSCRIPT_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(UNREALSCRIPT_LANG)
      break;
    case NEWLINE:
      std_newline(UNREALSCRIPT_LANG)
    }
  }}
	break;
	case 22:
#line 31 "unrealscript.rl"
	{{p = ((te))-1;}{
    switch(entity) {
    case UNREALSCRIPT_SPACE:
      ls
      break;
    case UNREALSCRIPT_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(UNREALSCRIPT_LANG)
      break;
    case NEWLINE:
      std_newline(UNREALSCRIPT_LANG)
    }
  }}
	break;
	case 23:
#line 90 "unrealscript.rl"
	{te = p+1;{
    callback(UNREALSCRIPT_LANG, unrealscript_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 24:
#line 102 "unrealscript.rl"
	{te = p+1;}
	break;
	case 25:
#line 90 "unrealscript.rl"
	{te = p;p--;{
    callback(UNREALSCRIPT_LANG, unrealscript_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 26:
#line 90 "unrealscript.rl"
	{te = p;p--;{
    callback(UNREALSCRIPT_LANG, unrealscript_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 27:
#line 102 "unrealscript.rl"
	{te = p;p--;}
	break;
	case 28:
#line 102 "unrealscript.rl"
	{{p = ((te))-1;}}
	break;
#line 560 "unrealscript.h"
		}
	}

_again:
	_acts = _unrealscript_actions + _unrealscript_to_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 11:
#line 1 "NONE"
	{ts = 0;}
	break;
#line 573 "unrealscript.h"
		}
	}

	if ( cs == 0 )
		goto _out;
	if ( ++p != pe )
		goto _resume;
	_test_eof: {}
	if ( p == eof )
	{
	if ( _unrealscript_eof_trans[cs] > 0 ) {
		_trans = _unrealscript_eof_trans[cs] - 1;
		goto _eof_trans;
	}
	}

	_out: {}
	}

#line 129 "unrealscript.rl"

  // if no newline at EOF; callback contents of last line
  if (count) { process_last_line(UNREALSCRIPT_LANG) }
}

#endif

/*****************************************************************************/
