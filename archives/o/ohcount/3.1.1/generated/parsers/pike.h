
#line 1 "pike.rl"
// pike.rl written by Mitchell Foral. mitchell<att>caladbolg<dott>net.

/************************* Required for every parser *************************/
#ifndef OHCOUNT_PIKE_PARSER_H
#define OHCOUNT_PIKE_PARSER_H

#include "../parser_macros.h"

// the name of the language
const char *PIKE_LANG = LANG_PIKE;

// the languages entities
const char *pike_entities[] = {
  "space", "comment", "string", "any"
};

// constants associated with the entities
enum {
  PIKE_SPACE = 0, PIKE_COMMENT, PIKE_STRING, PIKE_ANY
};

/*****************************************************************************/


#line 28 "pike.h"
static const char _pike_actions[] = {
	0, 1, 1, 1, 4, 1, 5, 1, 
	7, 1, 8, 1, 9, 1, 10, 1, 
	12, 1, 13, 1, 16, 1, 17, 1, 
	18, 1, 19, 1, 20, 1, 22, 1, 
	23, 1, 24, 1, 25, 1, 26, 2, 
	3, 2, 2, 5, 14, 2, 6, 15, 
	2, 8, 21, 2, 11, 6, 2, 11, 
	8, 3, 3, 2, 1, 3, 11, 0, 
	6
};

static const char _pike_cond_offsets[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	1, 2, 3, 3, 3, 3, 3, 3, 
	3, 4, 4, 4, 4, 4, 4
};

static const char _pike_cond_lengths[] = {
	0, 0, 0, 0, 0, 0, 0, 1, 
	1, 1, 0, 0, 0, 0, 0, 0, 
	1, 0, 0, 0, 0, 0, 0
};

static const short _pike_cond_keys[] = {
	13, 13, 13, 13, 13, 13, 13, 13, 
	0
};

static const char _pike_cond_spaces[] = {
	0, 0, 0, 0, 0
};

static const char _pike_key_offsets[] = {
	0, 0, 1, 3, 8, 11, 16, 19, 
	30, 41, 53, 54, 55, 59, 62, 64, 
	67, 80, 82, 87, 92, 94, 97
};

static const short _pike_trans_keys[] = {
	42, 42, 47, 10, 34, 92, 12, 13, 
	10, 12, 13, 10, 39, 92, 12, 13, 
	10, 12, 13, 9, 10, 12, 32, 42, 
	269, 525, 0, 11, 14, 255, 9, 10, 
	12, 32, 42, 269, 525, 0, 11, 14, 
	255, 9, 10, 12, 32, 42, 47, 269, 
	525, 0, 11, 14, 255, 10, 10, 32, 
	47, 9, 13, 32, 9, 13, 42, 47, 
	10, 12, 13, 9, 10, 12, 32, 34, 
	39, 47, 269, 525, 0, 8, 14, 255, 
	9, 32, 10, 34, 92, 12, 13, 10, 
	39, 92, 12, 13, 42, 47, 10, 12, 
	13, 10, 0
};

static const char _pike_single_lengths[] = {
	0, 1, 2, 3, 1, 3, 1, 7, 
	7, 8, 1, 1, 2, 1, 2, 1, 
	9, 2, 3, 3, 2, 1, 1
};

static const char _pike_range_lengths[] = {
	0, 0, 0, 1, 1, 1, 1, 2, 
	2, 2, 0, 0, 1, 1, 0, 1, 
	2, 0, 1, 1, 0, 1, 0
};

static const char _pike_index_offsets[] = {
	0, 0, 2, 5, 10, 13, 18, 21, 
	31, 41, 52, 54, 56, 60, 63, 66, 
	69, 81, 84, 89, 94, 97, 100
};

