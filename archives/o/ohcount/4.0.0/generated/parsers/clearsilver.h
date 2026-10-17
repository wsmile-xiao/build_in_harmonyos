
#line 1 "clearsilver.rl"
// clearsilver.rl written by Mitchell Foral. mitchell<att>caladbolg<dott>net.

/************************* Required for every parser *************************/
#ifndef OHCOUNT_CS_PARSER_H
#define OHCOUNT_CS_PARSER_H

#include "../parser_macros.h"

// the name of the language
const char *CS_LANG = LANG_CLEARSILVER;

// the languages entities
const char *cs_entities[] = {
  "space", "comment", "string", "any"
};

// constants associated with the entities
enum {
  CS_SPACE = 0, CS_COMMENT, CS_STRING, CS_ANY
};

/*****************************************************************************/


#line 28 "clearsilver.h"
static const char _clearsilver_actions[] = {
	0, 1, 2, 1, 3, 1, 5, 1, 
	6, 1, 7, 1, 8, 1, 10, 1, 
	13, 1, 14, 1, 15, 1, 16, 1, 
	17, 1, 18, 1, 19, 1, 20, 2, 
	1, 4, 2, 3, 11, 2, 4, 12, 
	3, 9, 0, 4
};

static const char _clearsilver_cond_offsets[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	1, 1, 1, 1
};

static const char _clearsilver_cond_lengths[] = {
	0, 0, 0, 0, 0, 0, 0, 1, 
	0, 0, 0, 0
};

static const short _clearsilver_cond_keys[] = {
	13, 13, 0
};

static const char _clearsilver_cond_spaces[] = {
	0, 0
};

static const char _clearsilver_key_offsets[] = {
	0, 0, 5, 8, 9, 13, 16, 19, 
	31, 33, 38, 41
};

static const short _clearsilver_trans_keys[] = {
	10, 34, 92, 12, 13, 10, 12, 13, 
	10, 32, 35, 9, 13, 32, 9, 13, 
	10, 12, 13, 9, 10, 12, 32, 34, 
	35, 269, 525, 0, 8, 14, 255, 9, 
	32, 10, 34, 92, 12, 13, 10, 12, 
	13, 10, 0
};

static const char _clearsilver_single_lengths[] = {
	0, 3, 1, 1, 2, 1, 1, 8, 
	2, 3, 1, 1
};

static const char _clearsilver_range_lengths[] = {
	0, 1, 1, 0, 1, 1, 1, 2, 
	0, 1, 1, 0
};

static const char _clearsilver_index_offsets[] = {
	0, 0, 5, 8, 10, 14, 17, 20, 
	31, 34, 39, 42
};

static const char _clearsilver_trans_targs[] = {
	7, 7, 2, 7, 1, 7, 7, 1, 
	7, 0, 5, 6, 5, 4, 5, 5, 
	4, 4, 4, 6, 8, 7, 7, 8, 
	9, 10, 3, 11, 7, 7, 0, 8, 
	8, 7, 7, 7, 2, 7, 1, 7, 
	7, 10, 7, 7, 7, 7, 4, 4, 
	7, 7, 7, 7, 0
};

static const char _clearsilver_trans_actions[] = {
	23, 13, 0, 23, 0, 23, 23, 0, 
	34, 0, 5, 7, 5, 25, 5, 5, 
	27, 29, 29, 7, 1, 34, 34, 1, 
	40, 31, 3, 3, 37, 37, 0, 1, 
	1, 15, 21, 13, 0, 21, 0, 17, 
	17, 0, 34, 19, 23, 23, 27, 29, 
	15, 21, 17, 19, 0
};

static const char _clearsilver_to_state_actions[] = {
	0, 0, 0, 0, 9, 0, 0, 9, 
	0, 0, 0, 0
};

static const char _clearsilver_from_state_actions[] = {
	0, 0, 0, 0, 11, 0, 0, 11, 
	0, 0, 0, 0
};

static const char _clearsilver_eof_trans[] = {
	0, 46, 46, 0, 0, 47, 48, 0, 
	49, 50, 51, 52
};

static const int clearsilver_start = 4;
static const int clearsilver_first_final = 4;
static const int clearsilver_error = 0;

static const int clearsilver_en_cs_line = 7;
static const int clearsilver_en_cs_entity = 4;


#line 73 "clearsilver.rl"


/************************* Required for every parser *************************/

