
#line 1 "autoconf.rl"
// autoconf.rl written by Mitchell Foral. mitchell<att>caladbolg<dott>net.

/************************* Required for every parser *************************/
#ifndef OHCOUNT_AUTOCONF_PARSER_H
#define OHCOUNT_AUTOCONF_PARSER_H

#include "../parser_macros.h"

// the name of the language
const char *AC_LANG = LANG_AUTOCONF;

// the languages entities
const char *ac_entities[] = {
  "space", "comment", "string", "any"
};

// constants associated with the entities
enum {
  AC_SPACE = 0, AC_COMMENT, AC_STRING, AC_ANY
};

/*****************************************************************************/


#line 28 "autoconf.h"
static const char _autoconf_actions[] = {
	0, 1, 0, 1, 7, 1, 8, 1, 
	10, 1, 11, 1, 12, 1, 13, 1, 
	15, 1, 18, 1, 19, 1, 20, 1, 
	21, 1, 22, 1, 23, 1, 24, 1, 
	25, 1, 26, 1, 27, 1, 28, 2, 
	4, 0, 2, 5, 0, 2, 6, 2, 
	2, 8, 16, 2, 9, 17, 2, 14, 
	1, 2, 14, 9, 2, 14, 11, 3, 
	6, 2, 0, 3, 6, 2, 15, 4, 
	6, 2, 4, 0, 4, 6, 2, 5, 
	0, 4, 14, 3, 0, 9
};

static const char _autoconf_cond_offsets[] = {
	0, 0, 0, 0, 2, 4, 4, 4, 
	4, 4, 4, 4, 4, 4, 5, 5, 
	7, 7, 7, 7
};

static const char _autoconf_cond_lengths[] = {
	0, 0, 0, 2, 2, 0, 0, 0, 
	0, 0, 0, 0, 0, 1, 0, 2, 
	0, 0, 0, 0
};

static const short _autoconf_cond_keys[] = {
	13, 13, 93, 93, 13, 13, 93, 93, 
	13, 13, 13, 13, 93, 93, 0
};

static const char _autoconf_cond_spaces[] = {
	0, 1, 0, 1, 0, 0, 1, 0
};

static const char _autoconf_key_offsets[] = {
	0, 0, 1, 3, 18, 33, 34, 35, 
	38, 39, 43, 46, 47, 50, 62, 64, 
	79, 80, 82, 85
};

static const short _autoconf_trans_keys[] = {
	108, 9, 32, 9, 10, 12, 32, 91, 
	269, 525, 861, 1117, 0, 11, 14, 92, 
	94, 255, 9, 10, 12, 32, 91, 269, 
	525, 861, 1117, 0, 11, 14, 92, 94, 
	255, 10, 108, 10, 12, 13, 10, 32, 
	100, 9, 13, 32, 9, 13, 110, 10, 
	12, 13, 9, 10, 12, 32, 91, 100, 
	269, 525, 0, 8, 14, 255, 9, 32, 
	9, 10, 12, 32, 91, 269, 525, 861, 
	1117, 0, 11, 14, 92, 94, 255, 110, 
	9, 32, 10, 12, 13, 10, 0
};

static const char _autoconf_single_lengths[] = {
	0, 1, 2, 9, 9, 1, 1, 1, 
	1, 2, 1, 1, 1, 8, 2, 9, 
	1, 2, 1, 1
};

static const char _autoconf_range_lengths[] = {
	0, 0, 0, 3, 3, 0, 0, 1, 
	0, 1, 1, 0, 1, 2, 0, 3, 
	0, 0, 1, 0
};

static const char _autoconf_index_offsets[] = {
	0, 0, 2, 5, 18, 31, 33, 35, 
	38, 40, 44, 47, 49, 52, 63, 66, 
	79, 81, 84, 87
};

