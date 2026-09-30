
#line 1 "actionscript.rl"
// actionscript.rl written by Mitchell Foral. mitchell<att>caladbolg<dott>net.

/************************* Required for every parser *************************/
#ifndef OHCOUNT_ACTIONSCRIPT_PARSER_H
#define OHCOUNT_ACTIONSCRIPT_PARSER_H

#include "../parser_macros.h"

// the name of the language
const char *AS_LANG = LANG_ACTIONSCRIPT;

// the languages entities
const char *as_entities[] = {
  "space", "comment", "string", "any",
};

// constants associated with the entities
enum {
  AS_SPACE = 0, AS_COMMENT, AS_STRING, AS_ANY
};

/*****************************************************************************/


#line 28 "actionscript.h"
static const char _actionscript_actions[] = {
	0, 1, 0, 1, 1, 1, 5, 1, 
	6, 1, 8, 1, 9, 1, 10, 1, 
	11, 1, 13, 1, 14, 1, 17, 1, 
	18, 1, 19, 1, 20, 1, 21, 1, 
	23, 1, 24, 1, 25, 1, 26, 1, 
	27, 2, 3, 2, 2, 4, 2, 2, 
	6, 15, 2, 7, 16, 2, 9, 22, 
	2, 12, 7, 2, 12, 9, 3, 3, 
	2, 1, 3, 4, 2, 0, 3, 12, 
	0, 7
};

static const char _actionscript_cond_offsets[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	1, 2, 3, 3, 3, 3, 3, 3, 
	3, 3, 3, 4, 5, 6, 7, 7, 
	7, 7, 7, 7, 7, 8, 8, 8, 
	8, 8, 8, 8
};

static const char _actionscript_cond_lengths[] = {
	0, 0, 0, 0, 0, 0, 0, 1, 
	1, 1, 0, 0, 0, 0, 0, 0, 
	0, 0, 1, 1, 1, 1, 0, 0, 
	0, 0, 0, 0, 1, 0, 0, 0, 
	0, 0, 0, 0
};

static const short _actionscript_cond_keys[] = {
	13, 13, 13, 13, 13, 13, 13, 13, 
	13, 13, 13, 13, 13, 13, 13, 13, 
	0
};

static const char _actionscript_cond_spaces[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0
};

static const char _actionscript_key_offsets[] = {
	0, 0, 1, 3, 8, 11, 16, 19, 
	30, 41, 53, 54, 55, 56, 57, 58, 
	59, 60, 61, 72, 83, 94, 106, 107, 
	108, 112, 115, 117, 120, 134, 136, 141, 
	146, 148, 151, 152
};

static const short _actionscript_trans_keys[] = {
	42, 42, 47, 10, 34, 92, 12, 13, 
	10, 12, 13, 10, 39, 92, 12, 13, 
	10, 12, 13, 9, 10, 12, 32, 42, 
	269, 525, 0, 11, 14, 255, 9, 10, 
	12, 32, 42, 269, 525, 0, 11, 14, 
	255, 9, 10, 12, 32, 42, 47, 269, 
	525, 0, 11, 14, 255, 10, 91, 67, 
	68, 65, 84, 65, 91, 9, 10, 12, 
	32, 93, 269, 525, 0, 11, 14, 255, 
	9, 10, 12, 32, 93, 269, 525, 0, 
	11, 14, 255, 9, 10, 12, 32, 93, 
	269, 525, 0, 11, 14, 255, 9, 10, 
	12, 32, 62, 93, 269, 525, 0, 11, 
	14, 255, 10, 10, 32, 47, 9, 13, 
	32, 9, 13, 42, 47, 10, 12, 13, 
	9, 10, 12, 32, 34, 39, 47, 60, 
	269, 525, 0, 8, 14, 255, 9, 32, 
	10, 34, 92, 12, 13, 10, 39, 92, 
	12, 13, 42, 47, 10, 12, 13, 33, 
	10, 0
};

static const char _actionscript_single_lengths[] = {
	0, 1, 2, 3, 1, 3, 1, 7, 
	7, 8, 1, 1, 1, 1, 1, 1, 
	1, 1, 7, 7, 7, 8, 1, 1, 
	2, 1, 2, 1, 10, 2, 3, 3, 
	2, 1, 1, 1
};

static const char _actionscript_range_lengths[] = {
	0, 0, 0, 1, 1, 1, 1, 2, 
	2, 2, 0, 0, 0, 0, 0, 0, 
	0, 0, 2, 2, 2, 2, 0, 0, 
	1, 1, 0, 1, 2, 0, 1, 1, 
	0, 1, 0, 0
};

static const char _actionscript_index_offsets[] = {
	0, 0, 2, 5, 10, 13, 18, 21, 
	31, 41, 52, 54, 56, 58, 60, 62, 
	64, 66, 68, 78, 88, 98, 109, 111, 
	113, 117, 120, 123, 126, 139, 142, 147, 
	152, 155, 158, 160
};