/* Parses a string buffer with Clearsilver code (not in HTML).
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
void parse_clearsilver(char *buffer, int length, int count,
                       void (*callback) (const char *lang, const char *entity,
                                         int s, int e, void *udata),
                       void *userdata
  ) {
  init

  
#line 152 "clearsilver.h"
	{
	cs = clearsilver_start;
	ts = 0;
	te = 0;
	act = 0;
	}

#line 96 "clearsilver.rl"
  cs = (count) ? clearsilver_en_cs_line : clearsilver_en_cs_entity;
  
#line 163 "clearsilver.h"
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
	_acts = _clearsilver_actions + _clearsilver_from_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 8:
#line 1 "NONE"
	{ts = p;}
	break;
#line 185 "clearsilver.h"
		}
	}

	_widec = (*p);
	_klen = _clearsilver_cond_lengths[cs];
	_keys = _clearsilver_cond_keys + (_clearsilver_cond_offsets[cs]*2);
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
				switch ( _clearsilver_cond_spaces[_clearsilver_cond_offsets[cs] + ((_mid - _keys)>>1)] ) {
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

	_keys = _clearsilver_trans_keys + _clearsilver_key_offsets[cs];
	_trans = _clearsilver_index_offsets[cs];

	_klen = _clearsilver_single_lengths[cs];
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

	_klen = _clearsilver_range_lengths[cs];
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
_eof_trans:
	cs = _clearsilver_trans_targs[_trans];

	if ( _clearsilver_trans_actions[_trans] == 0 )
		goto _again;

	_acts = _clearsilver_actions + _clearsilver_trans_actions[_trans];
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
#line 52 "clearsilver.rl"
	{ entity = CS_SPACE; }
	break;
	case 3:
#line 55 "clearsilver.rl"
	{ entity = NEWLINE;  }
	break;
	case 4:
#line 56 "clearsilver.rl"
	{ entity = CS_ANY;   }
	break;
	case 5:
#line 68 "clearsilver.rl"
	{ entity = CS_SPACE;   }
	break;
	case 6:
#line 69 "clearsilver.rl"
	{ entity = CS_COMMENT; }
	break;
	case 9:
#line 1 "NONE"
	{te = p+1;}
	break;
	case 10:
#line 54 "clearsilver.rl"
	{te = p+1;}
	break;
	case 11:
#line 31 "clearsilver.rl"
	{te = p+1;{
    switch(entity) {
    case CS_SPACE:
      ls
      break;
    case CS_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(CS_LANG)
      break;
    case NEWLINE:
      std_newline(CS_LANG)
    }
  }}
	break;
	case 12:
#line 31 "clearsilver.rl"
	{te = p+1;{
    switch(entity) {
    case CS_SPACE:
      ls
      break;
    case CS_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(CS_LANG)
      break;
    case NEWLINE:
      std_newline(CS_LANG)
    }
  }}
	break;
	case 13:
#line 31 "clearsilver.rl"
	{te = p;p--;{
    switch(entity) {
    case CS_SPACE:
      ls
      break;
    case CS_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(CS_LANG)
      break;
    case NEWLINE:
      std_newline(CS_LANG)
    }
  }}
	break;
	case 14:
#line 53 "clearsilver.rl"
	{te = p;p--;}
	break;
	case 15:
#line 31 "clearsilver.rl"
	{te = p;p--;{
    switch(entity) {
    case CS_SPACE:
      ls
      break;
    case CS_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(CS_LANG)
      break;
    case NEWLINE:
      std_newline(CS_LANG)
    }
  }}
	break;
	case 16:
#line 31 "clearsilver.rl"
	{te = p;p--;{
    switch(entity) {
    case CS_SPACE:
      ls
      break;
    case CS_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(CS_LANG)
      break;
    case NEWLINE:
      std_newline(CS_LANG)
    }
  }}
	break;
	case 17:
#line 31 "clearsilver.rl"
	{{p = ((te))-1;}{
    switch(entity) {
    case CS_SPACE:
      ls
      break;
    case CS_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(CS_LANG)
      break;
    case NEWLINE:
      std_newline(CS_LANG)
    }
  }}
	break;
	case 18:
#line 71 "clearsilver.rl"
	{te = p+1;}
	break;
	case 19:
#line 61 "clearsilver.rl"
	{te = p;p--;{
    callback(CS_LANG, cs_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 20:
#line 61 "clearsilver.rl"
	{te = p;p--;{
    callback(CS_LANG, cs_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
#line 453 "clearsilver.h"
		}
	}

_again:
	_acts = _clearsilver_actions + _clearsilver_to_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 7:
#line 1 "NONE"
	{ts = 0;}
	break;
#line 466 "clearsilver.h"
		}
	}

	if ( cs == 0 )
		goto _out;
	if ( ++p != pe )
		goto _resume;
	_test_eof: {}
	if ( p == eof )
	{
	if ( _clearsilver_eof_trans[cs] > 0 ) {
		_trans = _clearsilver_eof_trans[cs] - 1;
		goto _eof_trans;
	}
	}

	_out: {}
	}

#line 98 "clearsilver.rl"

  // if no newline at EOF; callback contents of last line
  if (count) { process_last_line(CS_LANG) }
}

#endif

/*****************************************************************************/
