
#line 1 "haxe.rl"
// haxe.rl patched by Niel Drummond from actionscript version written by Mitchell Foral. mitchell<att>caladbolg<dott>net.

/************************* Required for every parser *************************/
#ifndef OHCOUNT_HAXE_PARSER_H
#define OHCOUNT_HAXE_PARSER_H

#include "../parser_macros.h"

// the name of the language
const char *HX_LANG = LANG_HAXE;

// the languages entities
const char *hx_entities[] = {
  "space", "comment", "string", "any",
};

// constants associated with the entities
enum {
  HX_SPACE = 0, HX_COMMENT, HX_STRING, HX_ANY
};

/*****************************************************************************/


#line 28 "haxe.h"
static const char _haxe_actions[] = {
	0, 1, 1, 1, 5, 1, 6, 1, 
	8, 1, 9, 1, 10, 1, 11, 1, 
	13, 1, 14, 1, 17, 1, 18, 1, 
	19, 1, 20, 1, 21, 1, 22, 1, 
	24, 1, 25, 1, 26, 1, 27, 1, 
	28, 2, 3, 2, 2, 4, 2, 2, 
	6, 15, 2, 7, 16, 2, 9, 23, 
	2, 12, 1, 2, 12, 7, 2, 12, 
	9, 3, 3, 2, 1, 3, 3, 2, 
	18, 3, 4, 2, 1, 3, 12, 0, 
	7, 4, 12, 3, 2, 1
};

static const char _haxe_cond_offsets[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	1, 2, 3, 3, 3, 3, 3, 3, 
	3, 3, 4, 4, 4, 4, 4, 4, 
	5, 5, 5
};

static const char _haxe_cond_lengths[] = {
	0, 0, 0, 0, 0, 0, 0, 1, 
	1, 1, 0, 0, 0, 0, 0, 0, 
	0, 1, 0, 0, 0, 0, 0, 1, 
	0, 0, 0
};

static const short _haxe_cond_keys[] = {
	13, 13, 13, 13, 13, 13, 13, 13, 
	13, 13, 0
};

static const char _haxe_cond_spaces[] = {
	0, 0, 0, 0, 0, 0
};

static const char _haxe_key_offsets[] = {
	0, 0, 1, 3, 8, 11, 16, 19, 
	30, 41, 53, 54, 55, 56, 60, 63, 
	65, 68, 81, 83, 88, 93, 95, 101, 
	112, 118, 124
};

static const short _haxe_trans_keys[] = {
	42, 42, 47, 10, 34, 92, 12, 13, 
	10, 12, 13, 10, 39, 92, 12, 13, 
	10, 12, 13, 9, 10, 12, 32, 42, 
	269, 525, 0, 11, 14, 255, 9, 10, 
	12, 32, 42, 269, 525, 0, 11, 14, 
	255, 9, 10, 12, 32, 42, 47, 269, 
	525, 0, 11, 14, 255, 10, 10, 10, 
	32, 47, 9, 13, 32, 9, 13, 42, 
	47, 10, 12, 13, 9, 10, 12, 32, 
	34, 39, 47, 269, 525, 0, 8, 14, 
	255, 9, 32, 10, 34, 92, 12, 13, 
	10, 39, 92, 12, 13, 42, 47, 9, 
	10, 32, 92, 12, 13, 9, 10, 12, 
	32, 92, 269, 525, 0, 11, 14, 255, 
	9, 10, 32, 92, 12, 13, 9, 10, 
	32, 92, 12, 13, 10, 0
};

static const char _haxe_single_lengths[] = {
	0, 1, 2, 3, 1, 3, 1, 7, 
	7, 8, 1, 1, 1, 2, 1, 2, 
	1, 9, 2, 3, 3, 2, 4, 7, 
	4, 4, 1
};

static const char _haxe_range_lengths[] = {
	0, 0, 0, 1, 1, 1, 1, 2, 
	2, 2, 0, 0, 0, 1, 1, 0, 
	1, 2, 0, 1, 1, 0, 1, 2, 
	1, 1, 0
};

static const char _haxe_index_offsets[] = {
	0, 0, 2, 5, 10, 13, 18, 21, 
	31, 41, 52, 54, 56, 58, 62, 65, 
	68, 71, 83, 86, 91, 96, 99, 105, 
	115, 121, 127
};

