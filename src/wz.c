#include "wz.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#define CHANNEL_GAME 0
#define CHANNEL_ROSTER 1
/* A peer travels through netplay as an address whose port marks it virtual. */
#define PEER_PORT 7
static FF_Addr peer_addr(uint32_t peer) {return (FF_Addr){peer,PEER_PORT};}
bool ff_wz_is_code(const char *text) {
    static const char alphabet[]="ABCDEFGHJKMNPQRSTUVWXYZ23456789";
    int n=0;
    for(const char *c=text;*c;++c) {
        if(*c=='-'||*c==' ') continue;
        if(!strchr(alphabet,toupper((unsigned char)*c))) return false;
        ++n;
    }
    return n==6;
}
static void upper_copy(char *out,size_t capacity,const char *text) {
    size_t n=0;for(;text&&text[n]&&n+1<capacity;++n) out[n]=(char)toupper((unsigned char)text[n]);
    out[n]=0;
}
#ifdef FF_WARPZONE
#include "warpzone.h"
/* The few fields we read from the library's JSON; it has fixed shapes. */
static const char *json_key(const char *json,const char *key) {
    char pattern[48];snprintf(pattern,sizeof(pattern),"\"%s\":",key);
    const char *p=strstr(json,pattern);if(!p) return NULL;
    p+=strlen(pattern);while(*p==' ') ++p;return p;
}
static bool json_str(const char *json,const char *key,char *out,size_t capacity) {
    const char *p=json_key(json,key);out[0]=0;
    if(!p||*p!='"') return false;
    size_t n=0;for(++p;*p&&*p!='"'&&n+1<capacity;++p) {if(*p=='\\'&&p[1]) ++p;out[n++]=*p;}
    out[n]=0;return true;
}
static bool json_int(const char *json,const char *key,int64_t *out) {
    const char *p=json_key(json,key);
    if(!p||!(isdigit((unsigned char)*p)||*p=='-')) return false;
    *out=strtoll(p,NULL,10);return true;
}
static bool json_bool(const char *json,const char *key) {const char *p=json_key(json,key);return p&&!strncmp(p,"true",4);}
static bool send_hook(void *ctx,FF_Addr to,const void *data,int length) {
    FF_Wz *wz=ctx;
    if(to.port!=PEER_PORT||!wz->client) return false;
    return wz_send(wz->client,to.ip,CHANNEL_GAME,data,(size_t)length,0)==1;
}
bool ff_wz_open(FF_Wz *wz,const char *version) {
    memset(wz,0,sizeof(*wz));
    if(getenv("FF_NO_WARPZONE")) {snprintf(wz->status,sizeof(wz->status),"WARPZONE SWITCHED OFF");return false;}
    /* Matches are joined by hand: a new client is also told about matches made
     * before it started (the event stream replays), and those rooms are gone. */
    wz_config cfg={WZ_ABI_VERSION,NULL,"funny-furries",version,NULL,0};
    wz->client=wz_create(&cfg);
    if(!wz->client) {fprintf(stderr,"warpzone: %s\n",wz_last_error());snprintf(wz->status,sizeof(wz->status),"WARPZONE UNAVAILABLE");return false;}
    wz->available=true;wz->opened_ms=ff_net_ms();snprintf(wz->status,sizeof(wz->status),"CONNECTING TO WARPZONE");
    return true;
}
void ff_wz_close(FF_Wz *wz) {if(wz->client) wz_destroy(wz->client);wz->client=NULL;wz->available=false;}
int ff_wz_launch(FF_Wz *wz,int argc,char **argv) {
    if(!wz->client) return 0;
    int intent=wz_handle_launch(wz->client,argc,(const char *const *)argv);
    if(intent==1) {wz->pending=FF_WZ_NONE;wz->busy=true;snprintf(wz->status,sizeof(wz->status),"JOINING THE ROOM");wz->hosting=false;wz->local_count=1;}
    return intent;
}
void ff_wz_register(FF_Wz *wz,const char *name) {
    if(!wz->client) return;
    wz->error[0]=0;snprintf(wz->status,sizeof(wz->status),"CHECKING THE NAME");wz_register(wz->client,name);
}
static void run(FF_Wz *wz,int action,const char *requested) {
    char arg[16];snprintf(arg,sizeof(arg),"%s",requested?requested:"");   /* may be pending_arg itself */
    wz->error[0]=0;wz->busy=true;
    if(!wz->has_account) {
        wz->pending=action;snprintf(wz->pending_arg,sizeof(wz->pending_arg),"%s",arg);
        snprintf(wz->status,sizeof(wz->status),wz->need_name?"CHOOSE A NAME FOR ONLINE PLAY":"CONNECTING TO WARPZONE");
        return;
    }
    if(action==FF_WZ_QUEUE&&ff_net_ms()-wz->login_ms<3000) {
        /* Right after login the event stream replays old matches; queue once that is over. */
        wz->pending=action;snprintf(wz->pending_arg,sizeof(wz->pending_arg),"%s",arg);
        snprintf(wz->status,sizeof(wz->status),"CONNECTING TO WARPZONE");return;
    }
    wz->pending=FF_WZ_NONE;
    if(action==FF_WZ_HOST) {
        static const char *preset[]={"ffa","2v2"},*mode[]={"Free-for-all","2 vs 2"};
        char options[400];
        snprintf(options,sizeof(options),"{\"max_players\":4,\"visibility\":\"unlisted\",\"entry\":\"code\",\"preset\":\"%s\","
                 "\"metadata\":{\"arena\":\"%s\",\"mode\":\"%s\"}}",preset[wz->mode==FF_TEAMS],
                 wz->arena&&wz->arena->imported?"Original":"Practice",mode[wz->mode==FF_TEAMS]);
        wz->hosting=true;wz_host(wz->client,options);snprintf(wz->status,sizeof(wz->status),"OPENING A ROOM");
    } else if(action==FF_WZ_JOIN_CODE) {
        wz->hosting=false;snprintf(wz->code,sizeof(wz->code),"%s",arg);
        wz_join_code(wz->client,arg);snprintf(wz->status,sizeof(wz->status),"JOINING %s",arg);
    } else if(action==FF_WZ_QUEUE) {
        snprintf(wz->queue,sizeof(wz->queue),"%s",arg);wz->queued=true;wz->queue_confirmed=false;wz->waiting=0;wz->local_count=1;
        wz_queue(wz->client,arg,NULL);snprintf(wz->status,sizeof(wz->status),"LOOKING FOR A MATCH");
    }
}
void ff_wz_host(FF_Wz *wz,int local_count,int mode) {wz->local_count=local_count;wz->mode=mode;run(wz,FF_WZ_HOST,NULL);}
void ff_wz_join_code(FF_Wz *wz,const char *code,int local_count) {
    char clean[8];int n=0;
    for(const char *c=code;*c&&n<6;++c) if(*c!='-'&&*c!=' ') clean[n++]=(char)toupper((unsigned char)*c);
    clean[n]=0;wz->local_count=local_count;run(wz,FF_WZ_JOIN_CODE,clean);
}
void ff_wz_queue(FF_Wz *wz,const char *queue) {run(wz,FF_WZ_QUEUE,queue);}
static void forget_room(FF_Wz *wz) {
    wz->busy=wz->in_room=wz->host=wz->hosting=wz->ranked=wz->reported=wz->started_sent=false;wz->code[0]=wz->room[0]=0;
    memset(wz->peers,0,sizeof(wz->peers));wz->roster_count=0;wz->match_id[0]=0;
}
void ff_wz_leave(FF_Wz *wz,FF_Netplay *np) {
    if(!wz->client) return;
    if(np->virtual_net) ff_np_close(np);
    if(wz->queued) wz_leave_queue(wz->client);
    if(wz->in_room) wz_leave(wz->client);
    forget_room(wz);wz->queued=false;wz->pending=FF_WZ_NONE;wz->error[0]=0;wz->match_state[0]=0;
}
void ff_wz_mode_changed(FF_Wz *wz,int mode) {
    wz->mode=mode;
    if(wz->client&&wz->in_room&&wz->host&&!wz->ranked)
        wz_set_metadata(wz->client,mode==FF_TEAMS?"{\"mode\":\"2 vs 2\"}":"{\"mode\":\"Free-for-all\"}");
}
/* Ranked seats follow the matchmaker's teams: 2 vs 2 pairs even and odd seats. */
static int ranked_seat(const FF_Wz *wz,const char *name) {
    for(int t=0;t<wz->teams;++t) for(int k=0;k<wz->team_size;++k)
        if(!strcmp(wz->team_name[t][k],name)) return wz->team_size==2?t+2*k:t;
    return -1;
}
static void parse_teams(FF_Wz *wz,const char *json) {
    memset(wz->team_name,0,sizeof(wz->team_name));wz->teams=wz->team_size=0;
    const char *p=json_key(json,"teams");if(!p||*p!='[') return;
    int depth=0,t=-1,k=0;
    for(;*p;++p) {
        if(*p=='[') {if(++depth==2) {++t;k=0;}}
        else if(*p==']') {if(--depth==0) break;}
        else if(*p=='"'&&depth==2) {
            char name[20];size_t n=0;
            for(++p;*p&&*p!='"';++p) if(n+1<sizeof(name)) name[n++]=*p;
            name[n]=0;
            if(t<FF_PLAYERS&&k<2) snprintf(wz->team_name[t][k],sizeof(wz->team_name[t][k]),"%s",name);
            if(++k>wz->team_size) wz->team_size=k;
            if(!*p) break;
        }
    }
    wz->teams=t+1>FF_PLAYERS?FF_PLAYERS:t+1;if(wz->team_size>2) wz->team_size=2;
}
static FF_WzPeer *find_peer(FF_Wz *wz,uint32_t peer) {
    for(int i=0;i<FF_WZ_PEERS;++i) if(wz->peers[i].used&&wz->peers[i].peer==peer) return &wz->peers[i];
    return NULL;
}
static void send_roster(FF_Wz *wz) {
    char text[600];int n=snprintf(text,sizeof(text),"%lld %s\n",(long long)wz->account,wz->username);
    for(int i=0;i<FF_WZ_PEERS;++i) if(wz->peers[i].used&&n<(int)sizeof(text))
        n+=snprintf(text+n,sizeof(text)-(size_t)n,"%lld %s\n",(long long)wz->peers[i].account,wz->peers[i].name);
    if(n>=(int)sizeof(text)) n=(int)sizeof(text)-1;
    wz_broadcast(wz->client,CHANNEL_ROSTER,text,(size_t)n,1);
}
static void read_roster(FF_Wz *wz,const uint8_t *data,size_t length) {
    char text[600];if(length>=sizeof(text)) length=sizeof(text)-1;
    memcpy(text,data,length);text[length]=0;wz->roster_count=0;
    for(char *line=strtok(text,"\n");line&&wz->roster_count<FF_PLAYERS;line=strtok(NULL,"\n")) {
        char *space=strchr(line,' ');if(!space) continue;
        *space=0;wz->roster[wz->roster_count].account=strtoll(line,NULL,10);
        snprintf(wz->roster[wz->roster_count].name,sizeof(wz->roster[0].name),"%s",space+1);++wz->roster_count;
    }
}
static bool account_of(const FF_Wz *wz,const char *name,int64_t *account) {
    if(!strcmp(name,wz->username)) {*account=wz->account;return true;}
    for(int i=0;i<FF_WZ_PEERS;++i) if(wz->peers[i].used&&!strcmp(wz->peers[i].name,name)) {*account=wz->peers[i].account;return true;}
    for(int i=0;i<wz->roster_count;++i) if(!strcmp(wz->roster[i].name,name)) {*account=wz->roster[i].account;return true;}
    return false;
}
/* Placements from the agreed final state: teams by round wins, ties together. */
static void report(FF_Wz *wz,const FF_Netplay *np) {
    int score[FF_PLAYERS];int64_t account[FF_PLAYERS][2];
    for(int t=0;t<wz->teams;++t) {
        score[t]=-1;
        for(int k=0;k<wz->team_size;++k) {
            int seat=wz->team_size==2?t+2*k:t;
            if(!account_of(wz,wz->team_name[t][k],&account[t][k])) return;   /* the roster is still on its way */
            if(seat<FF_PLAYERS&&np->final_score[seat]>score[t]) score[t]=np->final_score[seat];
        }
    }
    char json[600];int n=snprintf(json,sizeof(json),"{\"placements\":[");
    bool placed[FF_PLAYERS]={false};bool first_group=true;
    for(;;) {
        int best=-1;for(int t=0;t<wz->teams;++t) if(!placed[t]&&(best<0||score[t]>score[best])) best=t;
        if(best<0) break;
        int top=score[best];n+=snprintf(json+n,sizeof(json)-(size_t)n,"%s[",first_group?"":",");first_group=false;
        bool first=true;
        for(int t=0;t<wz->teams;++t) if(!placed[t]&&score[t]==top) {
            placed[t]=true;
            for(int k=0;k<wz->team_size;++k) {n+=snprintf(json+n,sizeof(json)-(size_t)n,"%s%lld",first?"":",",(long long)account[t][k]);first=false;}
        }
        n+=snprintf(json+n,sizeof(json)-(size_t)n,"]");
    }
    snprintf(json+n,sizeof(json)-(size_t)n,"],\"state_hash\":\"%08x\"}",np->final_hash);
    wz_report_match(wz->client,wz->match_id,json);wz->reported=true;
    snprintf(wz->status,sizeof(wz->status),"RESULT SENT");
    if(getenv("FF_WZ_VERBOSE")) printf("warpzone report match=%s %s\n",wz->match_id,json),fflush(stdout);
}
static void start_netplay(FF_Wz *wz,FF_Netplay *np) {
    int local=wz->ranked?1:wz->local_count<1?1:wz->local_count;
    bool ok=wz->host?ff_np_host_virtual(np,wz->arena,local,send_hook,wz):ff_np_join_virtual(np,wz->arena,local,send_hook,wz);
    if(!ok) return;
    snprintf(np->code,sizeof(np->code),"%s",wz->code);
    /* The host tells guests apart by this nonce; games started in the same millisecond share the clock part. */
    np->nonce^=(uint32_t)wz->account*2654435761u;
    if(wz->ranked) {
        np->first_to=FF_RANKED_WINS;
        const char *wins=getenv("FF_RANKED_WINS");if(wins&&atoi(wins)>0) np->first_to=atoi(wins);
        np->mode=wz->team_size==2?FF_TEAMS:FF_FFA;
        int seat=ranked_seat(wz,wz->username);
        if(wz->host&&seat>=0) ff_np_set_local_seats(np,1u<<seat);
    } else np->mode=wz->mode;
}
void ff_wz_update(FF_Wz *wz,FF_Netplay *np,const FF_Arena *arena) {
    if(!wz->client) return;
    wz->arena=arena;
    wz_poll(wz->client);
    wz_event e;
    while(wz_next_event(wz->client,&e)) {
        const char *j=e.json?e.json:"{}";
        if(getenv("FF_WZ_VERBOSE")&&e.type!=WZ_EVENT_PEER_DATA) printf("warpzone event %d %s\n",(int)e.type,j),fflush(stdout);
        switch(e.type) {
        case WZ_EVENT_LOGGED_IN: case WZ_EVENT_REGISTERED: {
            wz->online=true;int64_t id;
            if(json_int(j,"id",&id)) {
                wz->account=id;wz->has_account=true;wz->login_ms=ff_net_ms();wz->need_name=false;json_str(j,"username",wz->username,sizeof(wz->username));
                snprintf(wz->status,sizeof(wz->status),"ONLINE AS %s",wz->username);upper_copy(wz->status,sizeof(wz->status),wz->status);
            } else {
                wz->need_name=true;
                const char *name=getenv("FF_WZ_NAME");if(name&&*name) ff_wz_register(wz,name);
            }
            break;
        }
        case WZ_EVENT_ERROR: {
            char op[16],message[96];json_str(j,"op",op,sizeof(op));json_str(j,"message",message,sizeof(message));
            fprintf(stderr,"warpzone %s: %s\n",op,message);
            if(!strcmp(op,"login")) {
                wz->online=false;snprintf(wz->status,sizeof(wz->status),"WARPZONE IS NOT REACHABLE");
                if(wz->pending) snprintf(wz->error,sizeof(wz->error),"WARPZONE IS NOT REACHABLE - TRYING AGAIN");
                break;
            }
            if(!strcmp(op,"udp")||!strcmp(op,"report")||!strcmp(op,"list")) break;
            if(!strcmp(op,"join")&&wz->ranked&&!wz->in_room) {
                /* A replayed old match: its room is gone, and we are still in the queue. */
                wz->ranked=false;wz->queued=true;snprintf(wz->status,sizeof(wz->status),"LOOKING FOR A MATCH");break;
            }
            upper_copy(wz->error,sizeof(wz->error),message);
            if(!strcmp(op,"queue")) wz->queued=false;
            if(!strcmp(op,"host")||!strcmp(op,"join")) wz->hosting=false;
            break;
        }
        case WZ_EVENT_ROOM_HOSTED: json_str(j,"code",wz->code,sizeof(wz->code));break;
        case WZ_EVENT_ROOM_JOINED: {
            wz->in_room=true;wz->busy=false;wz->host=json_bool(j,"host");json_str(j,"id",wz->room,sizeof(wz->room));
            if(np->phase!=FF_NP_OFF) ff_np_close(np);
            start_netplay(wz,np);
            snprintf(wz->status,sizeof(wz->status),wz->host?"ROOM OPEN":"IN THE ROOM");
            break;
        }
        case WZ_EVENT_KNOCKING: snprintf(wz->status,sizeof(wz->status),"WAITING FOR THE HOST TO LET YOU IN");break;
        case WZ_EVENT_KNOCK_DENIED: snprintf(wz->error,sizeof(wz->error),"THE HOST DID NOT LET YOU IN");break;
        case WZ_EVENT_KNOCK: {
            /* Our rooms use codes; a knock only comes from a ranked room, where the server approved everyone. */
            char knock[64];if(json_str(j,"knock",knock,sizeof(knock))) wz_answer_knock(wz->client,knock,wz->ranked);
            break;
        }
        case WZ_EVENT_PEER_JOINED: {
            int64_t account=-1;json_int(j,"account",&account);
            FF_WzPeer *p=NULL;
            for(int i=0;i<FF_WZ_PEERS&&!p;++i) if(wz->peers[i].used&&wz->peers[i].account==account) p=&wz->peers[i];
            for(int i=0;i<FF_WZ_PEERS&&!p;++i) if(!wz->peers[i].used) p=&wz->peers[i];
            if(!p) break;
            memset(p,0,sizeof(*p));p->used=true;p->peer=e.peer;
            json_int(j,"account",&p->account);json_str(j,"username",p->name,sizeof(p->name));
            if(wz->host&&wz->ranked) {int seat=ranked_seat(wz,p->name);if(seat>=0) ff_np_reserve(np,peer_addr(e.peer),1u<<seat);}
            break;
        }
        case WZ_EVENT_PEER_CONNECTED: case WZ_EVENT_PEER_PATH: {
            FF_WzPeer *p=find_peer(wz,e.peer);if(!p) break;
            p->connected=true;p->relayed=json_bool(j,"relayed");
            if(e.type==WZ_EVENT_PEER_CONNECTED) {
                if(!wz->host) ff_np_virtual_host(np,peer_addr(e.peer));
                else send_roster(wz);
            }
            break;
        }
        case WZ_EVENT_PEER_DATA:
            if(e.channel==CHANNEL_GAME&&np->virtual_net&&np->phase!=FF_NP_OFF) ff_udp_inject(&np->udp,peer_addr(e.peer),e.data,(int)e.len);
            if(e.channel==CHANNEL_ROSTER&&!wz->host) read_roster(wz,e.data,e.len);
            break;
        case WZ_EVENT_PEER_LEFT: {FF_WzPeer *p=find_peer(wz,e.peer);if(p) p->used=false;break;}
        case WZ_EVENT_ROOM_CLOSED: case WZ_EVENT_KICKED:
            if(np->virtual_net) ff_np_end(np,e.type==WZ_EVENT_KICKED?"YOU WERE REMOVED FROM THE ROOM":"THE ROOM WAS CLOSED");
            forget_room(wz);break;
        case WZ_EVENT_QUEUED: {
            int64_t waiting=0;json_int(j,"waiting",&waiting);wz->waiting=(int)waiting;wz->queued=json_bool(j,"queued");wz->queue_confirmed=wz->queued;
            if(wz->queued) snprintf(wz->status,sizeof(wz->status),"LOOKING FOR A MATCH - %d WAITING",wz->waiting);
            break;
        }
        case WZ_EVENT_MATCH_FOUND: {
            if(!wz->queued||!wz->queue_confirmed||wz->ranked) break;
            char room[48];json_str(j,"room",room,sizeof(room));
            wz_join(wz->client,room,NULL,NULL);
            wz->queued=false;wz->ranked=true;wz->reported=false;wz->match_state[0]=0;wz->roster_count=0;
            json_str(j,"match_id",wz->match_id,sizeof(wz->match_id));parse_teams(wz,j);
            snprintf(wz->status,sizeof(wz->status),"MATCH FOUND");
            break;
        }
        case WZ_EVENT_MATCH_FINISHED: {
            char id[40],state[16];json_str(j,"match_id",id,sizeof(id));json_str(j,"state",state,sizeof(state));
            if(!strcmp(id,wz->match_id)) upper_copy(wz->match_state,sizeof(wz->match_state),state);
            break;
        }
        default: break;
        }
    }
    if(wz->pending&&wz->has_account&&!wz->need_name) run(wz,wz->pending,wz->pending_arg);
    /* libwarpzone 0.1.0 holds every event, the login error too, until the server
     * first answered, so an unreachable server is only noticed by its silence. */
    if(wz->pending&&!wz->has_account&&!wz->need_name&&!wz->error[0]&&ff_net_ms()-wz->opened_ms>10000) {
        wz->online=false;snprintf(wz->error,sizeof(wz->error),"WARPZONE IS NOT REACHABLE - TRYING AGAIN");
    }
    if(np->virtual_net&&np->phase==FF_NP_LOBBY&&wz->host&&wz->ranked) {
        int n=0;for(int s=0;s<FF_PLAYERS;++s) n+=(np->seats>>s)&1u;
        if(n==wz->teams*wz->team_size&&n>=2) {send_roster(wz);ff_np_start(np,np->mode,0);}
    }
    if(np->virtual_net&&np->phase==FF_NP_PLAYING&&wz->host&&!wz->started_sent) {
        wz->started_sent=true;if(!wz->ranked) wz_set_closed(wz->client,1);
    }
    if(wz->ranked&&np->finished&&!wz->reported) report(wz,np);
}
bool ff_wz_seat_name(const FF_Wz *wz,int seat,char *out,unsigned capacity) {
    if(!wz->ranked) return false;
    for(int t=0;t<wz->teams;++t) for(int k=0;k<wz->team_size;++k)
        if((wz->team_size==2?t+2*k:t)==seat&&wz->team_name[t][k][0]) {upper_copy(out,capacity,wz->team_name[t][k]);return true;}
    return false;
}
bool ff_wz_peer_line(FF_Wz *wz,int n,char *out,unsigned capacity) {
    for(int i=0;i<FF_WZ_PEERS;++i) {
        const FF_WzPeer *p=&wz->peers[i];
        if(!p->used||n--) continue;
        char name[20];upper_copy(name,sizeof(name),p->name);
        int rtt=wz->client?wz_peer_rtt_ms(wz->client,p->peer):-1;
        if(!p->connected) snprintf(out,capacity,"%s CONNECTING",name);
        else if(rtt>=0) snprintf(out,capacity,"%s %d MS%s",name,rtt,p->relayed?" RELAYED":" DIRECT");
        else snprintf(out,capacity,"%s%s",name,p->relayed?" RELAYED":" DIRECT");
        return true;
    }
    return false;
}
#else
bool ff_wz_open(FF_Wz *wz,const char *version) {(void)version;(void)upper_copy;memset(wz,0,sizeof(*wz));return false;}
void ff_wz_close(FF_Wz *wz) {(void)wz;}
int ff_wz_launch(FF_Wz *wz,int argc,char **argv) {(void)wz;(void)argc;(void)argv;return 0;}
void ff_wz_register(FF_Wz *wz,const char *name) {(void)wz;(void)name;}
void ff_wz_host(FF_Wz *wz,int local_count,int mode) {(void)wz;(void)local_count;(void)mode;}
void ff_wz_join_code(FF_Wz *wz,const char *code,int local_count) {(void)wz;(void)code;(void)local_count;}
void ff_wz_queue(FF_Wz *wz,const char *queue) {(void)wz;(void)queue;}
void ff_wz_leave(FF_Wz *wz,FF_Netplay *np) {(void)wz;(void)np;}
void ff_wz_update(FF_Wz *wz,FF_Netplay *np,const FF_Arena *arena) {(void)wz;(void)np;(void)arena;}
void ff_wz_mode_changed(FF_Wz *wz,int mode) {(void)wz;(void)mode;}
bool ff_wz_seat_name(const FF_Wz *wz,int seat,char *out,unsigned capacity) {(void)wz;(void)seat;(void)out;(void)capacity;return false;}
bool ff_wz_peer_line(FF_Wz *wz,int n,char *out,unsigned capacity) {(void)wz;(void)n;(void)out;(void)capacity;return false;}
#endif