static const char _autoconf_indicies[] = {
	1, 0, 2, 2, 0, 5, 6, 6, 
	5, 7, 8, 6, 9, 10, 4, 4, 
	4, 3, 12, 13, 13, 12, 14, 15, 
	13, 16, 17, 11, 11, 11, 3, 6, 
	3, 18, 3, 19, 19, 20, 21, 22, 
	24, 25, 24, 23, 24, 24, 26, 28, 
	27, 29, 29, 2, 31, 21, 21, 31, 
	32, 33, 34, 35, 30, 30, 22, 31, 
	31, 36, 5, 6, 6, 5, 7, 8, 
	6, 9, 10, 4, 4, 4, 37, 38, 
	37, 40, 40, 39, 39, 39, 20, 21, 
	41, 0
};

static const char _autoconf_trans_targs[] = {
	9, 2, 12, 13, 3, 3, 4, 3, 
	5, 3, 13, 3, 3, 4, 3, 5, 
	3, 13, 17, 13, 18, 13, 0, 9, 
	10, 11, 9, 9, 1, 9, 13, 14, 
	15, 16, 8, 19, 13, 13, 6, 13, 
	7, 13
};

static const char _autoconf_trans_actions[] = {
	37, 9, 9, 27, 1, 0, 0, 39, 
	0, 42, 15, 63, 45, 45, 71, 45, 
	76, 67, 54, 25, 0, 48, 0, 29, 
	7, 60, 31, 35, 9, 33, 51, 3, 
	81, 57, 5, 5, 17, 23, 0, 19, 
	0, 21
};

static const char _autoconf_to_state_actions[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 11, 0, 0, 0, 11, 0, 0, 
	0, 0, 0, 0
};

static const char _autoconf_from_state_actions[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 13, 0, 0, 0, 13, 0, 0, 
	0, 0, 0, 0
};

static const char _autoconf_eof_trans[] = {
	0, 1, 1, 4, 4, 4, 4, 20, 
	0, 0, 27, 28, 30, 0, 37, 38, 
	38, 40, 40, 42
};

static const int autoconf_start = 9;
static const int autoconf_first_final = 9;
static const int autoconf_error = 0;

static const int autoconf_en_ac_line = 13;
static const int autoconf_en_ac_entity = 9;


#line 88 "autoconf.rl"


/************************* Required for every parser *************************/

