#ifndef FF_INPUT_H
#define FF_INPUT_H
#include <SDL.h>
#include "game.h"
typedef struct { SDL_GameController *pads[2]; bool focused; uint8_t keys[2]; } FF_Input;
void ff_input_init(FF_Input *in);
void ff_input_close(FF_Input *in);
void ff_input_event(FF_Input *in,const SDL_Event *e);
void ff_input_read(FF_Input *in,uint8_t keys[2]);
#endif
