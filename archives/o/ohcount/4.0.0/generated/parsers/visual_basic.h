
#line 1 "visual_basic.rl"
// visual_basic.rl written by Mitchell Foral. mitchell<att>caladbolg<dott>net.

/************************* Required for every parser *************************/
#ifndef OHCOUNT_VISUAL_BASIC_PARSER_H
#define OHCOUNT_VISUAL_BASIC_PARSER_H

#include "../parser_macros.h"

// the name of the language
const char *VB_LANG = LANG_VISUALBASIC;

// the languages entities
const char *vb_entities[] = {
  "space", "comment", "string", "any"
};

// constants associated with the entities
enum {
  VB_SPACE = 0, VB_COMMENT, VB_STRING, VB_ANY,
};

/*****************************************************************************/


#line 28 "visual_basic.h"
static const char _visual_basic_actions[] = {
	0, 1, 1, 1, 2, 1, 3, 1, 
	5, 1, 6, 1, 7, 1, 8, 1, 
	10, 1, 13, 1, 14, 1, 15, 1, 
	16, 1, 17, 1, 18, 1, 19, 1, 
	20, 1, 21, 1, 22, 2, 1, 4, 
	2, 3, 11, 2, 4, 12, 2, 9, 
	4, 2, 9, 6, 3, 9, 0, 4
	
};

static const char _visual_basic_cond_offsets[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 1, 1, 1, 1, 1
};

static const char _visual_basic_cond_lengths[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 1, 0, 0, 0, 0, 0
};

static const short _visual_basic_cond_keys[] = {
	13, 13, 0
};

static const char _visual_basic_cond_spaces[] = {
	0, 0
};

static const char _visual_basic_key_offsets[] = {
	0, 0, 2, 7, 10, 12, 13, 19, 
	22, 25, 27, 41, 43, 48, 51, 53
};

static const short _visual_basic_trans_keys[] = {
	77, 109, 10, 34, 92, 12, 13, 10, 
	12, 13, 77, 109, 10, 32, 39, 82, 
	114, 9, 13, 32, 9, 13, 10, 12, 
	13, 69, 101, 9, 10, 12, 32, 34, 
	39, 82, 114, 269, 525, 0, 8, 14, 
	255, 9, 32, 10, 34, 92, 12, 13, 
	10, 12, 13, 69, 101, 10, 0
};

static const char _visual_basic_single_lengths[] = {
	0, 2, 3, 1, 2, 1, 4, 1, 
	1, 2, 10, 2, 3, 1, 2, 1
};

static const char _visual_basic_range_lengths[] = {
	0, 0, 1, 1, 0, 0, 1, 1, 
	1, 0, 2, 0, 1, 1, 0, 0
};

static const char _visual_basic_index_offsets[] = {
	0, 0, 3, 8, 11, 14, 16, 22, 
	25, 28, 31, 44, 47, 52, 55, 58
};

static const char _visual_basic_indicies[] = {
	1, 1, 0, 2, 4, 5, 2, 3, 
	2, 2, 3, 6, 6, 2, 7, 8, 
	10, 1, 11, 11, 10, 9, 10, 10, 
	12, 13, 13, 1, 15, 15, 14, 17, 
	7, 7, 17, 18, 19, 20, 20, 21, 
	22, 16, 16, 8, 17, 17, 23, 24, 
	4, 5, 24, 3, 25, 25, 26, 27, 
	27, 24, 7, 28, 0
};

static const char _visual_basic_trans_targs[] = {
	6, 8, 10, 2, 10, 3, 13, 10, 
	0, 6, 7, 9, 6, 6, 6, 1, 
	10, 11, 12, 13, 14, 5, 15, 10, 
	10, 10, 13, 4, 10
};

static const char _visual_basic_trans_actions[] = {
	35, 9, 25, 0, 15, 0, 1, 40, 
	0, 27, 7, 49, 29, 31, 33, 9, 
	43, 3, 52, 37, 46, 5, 5, 17, 
	23, 19, 0, 0, 21
};

static const char _visual_basic_to_state_actions[] = {
	0, 0, 0, 0, 0, 0, 11, 0, 
	0, 0, 11, 0, 0, 0, 0, 0
};

static const char _visual_basic_from_state_actions[] = {
	0, 0, 0, 0, 0, 0, 13, 0, 
	0, 0, 13, 0, 0, 0, 0, 0
};

static const char _visual_basic_eof_trans[] = {
	0, 1, 3, 3, 3, 0, 0, 13, 
	14, 15, 0, 24, 25, 26, 25, 29
};

static const int visual_basic_start = 6;
static const int visual_basic_first_final = 6;
static const int visual_basic_error = 0;

static const int visual_basic_en_vb_line = 10;
static const int visual_basic_en_vb_entity = 6;


#line 73 "visual_basic.rl"


/************************* Required for every parser *************************/