static const char _actionscript_indicies[] = {
	2, 1, 2, 3, 1, 4, 6, 7, 
	4, 5, 4, 4, 5, 4, 6, 9, 
	4, 8, 4, 4, 8, 11, 12, 12, 
	11, 13, 14, 12, 10, 10, 4, 16, 
	17, 17, 16, 18, 19, 17, 15, 15, 
	4, 11, 12, 12, 11, 13, 20, 14, 
	12, 10, 10, 4, 12, 4, 21, 4, 
	22, 4, 23, 4, 24, 4, 25, 4, 
	26, 4, 27, 4, 28, 29, 29, 28, 
	30, 31, 29, 27, 27, 4, 33, 34, 
	34, 33, 35, 36, 34, 32, 32, 4, 
	28, 29, 29, 28, 37, 31, 29, 27, 
	27, 4, 28, 29, 29, 28, 6, 37, 
	31, 29, 27, 27, 4, 29, 4, 38, 
	39, 41, 42, 41, 40, 41, 41, 43, 
	1, 45, 44, 46, 46, 45, 48, 38, 
	38, 48, 49, 50, 51, 52, 53, 54, 
	47, 47, 39, 48, 48, 55, 56, 6, 
	7, 56, 5, 56, 6, 9, 56, 8, 
	10, 57, 56, 58, 58, 59, 60, 56, 
	38, 61, 0
};

static const char _actionscript_trans_targs[] = {
	24, 1, 2, 24, 28, 3, 28, 4, 
	5, 6, 7, 7, 8, 9, 10, 7, 
	7, 8, 9, 10, 28, 12, 13, 14, 
	15, 16, 17, 18, 18, 19, 20, 22, 
	18, 18, 19, 20, 22, 21, 28, 0, 
	24, 25, 26, 24, 24, 27, 24, 28, 
	29, 30, 31, 32, 34, 23, 35, 28, 
	28, 33, 28, 33, 11, 28
};

static const char _actionscript_trans_actions[] = {
	39, 11, 11, 53, 29, 0, 19, 0, 
	0, 0, 3, 0, 0, 3, 0, 62, 
	41, 41, 62, 41, 17, 0, 0, 0, 
	0, 0, 0, 1, 0, 0, 1, 0, 
	66, 44, 44, 66, 44, 1, 47, 0, 
	31, 9, 59, 33, 37, 11, 35, 50, 
	5, 70, 70, 56, 56, 7, 7, 21, 
	27, 3, 23, 0, 0, 25
};

static const char _actionscript_to_state_actions[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	13, 0, 0, 0, 13, 0, 0, 0, 
	0, 0, 0, 0
};

static const char _actionscript_from_state_actions[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	15, 0, 0, 0, 15, 0, 0, 0, 
	0, 0, 0, 0
};

static const char _actionscript_eof_trans[] = {
	0, 1, 1, 5, 5, 5, 5, 5, 
	5, 5, 5, 5, 5, 5, 5, 5, 
	5, 5, 5, 5, 5, 5, 5, 0, 
	0, 44, 45, 47, 0, 56, 57, 57, 
	57, 59, 57, 62
};

static const int actionscript_start = 24;
static const int actionscript_first_final = 24;
static const int actionscript_error = 0;

static const int actionscript_en_as_line = 28;
static const int actionscript_en_as_entity = 24;


#line 93 "actionscript.rl"


/************************* Required for every parser *************************/