/* Parses a string buffer with Autoconf code.
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
void parse_autoconf(char *buffer, int length, int count,
                    void (*callback) (const char *lang, const char *entity,
                                      int s, int e, void *udata),
                    void *userdata
  ) {
  init

  int nest_count = 0;

  
#line 187 "autoconf.h"
	{
	cs = autoconf_start;
	ts = 0;
	te = 0;
	act = 0;
	}

#line 113 "autoconf.rl"
  cs = (count) ? autoconf_en_ac_line : autoconf_en_ac_entity;
  
#line 198 "autoconf.h"
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
	_acts = _autoconf_actions + _autoconf_from_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 13:
#line 1 "NONE"
	{ts = p;}
	break;
#line 220 "autoconf.h"
		}
	}

	_widec = (*p);
	_klen = _autoconf_cond_lengths[cs];
	_keys = _autoconf_cond_keys + (_autoconf_cond_offsets[cs]*2);
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
				switch ( _autoconf_cond_spaces[_autoconf_cond_offsets[cs] + ((_mid - _keys)>>1)] ) {
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
#line 64 "autoconf.rl"
 nest_count == 0  ) _widec += 256;
		break;
	}
				}
				break;
			}
		}
	}

	_keys = _autoconf_trans_keys + _autoconf_key_offsets[cs];
	_trans = _autoconf_index_offsets[cs];

	_klen = _autoconf_single_lengths[cs];
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

	_klen = _autoconf_range_lengths[cs];
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
	_trans = _autoconf_indicies[_trans];
_eof_trans:
	cs = _autoconf_trans_targs[_trans];

	if ( _autoconf_trans_actions[_trans] == 0 )
		goto _again;

	_acts = _autoconf_actions + _autoconf_trans_actions[_trans];
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
#line 31 "autoconf.rl"
	{
    switch(entity) {
    case AC_SPACE:
      ls
      break;
    case AC_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(AC_LANG)
      break;
    case NEWLINE:
      std_newline(AC_LANG)
    }
  }
	break;
	case 3:
#line 47 "autoconf.rl"
	{ nest_count = 0; }
	break;
	case 4:
#line 48 "autoconf.rl"
	{ nest_count++; }
	break;
	case 5:
#line 49 "autoconf.rl"
	{ nest_count--; }
	break;
	case 6:
#line 55 "autoconf.rl"
	{ entity = INTERNAL_NL; }
	break;
	case 7:
#line 67 "autoconf.rl"
	{ entity = AC_SPACE; }
	break;
	case 8:
#line 70 "autoconf.rl"
	{ entity = NEWLINE;  }
	break;
	case 9:
#line 71 "autoconf.rl"
	{ entity = AC_ANY;   }
	break;
	case 10:
#line 83 "autoconf.rl"
	{ entity = AC_SPACE;   }
	break;
	case 11:
#line 84 "autoconf.rl"
	{ entity = AC_COMMENT; }
	break;
	case 14:
#line 1 "NONE"
	{te = p+1;}
	break;
	case 15:
#line 69 "autoconf.rl"
	{te = p+1;}
	break;
	case 16:
#line 31 "autoconf.rl"
	{te = p+1;{
    switch(entity) {
    case AC_SPACE:
      ls
      break;
    case AC_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(AC_LANG)
      break;
    case NEWLINE:
      std_newline(AC_LANG)
    }
  }}
	break;
	case 17:
#line 31 "autoconf.rl"
	{te = p+1;{
    switch(entity) {
    case AC_SPACE:
      ls
      break;
    case AC_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(AC_LANG)
      break;
    case NEWLINE:
      std_newline(AC_LANG)
    }
  }}
	break;
	case 18:
#line 31 "autoconf.rl"
	{te = p;p--;{
    switch(entity) {
    case AC_SPACE:
      ls
      break;
    case AC_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(AC_LANG)
      break;
    case NEWLINE:
      std_newline(AC_LANG)
    }
  }}
	break;
	case 19:
#line 68 "autoconf.rl"
	{te = p;p--;}
	break;
	case 20:
#line 31 "autoconf.rl"
	{te = p;p--;{
    switch(entity) {
    case AC_SPACE:
      ls
      break;
    case AC_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(AC_LANG)
      break;
    case NEWLINE:
      std_newline(AC_LANG)
    }
  }}
	break;
	case 21:
#line 31 "autoconf.rl"
	{te = p;p--;{
    switch(entity) {
    case AC_SPACE:
      ls
      break;
    case AC_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(AC_LANG)
      break;
    case NEWLINE:
      std_newline(AC_LANG)
    }
  }}
	break;
	case 22:
#line 68 "autoconf.rl"
	{{p = ((te))-1;}}
	break;
	case 23:
#line 31 "autoconf.rl"
	{{p = ((te))-1;}{
    switch(entity) {
    case AC_SPACE:
      ls
      break;
    case AC_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(AC_LANG)
      break;
    case NEWLINE:
      std_newline(AC_LANG)
    }
  }}
	break;
	case 24:
#line 86 "autoconf.rl"
	{te = p+1;}
	break;
	case 25:
#line 76 "autoconf.rl"
	{te = p;p--;{
    callback(AC_LANG, ac_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 26:
#line 76 "autoconf.rl"
	{te = p;p--;{
    callback(AC_LANG, ac_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 27:
#line 86 "autoconf.rl"
	{te = p;p--;}
	break;
	case 28:
#line 86 "autoconf.rl"
	{{p = ((te))-1;}}
	break;
#line 542 "autoconf.h"
		}
	}

_again:
	_acts = _autoconf_actions + _autoconf_to_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 12:
#line 1 "NONE"
	{ts = 0;}
	break;
#line 555 "autoconf.h"
		}
	}

	if ( cs == 0 )
		goto _out;
	if ( ++p != pe )
		goto _resume;
	_test_eof: {}
	if ( p == eof )
	{
	if ( _autoconf_eof_trans[cs] > 0 ) {
		_trans = _autoconf_eof_trans[cs] - 1;
		goto _eof_trans;
	}
	}

	_out: {}
	}

#line 115 "autoconf.rl"

  // if no newline at EOF; callback contents of last line
  if (count) { process_last_line(AC_LANG) }
}

#endif

/*****************************************************************************/
