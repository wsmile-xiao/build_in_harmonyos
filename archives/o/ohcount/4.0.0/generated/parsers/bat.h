
#line 1 "bat.rl"
// bat.rl written by Mitchell Foral. mitchell<att>caladbolg<dott>net

/************************* Required for every parser *************************/
#ifndef OHCOUNT_BAT_PARSER_H
#define OHCOUNT_BAT_PARSER_H

#include "../parser_macros.h"

// the name of the language
const char *BAT_LANG = LANG_BAT;

// the languages entities
const char *bat_entities[] = {
  "space", "comment", "string", "any"
};

// constants associated with the entities
enum {
  BAT_SPACE = 0, BAT_COMMENT, BAT_STRING, BAT_ANY
};

/*****************************************************************************/


#line 28 "bat.h"
static const char _bat_actions[] = {
	0, 1, 0, 1, 1, 1, 2, 1, 
	3, 1, 4, 1, 5, 1, 6, 1, 
	7, 1, 11, 1, 12, 1, 13, 1, 
	14, 1, 15, 1, 16, 1, 17, 1, 
	18, 1, 19, 1, 20, 2, 2, 9, 
	2, 3, 10, 2, 8, 3, 2, 8, 
	5
};

static const char _bat_cond_offsets[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 1, 1, 1, 
	1, 1, 1
};

static const char _bat_cond_lengths[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 1, 0, 0, 0, 
	0, 0, 0
};

static const short _bat_cond_keys[] = {
	13, 13, 0
};

static const char _bat_cond_spaces[] = {
	0, 0
};

static const char _bat_key_offsets[] = {
	0, 0, 2, 4, 6, 8, 9, 16, 
	19, 20, 23, 25, 27, 41, 43, 44, 
	47, 49, 51
};

static const short _bat_trans_keys[] = {
	69, 101, 77, 109, 69, 101, 77, 109, 
	10, 32, 58, 64, 82, 114, 9, 13, 
	32, 9, 13, 58, 10, 12, 13, 82, 
	114, 69, 101, 9, 10, 12, 32, 58, 
	64, 82, 114, 269, 525, 0, 8, 14, 
	255, 9, 32, 58, 10, 12, 13, 82, 
	114, 69, 101, 10, 0
};

static const char _bat_single_lengths[] = {
	0, 2, 2, 2, 2, 1, 5, 1, 
	1, 1, 2, 2, 10, 2, 1, 1, 
	2, 2, 1
};

static const char _bat_range_lengths[] = {
	0, 0, 0, 0, 0, 0, 1, 1, 
	0, 1, 0, 0, 2, 0, 0, 1, 
	0, 0, 0
};

static const char _bat_index_offsets[] = {
	0, 0, 3, 6, 9, 12, 14, 21, 
	24, 26, 29, 32, 35, 48, 51, 53, 
	56, 59, 62
};

static const char _bat_indicies[] = {
	1, 1, 0, 2, 2, 0, 4, 4, 
	3, 5, 5, 3, 6, 7, 9, 10, 
	11, 12, 12, 9, 8, 9, 9, 13, 
	2, 14, 15, 15, 2, 16, 16, 14, 
	1, 1, 14, 18, 6, 6, 18, 19, 
	20, 21, 21, 22, 23, 17, 17, 7, 
	18, 18, 24, 5, 25, 26, 26, 27, 
	28, 28, 25, 4, 4, 25, 6, 29, 
	0
};

static const char _bat_trans_targs[] = {
	6, 2, 9, 12, 4, 15, 12, 0, 
	6, 7, 8, 10, 11, 6, 6, 6, 
	1, 12, 13, 14, 16, 17, 5, 18, 
	12, 12, 12, 15, 3, 12
};

static const char _bat_trans_actions[] = {
	35, 11, 11, 25, 0, 1, 37, 0, 
	27, 9, 11, 46, 46, 29, 33, 31, 
	11, 40, 3, 7, 43, 43, 5, 5, 
	17, 23, 19, 0, 0, 21
};

static const char _bat_to_state_actions[] = {
	0, 0, 0, 0, 0, 0, 13, 0, 
	0, 0, 0, 0, 13, 0, 0, 0, 
	0, 0, 0
};

static const char _bat_from_state_actions[] = {
	0, 0, 0, 0, 0, 0, 15, 0, 
	0, 0, 0, 0, 15, 0, 0, 0, 
	0, 0, 0
};

static const char _bat_eof_trans[] = {
	0, 1, 1, 4, 4, 0, 0, 14, 
	15, 16, 15, 15, 0, 25, 26, 27, 
	26, 26, 30
};

static const int bat_start = 6;
static const int bat_first_final = 6;
static const int bat_error = 0;

static const int bat_en_bat_line = 12;
static const int bat_en_bat_entity = 6;


#line 70 "bat.rl"


/************************* Required for every parser *************************/

