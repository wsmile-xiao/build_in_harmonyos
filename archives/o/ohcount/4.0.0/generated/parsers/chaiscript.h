
#line 1 "chaiscript.rl"
// Chaiscript.rl written by Jason Turner. lefticus<att>gmail<dott>com
// based on Javascript.rl written by Mitchell Foral. mitchell<att>caladbolg<dott>net.

/************************* Required for every parser *************************/
#ifndef OHCOUNT_CHAISCRIPT_PARSER_H
#define OHCOUNT_CHAISCRIPT_PARSER_H

#include "../parser_macros.h"

// the name of the language
const char *CHAI_LANG = LANG_CHAISCRIPT;

// the languages entities
const char *chai_entities[] = {
  "space", "comment", "string", "number", "keyword",
  "identifier", "operator", "any"
};

// constants associated with the entities
enum {
  CHAI_SPACE = 0, CHAI_COMMENT, CHAI_STRING, CHAI_NUMBER, CHAI_KEYWORD,
  CHAI_IDENTIFIER, CHAI_OPERATOR, CHAI_ANY
};

/*****************************************************************************/


#line 31 "chaiscript.h"
static const char _chaiscript_actions[] = {
	0, 1, 0, 1, 1, 1, 6, 1, 
	7, 1, 9, 1, 10, 1, 11, 1, 
	12, 1, 14, 1, 15, 1, 18, 1, 
	19, 1, 20, 1, 21, 1, 22, 1, 
	24, 1, 25, 1, 26, 1, 27, 1, 
	28, 2, 0, 15, 2, 3, 2, 2, 
	4, 2, 2, 5, 2, 2, 7, 16, 
	2, 8, 17, 2, 10, 23, 2, 13, 
	8, 2, 13, 10, 3, 3, 2, 1, 
	3, 4, 2, 0, 3, 4, 2, 15, 
	3, 5, 2, 0, 3, 5, 2, 15, 
	3, 13, 0, 8
};

static const char _chaiscript_cond_offsets[] = {
	0, 0, 0, 0, 0, 1, 1, 1, 
	1, 1, 2, 2, 2, 2, 2, 2, 
	3, 4, 5, 5, 5, 5, 5, 5, 
	5, 6, 6, 6, 6, 6, 6
};

static const char _chaiscript_cond_lengths[] = {
	0, 0, 0, 0, 1, 0, 0, 0, 
	0, 1, 0, 0, 0, 0, 0, 1, 
	1, 1, 0, 0, 0, 0, 0, 0, 
	1, 0, 0, 0, 0, 0, 0
};

static const short _chaiscript_cond_keys[] = {
	13, 13, 13, 13, 13, 13, 13, 13, 
	13, 13, 13, 13, 0
};

static const char _chaiscript_cond_spaces[] = {
	0, 0, 0, 0, 0, 0, 0
};

static const char _chaiscript_key_offsets[] = {
	0, 0, 1, 3, 7, 15, 19, 20, 
	25, 29, 37, 41, 42, 47, 52, 55, 
	66, 77, 89, 90, 91, 95, 98, 100, 
	103, 116, 118, 122, 126, 128, 131
};