static const char _haxe_indicies[] = {
	2, 1, 2, 3, 1, 4, 6, 7, 
	4, 5, 4, 4, 5, 4, 6, 9, 
	4, 8, 4, 4, 8, 11, 12, 12, 
	11, 13, 14, 12, 10, 10, 4, 16, 
	17, 17, 16, 18, 19, 17, 15, 15, 
	4, 11, 12, 12, 11, 13, 20, 14, 
	12, 10, 10, 4, 12, 4, 22, 21, 
	23, 24, 26, 27, 26, 25, 26, 26, 
	28, 1, 30, 29, 31, 31, 30, 33, 
	23, 23, 33, 34, 35, 36, 37, 38, 
	32, 32, 24, 33, 33, 39, 40, 6, 
	7, 40, 5, 40, 6, 9, 40, 8, 
	10, 41, 40, 43, 42, 43, 44, 42, 
	41, 43, 22, 22, 43, 44, 45, 46, 
	41, 41, 42, 49, 47, 49, 50, 47, 
	48, 49, 22, 49, 50, 47, 48, 23, 
	51, 0
};

static const char _haxe_trans_targs[] = {
	13, 1, 2, 13, 17, 3, 17, 4, 
	5, 6, 7, 7, 8, 9, 10, 7, 
	7, 8, 9, 10, 17, 17, 24, 17, 
	0, 13, 14, 15, 13, 13, 16, 13, 
	17, 18, 19, 20, 21, 12, 26, 17, 
	17, 22, 17, 22, 23, 11, 25, 17, 
	22, 22, 23, 17
};

static const char _haxe_trans_actions[] = {
	39, 9, 9, 53, 29, 0, 17, 0, 
	0, 0, 1, 0, 0, 1, 0, 73, 
	44, 44, 73, 44, 15, 27, 0, 47, 
	0, 31, 7, 62, 33, 37, 9, 35, 
	50, 3, 77, 77, 59, 5, 5, 19, 
	25, 1, 21, 0, 56, 0, 0, 69, 
	65, 41, 81, 23
};

static const char _haxe_to_state_actions[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 11, 0, 0, 
	0, 11, 0, 0, 0, 0, 0, 0, 
	0, 0, 0
};

static const char _haxe_from_state_actions[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 13, 0, 0, 
	0, 13, 0, 0, 0, 0, 0, 0, 
	0, 0, 0
};

static const char _haxe_eof_trans[] = {
	0, 1, 1, 5, 5, 5, 5, 5, 
	5, 5, 5, 22, 0, 0, 29, 30, 
	32, 0, 40, 41, 41, 41, 43, 43, 
	48, 48, 52
};

static const int haxe_start = 13;
static const int haxe_first_final = 13;
static const int haxe_error = 0;

static const int haxe_en_hx_line = 17;
static const int haxe_en_hx_entity = 13;


#line 93 "haxe.rl"


/************************* Required for every parser *************************/