/* Parses a string buffer with Batch code.
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
void parse_bat(char *buffer, int length, int count,
               void (*callback) (const char *lang, const char *entity, int s,
                                 int e, void *udata),
               void *userdata
  ) {
  init

  
#line 169 "bat.h"
	{
	cs = bat_start;
	ts = 0;
	te = 0;
	act = 0;
	}

#line 93 "bat.rl"
  cs = (count) ? bat_en_bat_line : bat_en_bat_entity;
  
#line 180 "bat.h"
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
	_acts = _bat_actions + _bat_from_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 7:
#line 1 "NONE"
	{ts = p;}
	break;
#line 202 "bat.h"
		}
	}

	_widec = (*p);
	_klen = _bat_cond_lengths[cs];
	_keys = _bat_cond_keys + (_bat_cond_offsets[cs]*2);
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
				switch ( _bat_cond_spaces[_bat_cond_offsets[cs] + ((_mid - _keys)>>1)] ) {
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

	_keys = _bat_trans_keys + _bat_key_offsets[cs];
	_trans = _bat_index_offsets[cs];

	_klen = _bat_single_lengths[cs];
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

	_klen = _bat_range_lengths[cs];
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
	_trans = _bat_indicies[_trans];
_eof_trans:
	cs = _bat_trans_targs[_trans];

	if ( _bat_trans_actions[_trans] == 0 )
		goto _again;

	_acts = _bat_actions + _bat_trans_actions[_trans];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 )
	{
		switch ( *_acts++ )
		{
	case 0:
#line 58 "common.rl"
	{
  if (!line_contains_code) {
    whole_line_comment = 1;
    if (!line_start) line_start = ts;
  }
}
	break;
	case 1:
#line 50 "bat.rl"
	{ entity = BAT_SPACE; }
	break;
	case 2:
#line 52 "bat.rl"
	{ entity = NEWLINE;   }
	break;
	case 3:
#line 53 "bat.rl"
	{ entity = BAT_ANY;   }
	break;
	case 4:
#line 65 "bat.rl"
	{ entity = BAT_SPACE;   }
	break;
	case 5:
#line 66 "bat.rl"
	{ entity = BAT_COMMENT; }
	break;
	case 8:
#line 1 "NONE"
	{te = p+1;}
	break;
	case 9:
#line 31 "bat.rl"
	{te = p+1;{
    switch(entity) {
    case BAT_SPACE:
      ls
      break;
    case BAT_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(BAT_LANG)
      break;
    case NEWLINE:
      std_newline(BAT_LANG)
    }
  }}
	break;
	case 10:
#line 31 "bat.rl"
	{te = p+1;{
    switch(entity) {
    case BAT_SPACE:
      ls
      break;
    case BAT_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(BAT_LANG)
      break;
    case NEWLINE:
      std_newline(BAT_LANG)
    }
  }}
	break;
	case 11:
#line 31 "bat.rl"
	{te = p;p--;{
    switch(entity) {
    case BAT_SPACE:
      ls
      break;
    case BAT_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(BAT_LANG)
      break;
    case NEWLINE:
      std_newline(BAT_LANG)
    }
  }}
	break;
	case 12:
#line 51 "bat.rl"
	{te = p;p--;}
	break;
	case 13:
#line 31 "bat.rl"
	{te = p;p--;{
    switch(entity) {
    case BAT_SPACE:
      ls
      break;
    case BAT_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(BAT_LANG)
      break;
    case NEWLINE:
      std_newline(BAT_LANG)
    }
  }}
	break;
	case 14:
#line 31 "bat.rl"
	{te = p;p--;{
    switch(entity) {
    case BAT_SPACE:
      ls
      break;
    case BAT_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(BAT_LANG)
      break;
    case NEWLINE:
      std_newline(BAT_LANG)
    }
  }}
	break;
	case 15:
#line 31 "bat.rl"
	{{p = ((te))-1;}{
    switch(entity) {
    case BAT_SPACE:
      ls
      break;
    case BAT_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(BAT_LANG)
      break;
    case NEWLINE:
      std_newline(BAT_LANG)
    }
  }}
	break;
	case 16:
#line 68 "bat.rl"
	{te = p+1;}
	break;
	case 17:
#line 58 "bat.rl"
	{te = p;p--;{
    callback(BAT_LANG, bat_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 18:
#line 58 "bat.rl"
	{te = p;p--;{
    callback(BAT_LANG, bat_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 19:
#line 68 "bat.rl"
	{te = p;p--;}
	break;
	case 20:
#line 68 "bat.rl"
	{{p = ((te))-1;}}
	break;
#line 468 "bat.h"
		}
	}

_again:
	_acts = _bat_actions + _bat_to_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 6:
#line 1 "NONE"
	{ts = 0;}
	break;
#line 481 "bat.h"
		}
	}

	if ( cs == 0 )
		goto _out;
	if ( ++p != pe )
		goto _resume;
	_test_eof: {}
	if ( p == eof )
	{
	if ( _bat_eof_trans[cs] > 0 ) {
		_trans = _bat_eof_trans[cs] - 1;
		goto _eof_trans;
	}
	}

	_out: {}
	}

#line 95 "bat.rl"

  // if no newline at EOF; callback contents of last line
  if (count) { process_last_line(BAT_LANG) }
}

#endif

/*****************************************************************************/