static const short _chaiscript_trans_keys[] = {
	42, 42, 47, 9, 32, 34, 92, 10, 
	12, 269, 525, 0, 11, 14, 255, 9, 
	32, 34, 92, 10, 9, 10, 32, 34, 
	92, 9, 32, 39, 92, 10, 12, 269, 
	525, 0, 11, 14, 255, 9, 32, 39, 
	92, 10, 9, 10, 32, 39, 92, 10, 
	47, 92, 12, 13, 10, 12, 13, 9, 
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

static const char _chaiscript_single_lengths[] = {
	0, 1, 2, 4, 4, 4, 1, 5, 
	4, 4, 4, 1, 5, 3, 1, 7, 
	7, 8, 1, 1, 2, 1, 2, 1, 
	9, 2, 4, 4, 2, 1, 1
};

static const char _chaiscript_range_lengths[] = {
	0, 0, 0, 0, 2, 0, 0, 0, 
	0, 2, 0, 0, 0, 1, 1, 2, 
	2, 2, 0, 0, 1, 1, 0, 1, 
	2, 0, 0, 0, 0, 1, 0
};

static const char _chaiscript_index_offsets[] = {
	0, 0, 2, 5, 10, 17, 22, 24, 
	30, 35, 42, 47, 49, 55, 60, 63, 
	73, 83, 94, 96, 98, 102, 105, 108, 
	111, 123, 126, 131, 136, 139, 142
};

static const char _chaiscript_indicies[] = {
	2, 1, 2, 3, 1, 6, 6, 7, 
	8, 5, 9, 9, 10, 11, 5, 5, 
	4, 13, 13, 14, 15, 12, 9, 4, 
	13, 16, 13, 14, 15, 12, 18, 18, 
	7, 19, 17, 20, 20, 21, 22, 17, 
	17, 4, 24, 24, 25, 26, 23, 20, 
	4, 24, 27, 24, 25, 26, 23, 4, 
	29, 30, 4, 28, 4, 4, 28, 32, 
	33, 33, 32, 34, 35, 33, 31, 31, 
	4, 37, 38, 38, 37, 39, 40, 38, 
	36, 36, 4, 32, 33, 33, 32, 34, 
	41, 35, 33, 31, 31, 4, 33, 4, 
	42, 43, 45, 46, 45, 44, 45, 45, 
	47, 1, 49, 48, 50, 50, 49, 52, 
	42, 42, 52, 53, 54, 55, 56, 57, 
	51, 51, 43, 52, 52, 58, 6, 6, 
	7, 8, 5, 18, 18, 7, 19, 17, 
	31, 60, 28, 61, 61, 62, 42, 63, 
	0
};

static const char _chaiscript_trans_targs[] = {
	20, 1, 2, 20, 24, 3, 3, 24, 
	4, 5, 6, 7, 3, 3, 24, 4, 
	5, 8, 8, 9, 10, 11, 12, 8, 
	8, 24, 9, 10, 13, 24, 14, 15, 
	15, 16, 17, 18, 15, 15, 16, 17, 
	18, 24, 24, 0, 20, 21, 22, 20, 
	20, 23, 20, 24, 25, 26, 27, 28, 
	19, 30, 24, 24, 29, 24, 29, 24
};

static const char _chaiscript_trans_actions[] = {
	39, 11, 11, 59, 29, 1, 0, 19, 
	0, 0, 0, 0, 80, 50, 84, 50, 
	80, 1, 0, 0, 0, 0, 0, 72, 
	47, 76, 47, 72, 0, 41, 0, 3, 
	0, 0, 3, 0, 68, 44, 44, 68, 
	44, 17, 53, 0, 31, 9, 65, 33, 
	37, 11, 35, 56, 5, 88, 88, 62, 
	7, 7, 21, 27, 3, 23, 0, 25
};

static const char _chaiscript_to_state_actions[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 13, 0, 0, 0, 
	13, 0, 0, 0, 0, 0, 0
};

static const char _chaiscript_from_state_actions[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 15, 0, 0, 0, 
	15, 0, 0, 0, 0, 0, 0
};

static const char _chaiscript_eof_trans[] = {
	0, 1, 1, 5, 5, 5, 5, 5, 
	5, 5, 5, 5, 5, 5, 5, 5, 
	5, 5, 5, 0, 0, 48, 49, 51, 
	0, 59, 60, 60, 60, 62, 64
};

static const int chaiscript_start = 20;
static const int chaiscript_first_final = 20;
static const int chaiscript_error = 0;

static const int chaiscript_en_chai_line = 24;
static const int chaiscript_en_chai_entity = 20;


#line 110 "chaiscript.rl"


/* Parses a string buffer with Chaiscript code.
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
void parse_chaiscript(char *buffer, int length, int count,
                      void (*callback) (const char *lang, const char *entity,
                                        int s, int e, void *udata),
                      void *userdata
  ) {
  init

  
#line 213 "chaiscript.h"
	{
	cs = chaiscript_start;
	ts = 0;
	te = 0;
	act = 0;
	}

#line 131 "chaiscript.rl"
  cs = (count) ? chaiscript_en_chai_line : chaiscript_en_chai_entity;
  
#line 224 "chaiscript.h"
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
	_acts = _chaiscript_actions + _chaiscript_from_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 12:
#line 1 "NONE"
	{ts = p;}
	break;
#line 246 "chaiscript.h"
		}
	}

	_widec = (*p);
	_klen = _chaiscript_cond_lengths[cs];
	_keys = _chaiscript_cond_keys + (_chaiscript_cond_offsets[cs]*2);
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
				switch ( _chaiscript_cond_spaces[_chaiscript_cond_offsets[cs] + ((_mid - _keys)>>1)] ) {
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

	_keys = _chaiscript_trans_keys + _chaiscript_key_offsets[cs];
	_trans = _chaiscript_index_offsets[cs];

	_klen = _chaiscript_single_lengths[cs];
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

	_klen = _chaiscript_range_lengths[cs];
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
	_trans = _chaiscript_indicies[_trans];
_eof_trans:
	cs = _chaiscript_trans_targs[_trans];

	if ( _chaiscript_trans_actions[_trans] == 0 )
		goto _again;

	_acts = _chaiscript_actions + _chaiscript_trans_actions[_trans];
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
#line 34 "chaiscript.rl"
	{
    switch(entity) {
    case CHAI_SPACE:
      ls
      break;
    case CHAI_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(CHAI_LANG)
      break;
    case NEWLINE:
      std_newline(CHAI_LANG)
    }
  }
	break;
	case 3:
#line 53 "chaiscript.rl"
	{ entity = INTERNAL_NL; }
	break;
	case 4:
#line 65 "chaiscript.rl"
	{ entity = INTERNAL_NL; }
	break;
	case 5:
#line 75 "chaiscript.rl"
	{ entity = INTERNAL_NL; }
	break;
	case 6:
#line 87 "chaiscript.rl"
	{ entity = CHAI_SPACE; }
	break;
	case 7:
#line 90 "chaiscript.rl"
	{ entity = NEWLINE;  }
	break;
	case 8:
#line 91 "chaiscript.rl"
	{ entity = CHAI_ANY;   }
	break;
	case 9:
#line 105 "chaiscript.rl"
	{ entity = CHAI_SPACE;   }
	break;
	case 10:
#line 106 "chaiscript.rl"
	{ entity = CHAI_COMMENT; }
	break;
	case 13:
#line 1 "NONE"
	{te = p+1;}
	break;
	case 14:
#line 88 "chaiscript.rl"
	{te = p+1;}
	break;
	case 15:
#line 89 "chaiscript.rl"
	{te = p+1;}
	break;
	case 16:
#line 34 "chaiscript.rl"
	{te = p+1;{
    switch(entity) {
    case CHAI_SPACE:
      ls
      break;
    case CHAI_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(CHAI_LANG)
      break;
    case NEWLINE:
      std_newline(CHAI_LANG)
    }
  }}
	break;
	case 17:
#line 34 "chaiscript.rl"
	{te = p+1;{
    switch(entity) {
    case CHAI_SPACE:
      ls
      break;
    case CHAI_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(CHAI_LANG)
      break;
    case NEWLINE:
      std_newline(CHAI_LANG)
    }
  }}
	break;
	case 18:
#line 34 "chaiscript.rl"
	{te = p;p--;{
    switch(entity) {
    case CHAI_SPACE:
      ls
      break;
    case CHAI_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(CHAI_LANG)
      break;
    case NEWLINE:
      std_newline(CHAI_LANG)
    }
  }}
	break;
	case 19:
#line 88 "chaiscript.rl"
	{te = p;p--;}
	break;
	case 20:
#line 34 "chaiscript.rl"
	{te = p;p--;{
    switch(entity) {
    case CHAI_SPACE:
      ls
      break;
    case CHAI_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(CHAI_LANG)
      break;
    case NEWLINE:
      std_newline(CHAI_LANG)
    }
  }}
	break;
	case 21:
#line 34 "chaiscript.rl"
	{te = p;p--;{
    switch(entity) {
    case CHAI_SPACE:
      ls
      break;
    case CHAI_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(CHAI_LANG)
      break;
    case NEWLINE:
      std_newline(CHAI_LANG)
    }
  }}
	break;
	case 22:
#line 34 "chaiscript.rl"
	{{p = ((te))-1;}{
    switch(entity) {
    case CHAI_SPACE:
      ls
      break;
    case CHAI_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(CHAI_LANG)
      break;
    case NEWLINE:
      std_newline(CHAI_LANG)
    }
  }}
	break;
	case 23:
#line 96 "chaiscript.rl"
	{te = p+1;{
    callback(CHAI_LANG, chai_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 24:
#line 108 "chaiscript.rl"
	{te = p+1;}
	break;
	case 25:
#line 96 "chaiscript.rl"
	{te = p;p--;{
    callback(CHAI_LANG, chai_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 26:
#line 96 "chaiscript.rl"
	{te = p;p--;{
    callback(CHAI_LANG, chai_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 27:
#line 108 "chaiscript.rl"
	{te = p;p--;}
	break;
	case 28:
#line 108 "chaiscript.rl"
	{{p = ((te))-1;}}
	break;
#line 563 "chaiscript.h"
		}
	}

_again:
	_acts = _chaiscript_actions + _chaiscript_to_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 11:
#line 1 "NONE"
	{ts = 0;}
	break;
#line 576 "chaiscript.h"
		}
	}

	if ( cs == 0 )
		goto _out;
	if ( ++p != pe )
		goto _resume;
	_test_eof: {}
	if ( p == eof )
	{
	if ( _chaiscript_eof_trans[cs] > 0 ) {
		_trans = _chaiscript_eof_trans[cs] - 1;
		goto _eof_trans;
	}
	}

	_out: {}
	}

#line 133 "chaiscript.rl"

  // if no newline at EOF; callback contents of last line
  if (count) { process_last_line(CHAI_LANG) }
}

#endif