/* Parses a string buffer with Actionscript code.
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
void parse_actionscript(char *buffer, int length, int count,
                        void (*callback) (const char *lang, const char *entity,
                                          int s, int e, void *udata),
                        void *userdata
  ) {
  init

  
#line 226 "actionscript.h"
	{
	cs = actionscript_start;
	ts = 0;
	te = 0;
	act = 0;
	}

#line 116 "actionscript.rl"
  cs = (count) ? actionscript_en_as_line : actionscript_en_as_entity;
  
#line 237 "actionscript.h"
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
	_acts = _actionscript_actions + _actionscript_from_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 11:
#line 1 "NONE"
	{ts = p;}
	break;
#line 259 "actionscript.h"
		}
	}

	_widec = (*p);
	_klen = _actionscript_cond_lengths[cs];
	_keys = _actionscript_cond_keys + (_actionscript_cond_offsets[cs]*2);
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
				switch ( _actionscript_cond_spaces[_actionscript_cond_offsets[cs] + ((_mid - _keys)>>1)] ) {
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

	_keys = _actionscript_trans_keys + _actionscript_key_offsets[cs];
	_trans = _actionscript_index_offsets[cs];

	_klen = _actionscript_single_lengths[cs];
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

	_klen = _actionscript_range_lengths[cs];
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
	_trans = _actionscript_indicies[_trans];
_eof_trans:
	cs = _actionscript_trans_targs[_trans];

	if ( _actionscript_trans_actions[_trans] == 0 )
		goto _again;

	_acts = _actionscript_actions + _actionscript_trans_actions[_trans];
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
#line 31 "actionscript.rl"
	{
    switch(entity) {
    case AS_SPACE:
      ls
      break;
    case AS_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(AS_LANG)
      break;
    case NEWLINE:
      std_newline(AS_LANG)
    }
  }
	break;
	case 3:
#line 50 "actionscript.rl"
	{ entity = INTERNAL_NL; }
	break;
	case 4:
#line 61 "actionscript.rl"
	{ entity = INTERNAL_NL; }
	break;
	case 5:
#line 70 "actionscript.rl"
	{ entity = AS_SPACE; }
	break;
	case 6:
#line 73 "actionscript.rl"
	{ entity = NEWLINE;  }
	break;
	case 7:
#line 74 "actionscript.rl"
	{ entity = AS_ANY;   }
	break;
	case 8:
#line 88 "actionscript.rl"
	{ entity = AS_SPACE;   }
	break;
	case 9:
#line 89 "actionscript.rl"
	{ entity = AS_COMMENT; }
	break;
	case 12:
#line 1 "NONE"
	{te = p+1;}
	break;
	case 13:
#line 71 "actionscript.rl"
	{te = p+1;}
	break;
	case 14:
#line 72 "actionscript.rl"
	{te = p+1;}
	break;
	case 15:
#line 31 "actionscript.rl"
	{te = p+1;{
    switch(entity) {
    case AS_SPACE:
      ls
      break;
    case AS_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(AS_LANG)
      break;
    case NEWLINE:
      std_newline(AS_LANG)
    }
  }}
	break;
	case 16:
#line 31 "actionscript.rl"
	{te = p+1;{
    switch(entity) {
    case AS_SPACE:
      ls
      break;
    case AS_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(AS_LANG)
      break;
    case NEWLINE:
      std_newline(AS_LANG)
    }
  }}
	break;
	case 17:
#line 31 "actionscript.rl"
	{te = p;p--;{
    switch(entity) {
    case AS_SPACE:
      ls
      break;
    case AS_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(AS_LANG)
      break;
    case NEWLINE:
      std_newline(AS_LANG)
    }
  }}
	break;
	case 18:
#line 71 "actionscript.rl"
	{te = p;p--;}
	break;
	case 19:
#line 31 "actionscript.rl"
	{te = p;p--;{
    switch(entity) {
    case AS_SPACE:
      ls
      break;
    case AS_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(AS_LANG)
      break;
    case NEWLINE:
      std_newline(AS_LANG)
    }
  }}
	break;
	case 20:
#line 31 "actionscript.rl"
	{te = p;p--;{
    switch(entity) {
    case AS_SPACE:
      ls
      break;
    case AS_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(AS_LANG)
      break;
    case NEWLINE:
      std_newline(AS_LANG)
    }
  }}
	break;
	case 21:
#line 31 "actionscript.rl"
	{{p = ((te))-1;}{
    switch(entity) {
    case AS_SPACE:
      ls
      break;
    case AS_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(AS_LANG)
      break;
    case NEWLINE:
      std_newline(AS_LANG)
    }
  }}
	break;
	case 22:
#line 79 "actionscript.rl"
	{te = p+1;{
    callback(AS_LANG, as_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 23:
#line 91 "actionscript.rl"
	{te = p+1;}
	break;
	case 24:
#line 79 "actionscript.rl"
	{te = p;p--;{
    callback(AS_LANG, as_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 25:
#line 79 "actionscript.rl"
	{te = p;p--;{
    callback(AS_LANG, as_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 26:
#line 91 "actionscript.rl"
	{te = p;p--;}
	break;
	case 27:
#line 91 "actionscript.rl"
	{{p = ((te))-1;}}
	break;
#line 572 "actionscript.h"
		}
	}

_again:
	_acts = _actionscript_actions + _actionscript_to_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 10:
#line 1 "NONE"
	{ts = 0;}
	break;
#line 585 "actionscript.h"
		}
	}

	if ( cs == 0 )
		goto _out;
	if ( ++p != pe )
		goto _resume;
	_test_eof: {}
	if ( p == eof )
	{
	if ( _actionscript_eof_trans[cs] > 0 ) {
		_trans = _actionscript_eof_trans[cs] - 1;
		goto _eof_trans;
	}
	}

	_out: {}
	}

#line 118 "actionscript.rl"

  // if no newline at EOF; callback contents of last line
  if (count) { process_last_line(AS_LANG) }
}

#endif

/*****************************************************************************/