static const char _pike_indicies[] = {
	2, 1, 2, 3, 1, 4, 6, 7, 
	4, 5, 4, 4, 5, 4, 6, 9, 
	4, 8, 4, 4, 8, 11, 12, 12, 
	11, 13, 14, 12, 10, 10, 4, 16, 
	17, 17, 16, 18, 19, 17, 15, 15, 
	4, 11, 12, 12, 11, 13, 20, 14, 
	12, 10, 10, 4, 12, 4, 21, 22, 
	24, 25, 24, 23, 24, 24, 26, 1, 
	28, 27, 29, 29, 28, 31, 21, 21, 
	31, 32, 33, 34, 35, 36, 30, 30, 
	22, 31, 31, 37, 38, 6, 7, 38, 
	5, 38, 6, 9, 38, 8, 10, 39, 
	38, 40, 40, 41, 21, 42, 0
};

static const char _pike_trans_targs[] = {
	12, 1, 2, 12, 16, 3, 16, 4, 
	5, 6, 7, 7, 8, 9, 10, 7, 
	7, 8, 9, 10, 16, 16, 0, 12, 
	13, 14, 12, 12, 15, 12, 16, 17, 
	18, 19, 20, 11, 22, 16, 16, 21, 
	16, 21, 16
};

static const char _pike_trans_actions[] = {
	37, 9, 9, 48, 27, 0, 17, 0, 
	0, 0, 1, 0, 0, 1, 0, 57, 
	39, 39, 57, 39, 15, 42, 0, 29, 
	7, 54, 31, 35, 9, 33, 45, 3, 
	61, 61, 51, 5, 5, 19, 25, 1, 
	21, 0, 23
};

static const char _pike_to_state_actions[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 11, 0, 0, 0, 
	11, 0, 0, 0, 0, 0, 0
};

static const char _pike_from_state_actions[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 13, 0, 0, 0, 
	13, 0, 0, 0, 0, 0, 0
};

static const char _pike_eof_trans[] = {
	0, 1, 1, 5, 5, 5, 5, 5, 
	5, 5, 5, 0, 0, 27, 28, 30, 
	0, 38, 39, 39, 39, 41, 43
};

static const int pike_start = 12;
static const int pike_first_final = 12;
static const int pike_error = 0;

static const int pike_en_pike_line = 16;
static const int pike_en_pike_entity = 12;


#line 86 "pike.rl"


/************************* Required for every parser *************************/

