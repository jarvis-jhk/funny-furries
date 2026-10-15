#include "input.h"
#include <stdio.h>
#include <stdlib.h>
#define CHECK(c) do {if(!(c)) {fprintf(stderr,"line %d: %s (%s)\n",__LINE__,#c,SDL_GetError());exit(1);} ++checks;} while(0)
static unsigned checks;
static void pump(FF_Input *input) {SDL_Event e;SDL_PumpEvents();SDL_GameControllerUpdate();while(SDL_PollEvent(&e)) ff_input_event(input,&e);}
static void play_match(FF_Input *input,SDL_Joystick *a,SDL_Joystick *b) {
    static FF_Arena arena;FF_Game game,replay;ff_arena_practice(&arena);arena.bonus_count=0;
    ff_game_init(&game,&arena,91);memset(game.pickups,0,sizeof(game.pickups));
    for(int i=0;i<2;++i) {
        game.players[i].x=(300+30*i)*FF_FP;game.players[i].y=560*FF_FP;
        game.players[i].invulnerable=0;game.players[i].health=12;game.players[i].lives=1;
    }
    CHECK(SDL_JoystickSetVirtualAxis(a,SDL_CONTROLLER_AXIS_LEFTX,0)==0);
    CHECK(SDL_JoystickSetVirtualAxis(b,SDL_CONTROLLER_AXIS_LEFTX,0)==0);
    CHECK(SDL_JoystickSetVirtualButton(b,SDL_CONTROLLER_BUTTON_A,0)==0);
    CHECK(SDL_JoystickSetVirtualButton(a,SDL_CONTROLLER_BUTTON_X,1)==0);
    CHECK(SDL_JoystickSetVirtualButton(b,SDL_CONTROLLER_BUTTON_X,1)==0);
    replay=game;
    uint8_t expected[2]={FF_PUNCH,FF_PUNCH};
    for(int i=0;i<151;++i) {
        pump(input);uint8_t keys[2];ff_input_read(input,keys);CHECK(keys[0]==FF_PUNCH&&keys[1]==FF_PUNCH);
        ff_game_tick(&game,&arena,keys);ff_game_tick(&replay,&arena,expected);
        CHECK(ff_game_hash(&game)==ff_game_hash(&replay));
        if(i==0) {CHECK(game.winner==2);CHECK(!game.players[0].lives&&!game.players[1].lives);}
    }
    CHECK(game.winner==-1&&game.players[0].lives==3&&game.players[1].lives==3);
    CHECK(SDL_JoystickSetVirtualButton(a,SDL_CONTROLLER_BUTTON_X,0)==0);
    CHECK(SDL_JoystickSetVirtualButton(b,SDL_CONTROLLER_BUTTON_X,0)==0);
    CHECK(SDL_JoystickSetVirtualAxis(a,SDL_CONTROLLER_AXIS_LEFTX,20000)==0);
    CHECK(SDL_JoystickSetVirtualAxis(b,SDL_CONTROLLER_AXIS_LEFTX,-20000)==0);
    CHECK(SDL_JoystickSetVirtualButton(b,SDL_CONTROLLER_BUTTON_A,1)==0);
    game.players[0].y=game.players[1].y=560*FF_FP;game.players[1].grounded=1;
    int left=game.players[0].x,right=game.players[1].x;
    for(int i=0;i<10;++i) {pump(input);uint8_t keys[2];ff_input_read(input,keys);ff_game_tick(&game,&arena,keys);}
    CHECK(game.players[0].x>left&&game.players[1].x<right);CHECK(game.players[1].y<560*FF_FP);
}
int main(int argc,char **argv) {
    (void)argc;(void)argv;
    CHECK(SDL_Init(SDL_INIT_GAMECONTROLLER|SDL_INIT_EVENTS)==0);
    FF_Input input;ff_input_init(&input);uint8_t keys[2];SDL_Event e;
    SDL_zero(e);e.type=SDL_KEYDOWN;e.key.keysym.scancode=SDL_SCANCODE_F;ff_input_event(&input,&e);
    e.key.keysym.scancode=SDL_SCANCODE_UP;ff_input_event(&input,&e);ff_input_read(&input,keys);
    CHECK(keys[0]==FF_JUMP);CHECK(keys[1]==FF_LEFT);
    SDL_zero(e);e.type=SDL_WINDOWEVENT;e.window.event=SDL_WINDOWEVENT_FOCUS_LOST;ff_input_event(&input,&e);ff_input_read(&input,keys);CHECK(!keys[0]&&!keys[1]);
    e.window.event=SDL_WINDOWEVENT_FOCUS_GAINED;ff_input_event(&input,&e);ff_input_read(&input,keys);CHECK(!keys[0]&&!keys[1]);
    SDL_VirtualJoystickDesc desc;SDL_zero(desc);desc.version=SDL_VIRTUAL_JOYSTICK_DESC_VERSION;
    desc.type=SDL_JOYSTICK_TYPE_GAMECONTROLLER;desc.naxes=SDL_CONTROLLER_AXIS_MAX;desc.nbuttons=SDL_CONTROLLER_BUTTON_MAX;
    desc.axis_mask=(1u<<SDL_CONTROLLER_AXIS_MAX)-1;desc.button_mask=(1u<<SDL_CONTROLLER_BUTTON_MAX)-1;
    int first=SDL_JoystickAttachVirtualEx(&desc);CHECK(first>=0);
    int second=SDL_JoystickAttachVirtualEx(&desc);CHECK(second>=0);pump(&input);
    CHECK(input.pads[0]&&input.pads[1]);
    SDL_Joystick *a=SDL_GameControllerGetJoystick(input.pads[0]),*b=SDL_GameControllerGetJoystick(input.pads[1]);
    CHECK(SDL_JoystickSetVirtualAxis(a,SDL_CONTROLLER_AXIS_LEFTX,-20000)==0);
    CHECK(SDL_JoystickSetVirtualButton(a,SDL_CONTROLLER_BUTTON_X,1)==0);
    CHECK(SDL_JoystickSetVirtualAxis(b,SDL_CONTROLLER_AXIS_LEFTX,20000)==0);
    CHECK(SDL_JoystickSetVirtualButton(b,SDL_CONTROLLER_BUTTON_A,1)==0);pump(&input);ff_input_read(&input,keys);
    CHECK(keys[0]==(FF_LEFT|FF_PUNCH));CHECK(keys[1]==(FF_RIGHT|FF_JUMP));
    play_match(&input,a,b);
    SDL_JoystickID remaining=SDL_JoystickInstanceID(b);
    CHECK(SDL_JoystickDetachVirtual(first)==0);pump(&input);ff_input_read(&input,keys);
    CHECK(!input.pads[0]);CHECK(!keys[0]);CHECK(SDL_JoystickInstanceID(SDL_GameControllerGetJoystick(input.pads[1]))==remaining);
    int replacement=SDL_JoystickAttachVirtualEx(&desc);CHECK(replacement>=0);pump(&input);CHECK(input.pads[0]&&input.pads[1]);
    CHECK(SDL_JoystickInstanceID(SDL_GameControllerGetJoystick(input.pads[1]))==remaining);
    ff_input_close(&input);SDL_Quit();printf("%u input checks passed\n",checks);return 0;
}