/* Parses a string buffer with Visual Basic code.
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
void parse_visual_basic(char *buffer, int length, int count,
                        void (*callback) (const char *lang, const char *entity,
                                          int s, int e, void *udata),
                        void *userdata
  ) {
  init

  
#line 160 "visual_basic.h"
	{
	cs = visual_basic_start;
	ts = 0;
	te = 0;
	act = 0;
	}

#line 96 "visual_basic.rl"
  cs = (count) ? visual_basic_en_vb_line : visual_basic_en_vb_entity;
  
#line 171 "visual_basic.h"
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
	_acts = _visual_basic_actions + _visual_basic_from_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 8:
#line 1 "NONE"
	{ts = p;}
	break;
#line 193 "visual_basic.h"
		}
	}

	_widec = (*p);
	_klen = _visual_basic_cond_lengths[cs];
	_keys = _visual_basic_cond_keys + (_visual_basic_cond_offsets[cs]*2);
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
				switch ( _visual_basic_cond_spaces[_visual_basic_cond_offsets[cs] + ((_mid - _keys)>>1)] ) {
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

	_keys = _visual_basic_trans_keys + _visual_basic_key_offsets[cs];
	_trans = _visual_basic_index_offsets[cs];

	_klen = _visual_basic_single_lengths[cs];
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

	_klen = _visual_basic_range_lengths[cs];
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
	_trans = _visual_basic_indicies[_trans];
_eof_trans:
	cs = _visual_basic_trans_targs[_trans];

	if ( _visual_basic_trans_actions[_trans] == 0 )
		goto _again;

	_acts = _visual_basic_actions + _visual_basic_trans_actions[_trans];
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
#line 52 "visual_basic.rl"
	{ entity = VB_SPACE; }
	break;
	case 3:
#line 55 "visual_basic.rl"
	{ entity = NEWLINE;  }
	break;
	case 4:
#line 56 "visual_basic.rl"
	{ entity = VB_ANY;   }
	break;
	case 5:
#line 68 "visual_basic.rl"
	{ entity = VB_SPACE;   }
	break;
	case 6:
#line 69 "visual_basic.rl"
	{ entity = VB_COMMENT; }
	break;
	case 9:
#line 1 "NONE"
	{te = p+1;}
	break;
	case 10:
#line 54 "visual_basic.rl"
	{te = p+1;}
	break;
	case 11:
#line 31 "visual_basic.rl"
	{te = p+1;{
    switch(entity) {
    case VB_SPACE:
      ls
      break;
    case VB_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(VB_LANG)
      break;
    case NEWLINE:
      std_newline(VB_LANG)
    }
  }}
	break;
	case 12:
#line 31 "visual_basic.rl"
	{te = p+1;{
    switch(entity) {
    case VB_SPACE:
      ls
      break;
    case VB_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(VB_LANG)
      break;
    case NEWLINE:
      std_newline(VB_LANG)
    }
  }}
	break;
	case 13:
#line 31 "visual_basic.rl"
	{te = p;p--;{
    switch(entity) {
    case VB_SPACE:
      ls
      break;
    case VB_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(VB_LANG)
      break;
    case NEWLINE:
      std_newline(VB_LANG)
    }
  }}
	break;
	case 14:
#line 53 "visual_basic.rl"
	{te = p;p--;}
	break;
	case 15:
#line 31 "visual_basic.rl"
	{te = p;p--;{
    switch(entity) {
    case VB_SPACE:
      ls
      break;
    case VB_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(VB_LANG)
      break;
    case NEWLINE:
      std_newline(VB_LANG)
    }
  }}
	break;
	case 16:
#line 31 "visual_basic.rl"
	{te = p;p--;{
    switch(entity) {
    case VB_SPACE:
      ls
      break;
    case VB_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(VB_LANG)
      break;
    case NEWLINE:
      std_newline(VB_LANG)
    }
  }}
	break;
	case 17:
#line 31 "visual_basic.rl"
	{{p = ((te))-1;}{
    switch(entity) {
    case VB_SPACE:
      ls
      break;
    case VB_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(VB_LANG)
      break;
    case NEWLINE:
      std_newline(VB_LANG)
    }
  }}
	break;
	case 18:
#line 71 "visual_basic.rl"
	{te = p+1;}
	break;
	case 19:
#line 61 "visual_basic.rl"
	{te = p;p--;{
    callback(VB_LANG, vb_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 20:
#line 61 "visual_basic.rl"
	{te = p;p--;{
    callback(VB_LANG, vb_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 21:
#line 71 "visual_basic.rl"
	{te = p;p--;}
	break;
	case 22:
#line 71 "visual_basic.rl"
	{{p = ((te))-1;}}
	break;
#line 470 "visual_basic.h"
		}
	}

_again:
	_acts = _visual_basic_actions + _visual_basic_to_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 7:
#line 1 "NONE"
	{ts = 0;}
	break;
#line 483 "visual_basic.h"
		}
	}

	if ( cs == 0 )
		goto _out;
	if ( ++p != pe )
		goto _resume;
	_test_eof: {}
	if ( p == eof )
	{
	if ( _visual_basic_eof_trans[cs] > 0 ) {
		_trans = _visual_basic_eof_trans[cs] - 1;
		goto _eof_trans;
	}
	}

	_out: {}
	}

#line 98 "visual_basic.rl"

  // if no newline at EOF; callback contents of last line
  if (count) { process_last_line(VB_LANG) }
}

#endif

/*****************************************************************************/
