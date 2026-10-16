#include "fault.h"
#include <stdlib.h>
#include <string.h>
#ifdef _WIN32
#include <process.h>
static char endpoint[2048];
#else
#include <unistd.h>
#include <signal.h>
#include <fcntl.h>
#include <errno.h>
static int courier=-1;
#endif
static const char runtime_payload[]="{\"lane\":\"furries\",\"kind\":\"bug\",\"title\":\"Game runtime failed\",\"detail\":\"native-runtime-fault\",\"source\":\"funny-furries/0.7.0 native-desktop\"}";
static const char crash_payload[]="{\"lane\":\"furries\",\"kind\":\"bug\",\"title\":\"Game process crashed\",\"detail\":\"native-process-signal\",\"source\":\"funny-furries/0.7.0 native-desktop\"}";
#ifndef _WIN32
static void notify_courier(char code) {
    if(courier>=0) {
        int descriptor=courier;courier=-1;ssize_t delivered;
        do {delivered=write(descriptor,&code,1);} while(delivered<0&&errno==EINTR);
        close(descriptor);
    }
}
static void crash(int number) {
    /* Only async-signal-safe syscalls here; network and allocation run elsewhere. */
    notify_courier('C');_exit(128+number);
}
#endif
void ff_fault(const char *category) {
#ifdef _WIN32
    if(endpoint[0]) _spawnlp(_P_NOWAIT,"curl.exe","curl.exe","--silent","--max-time","4","--output","NUL","-X","POST","-H","content-type: application/json","--data-binary",strcmp(category,"crash")==0?crash_payload:runtime_payload,endpoint,NULL);
#else
    notify_courier(strcmp(category,"crash")==0?'C':'R');
#endif
}
void ff_fault_init(void) {
    const char *url=getenv("FF_FAULT_REPORT_URL");
    if(url&&(strncmp(url,"https://",8)==0||strncmp(url,"http://",7)==0)&&strlen(url)<2048) {
#ifdef _WIN32
        memcpy(endpoint,url,strlen(url)+1);
#else
        int descriptors[2];
        if(pipe(descriptors)==0) {
            /* Prepare the courier before threads start. It exits silently on normal EOF. */
            signal(SIGCHLD,SIG_IGN);
            pid_t child=fork();
            if(child==0) {
                close(descriptors[1]);char code=0;ssize_t count;
                do {count=read(descriptors[0],&code,1);} while(count<0&&errno==EINTR);
                close(descriptors[0]);if(count!=1) _exit(0);
                int quiet=open("/dev/null",O_RDWR);
                if(quiet>=0) {for(int i=0;i<3;++i) dup2(quiet,i);if(quiet>2) close(quiet);}
                execlp("curl","curl","--silent","--max-time","4","--output","/dev/null","-X","POST","-H","content-type: application/json","--data-binary",code=='C'?crash_payload:runtime_payload,url,(char *)NULL);
                _exit(0);
            }
            close(descriptors[0]);
            if(child>0) {courier=descriptors[1];fcntl(courier,F_SETFD,FD_CLOEXEC);}
            else close(descriptors[1]);
        }
#endif
    }
#ifndef _WIN32
    signal(SIGPIPE,SIG_IGN);
    signal(SIGSEGV,crash);signal(SIGABRT,crash);signal(SIGFPE,crash);signal(SIGILL,crash);
#endif
}