/* Parses a string buffer with Haxe code.
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
void parse_haxe(char *buffer, int length, int count,
                void (*callback) (const char *lang, const char *entity, int s,
                                  int e, void *udata),
                void *userdata
  ) {
  init

  
#line 206 "haxe.h"
	{
	cs = haxe_start;
	ts = 0;
	te = 0;
	act = 0;
	}

#line 116 "haxe.rl"
  cs = (count) ? haxe_en_hx_line : haxe_en_hx_entity;
  
#line 217 "haxe.h"
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
	_acts = _haxe_actions + _haxe_from_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 11:
#line 1 "NONE"
	{ts = p;}
	break;
#line 239 "haxe.h"
		}
	}

	_widec = (*p);
	_klen = _haxe_cond_lengths[cs];
	_keys = _haxe_cond_keys + (_haxe_cond_offsets[cs]*2);
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
				switch ( _haxe_cond_spaces[_haxe_cond_offsets[cs] + ((_mid - _keys)>>1)] ) {
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

	_keys = _haxe_trans_keys + _haxe_key_offsets[cs];
	_trans = _haxe_index_offsets[cs];

	_klen = _haxe_single_lengths[cs];
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

	_klen = _haxe_range_lengths[cs];
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
	_trans = _haxe_indicies[_trans];
_eof_trans:
	cs = _haxe_trans_targs[_trans];

	if ( _haxe_trans_actions[_trans] == 0 )
		goto _again;

	_acts = _haxe_actions + _haxe_trans_actions[_trans];
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
#line 31 "haxe.rl"
	{
    switch(entity) {
    case HX_SPACE:
      ls
      break;
    case HX_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(HX_LANG)
      break;
    case NEWLINE:
      std_newline(HX_LANG)
    }
  }
	break;
	case 3:
#line 49 "haxe.rl"
	{ entity = INTERNAL_NL; }
	break;
	case 4:
#line 58 "haxe.rl"
	{ entity = INTERNAL_NL; }
	break;
	case 5:
#line 71 "haxe.rl"
	{ entity = HX_SPACE; }
	break;
	case 6:
#line 74 "haxe.rl"
	{ entity = NEWLINE;  }
	break;
	case 7:
#line 75 "haxe.rl"
	{ entity = HX_ANY;   }
	break;
	case 8:
#line 88 "haxe.rl"
	{ entity = HX_SPACE;   }
	break;
	case 9:
#line 89 "haxe.rl"
	{ entity = HX_COMMENT; }
	break;
	case 12:
#line 1 "NONE"
	{te = p+1;}
	break;
	case 13:
#line 72 "haxe.rl"
	{te = p+1;}
	break;
	case 14:
#line 73 "haxe.rl"
	{te = p+1;}
	break;
	case 15:
#line 31 "haxe.rl"
	{te = p+1;{
    switch(entity) {
    case HX_SPACE:
      ls
      break;
    case HX_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(HX_LANG)
      break;
    case NEWLINE:
      std_newline(HX_LANG)
    }
  }}
	break;
	case 16:
#line 31 "haxe.rl"
	{te = p+1;{
    switch(entity) {
    case HX_SPACE:
      ls
      break;
    case HX_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(HX_LANG)
      break;
    case NEWLINE:
      std_newline(HX_LANG)
    }
  }}
	break;
	case 17:
#line 31 "haxe.rl"
	{te = p;p--;{
    switch(entity) {
    case HX_SPACE:
      ls
      break;
    case HX_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(HX_LANG)
      break;
    case NEWLINE:
      std_newline(HX_LANG)
    }
  }}
	break;
	case 18:
#line 72 "haxe.rl"
	{te = p;p--;}
	break;
	case 19:
#line 31 "haxe.rl"
	{te = p;p--;{
    switch(entity) {
    case HX_SPACE:
      ls
      break;
    case HX_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(HX_LANG)
      break;
    case NEWLINE:
      std_newline(HX_LANG)
    }
  }}
	break;
	case 20:
#line 31 "haxe.rl"
	{te = p;p--;{
    switch(entity) {
    case HX_SPACE:
      ls
      break;
    case HX_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(HX_LANG)
      break;
    case NEWLINE:
      std_newline(HX_LANG)
    }
  }}
	break;
	case 21:
#line 72 "haxe.rl"
	{{p = ((te))-1;}}
	break;
	case 22:
#line 31 "haxe.rl"
	{{p = ((te))-1;}{
    switch(entity) {
    case HX_SPACE:
      ls
      break;
    case HX_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(HX_LANG)
      break;
    case NEWLINE:
      std_newline(HX_LANG)
    }
  }}
	break;
	case 23:
#line 80 "haxe.rl"
	{te = p+1;{
    callback(HX_LANG, hx_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 24:
#line 91 "haxe.rl"
	{te = p+1;}
	break;
	case 25:
#line 80 "haxe.rl"
	{te = p;p--;{
    callback(HX_LANG, hx_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 26:
#line 80 "haxe.rl"
	{te = p;p--;{
    callback(HX_LANG, hx_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 27:
#line 91 "haxe.rl"
	{te = p;p--;}
	break;
	case 28:
#line 91 "haxe.rl"
	{{p = ((te))-1;}}
	break;
#line 556 "haxe.h"
		}
	}

_again:
	_acts = _haxe_actions + _haxe_to_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 10:
#line 1 "NONE"
	{ts = 0;}
	break;
#line 569 "haxe.h"
		}
	}

	if ( cs == 0 )
		goto _out;
	if ( ++p != pe )
		goto _resume;
	_test_eof: {}
	if ( p == eof )
	{
	if ( _haxe_eof_trans[cs] > 0 ) {
		_trans = _haxe_eof_trans[cs] - 1;
		goto _eof_trans;
	}
	}

	_out: {}
	}

#line 118 "haxe.rl"

  // if no newline at EOF; callback contents of last line
  if (count) { process_last_line(HX_LANG) }
}

#endif

/*****************************************************************************/