/* Parses a string buffer with Pike code.
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
void parse_pike(char *buffer, int length, int count,
                void (*callback) (const char *lang, const char *entity, int s,
                                  int e, void *udata),
                void *userdata
  ) {
  init

  
#line 186 "pike.h"
	{
	cs = pike_start;
	ts = 0;
	te = 0;
	act = 0;
	}

#line 109 "pike.rl"
  cs = (count) ? pike_en_pike_line : pike_en_pike_entity;
  
#line 197 "pike.h"
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
	_acts = _pike_actions + _pike_from_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 10:
#line 1 "NONE"
	{ts = p;}
	break;
#line 219 "pike.h"
		}
	}

	_widec = (*p);
	_klen = _pike_cond_lengths[cs];
	_keys = _pike_cond_keys + (_pike_cond_offsets[cs]*2);
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
				switch ( _pike_cond_spaces[_pike_cond_offsets[cs] + ((_mid - _keys)>>1)] ) {
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

	_keys = _pike_trans_keys + _pike_key_offsets[cs];
	_trans = _pike_index_offsets[cs];

	_klen = _pike_single_lengths[cs];
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

	_klen = _pike_range_lengths[cs];
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
	_trans = _pike_indicies[_trans];
_eof_trans:
	cs = _pike_trans_targs[_trans];

	if ( _pike_trans_actions[_trans] == 0 )
		goto _again;

	_acts = _pike_actions + _pike_trans_actions[_trans];
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
#line 31 "pike.rl"
	{
    switch(entity) {
    case PIKE_SPACE:
      ls
      break;
    case PIKE_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(PIKE_LANG)
      break;
    case NEWLINE:
      std_newline(PIKE_LANG)
    }
  }
	break;
	case 3:
#line 50 "pike.rl"
	{ entity = INTERNAL_NL; }
	break;
	case 4:
#line 63 "pike.rl"
	{ entity = PIKE_SPACE; }
	break;
	case 5:
#line 66 "pike.rl"
	{ entity = NEWLINE;    }
	break;
	case 6:
#line 67 "pike.rl"
	{ entity = PIKE_ANY;   }
	break;
	case 7:
#line 81 "pike.rl"
	{ entity = PIKE_SPACE;   }
	break;
	case 8:
#line 82 "pike.rl"
	{ entity = PIKE_COMMENT; }
	break;
	case 11:
#line 1 "NONE"
	{te = p+1;}
	break;
	case 12:
#line 64 "pike.rl"
	{te = p+1;}
	break;
	case 13:
#line 65 "pike.rl"
	{te = p+1;}
	break;
	case 14:
#line 31 "pike.rl"
	{te = p+1;{
    switch(entity) {
    case PIKE_SPACE:
      ls
      break;
    case PIKE_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(PIKE_LANG)
      break;
    case NEWLINE:
      std_newline(PIKE_LANG)
    }
  }}
	break;
	case 15:
#line 31 "pike.rl"
	{te = p+1;{
    switch(entity) {
    case PIKE_SPACE:
      ls
      break;
    case PIKE_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(PIKE_LANG)
      break;
    case NEWLINE:
      std_newline(PIKE_LANG)
    }
  }}
	break;
	case 16:
#line 31 "pike.rl"
	{te = p;p--;{
    switch(entity) {
    case PIKE_SPACE:
      ls
      break;
    case PIKE_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(PIKE_LANG)
      break;
    case NEWLINE:
      std_newline(PIKE_LANG)
    }
  }}
	break;
	case 17:
#line 64 "pike.rl"
	{te = p;p--;}
	break;
	case 18:
#line 31 "pike.rl"
	{te = p;p--;{
    switch(entity) {
    case PIKE_SPACE:
      ls
      break;
    case PIKE_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(PIKE_LANG)
      break;
    case NEWLINE:
      std_newline(PIKE_LANG)
    }
  }}
	break;
	case 19:
#line 31 "pike.rl"
	{te = p;p--;{
    switch(entity) {
    case PIKE_SPACE:
      ls
      break;
    case PIKE_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(PIKE_LANG)
      break;
    case NEWLINE:
      std_newline(PIKE_LANG)
    }
  }}
	break;
	case 20:
#line 31 "pike.rl"
	{{p = ((te))-1;}{
    switch(entity) {
    case PIKE_SPACE:
      ls
      break;
    case PIKE_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(PIKE_LANG)
      break;
    case NEWLINE:
      std_newline(PIKE_LANG)
    }
  }}
	break;
	case 21:
#line 72 "pike.rl"
	{te = p+1;{
    callback(PIKE_LANG, pike_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 22:
#line 84 "pike.rl"
	{te = p+1;}
	break;
	case 23:
#line 72 "pike.rl"
	{te = p;p--;{
    callback(PIKE_LANG, pike_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 24:
#line 72 "pike.rl"
	{te = p;p--;{
    callback(PIKE_LANG, pike_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 25:
#line 84 "pike.rl"
	{te = p;p--;}
	break;
	case 26:
#line 84 "pike.rl"
	{{p = ((te))-1;}}
	break;
#line 528 "pike.h"
		}
	}

_again:
	_acts = _pike_actions + _pike_to_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 9:
#line 1 "NONE"
	{ts = 0;}
	break;
#line 541 "pike.h"
		}
	}

	if ( cs == 0 )
		goto _out;
	if ( ++p != pe )
		goto _resume;
	_test_eof: {}
	if ( p == eof )
	{
	if ( _pike_eof_trans[cs] > 0 ) {
		_trans = _pike_eof_trans[cs] - 1;
		goto _eof_trans;
	}
	}

	_out: {}
	}

#line 111 "pike.rl"

  // if no newline at EOF; callback contents of last line
  if (count) { process_last_line(PIKE_LANG) }
}

#endif

/*****************************************************************************/
