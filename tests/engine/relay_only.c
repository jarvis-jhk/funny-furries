/* LD_PRELOAD shim for tests: drops every UDP datagram that is not addressed to
 * the relay port (RELAY_ONLY_PORT, default 3478), so two game processes on one
 * machine cannot reach each other directly and Warpzone must relay. */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <netinet/in.h>
#include <stdlib.h>
#include <sys/socket.h>
static int blocked(const struct sockaddr *to) {
    if(!to) return 0;
    const char *v=getenv("RELAY_ONLY_PORT");int port=v?atoi(v):3478;
    if(to->sa_family==AF_INET) return ntohs(((const struct sockaddr_in *)to)->sin_port)!=port;
    if(to->sa_family==AF_INET6) return ntohs(((const struct sockaddr_in6 *)to)->sin6_port)!=port;
    return 0;
}
ssize_t sendto(int fd,const void *buf,size_t len,int flags,const struct sockaddr *to,socklen_t tolen) {
    static ssize_t (*real)(int,const void *,size_t,int,const struct sockaddr *,socklen_t);
    if(!real) real=(ssize_t (*)(int,const void *,size_t,int,const struct sockaddr *,socklen_t))dlsym(RTLD_NEXT,"sendto");
    int type=0;socklen_t size=sizeof(type);
    if(getsockopt(fd,SOL_SOCKET,SO_TYPE,&type,&size)==0&&type==SOCK_DGRAM&&blocked(to)) return (ssize_t)len;
    return real(fd,buf,len,flags,to,tolen);
}
ssize_t sendmsg(int fd,const struct msghdr *msg,int flags) {
    static ssize_t (*real)(int,const struct msghdr *,int);
    if(!real) real=(ssize_t (*)(int,const struct msghdr *,int))dlsym(RTLD_NEXT,"sendmsg");
    int type=0;socklen_t size=sizeof(type);
    if(msg&&msg->msg_name&&getsockopt(fd,SOL_SOCKET,SO_TYPE,&type,&size)==0&&type==SOCK_DGRAM&&blocked(msg->msg_name)) {
        ssize_t total=0;for(size_t i=0;i<msg->msg_iovlen;++i) total+=(ssize_t)msg->msg_iov[i].iov_len;
        return total;
    }
    return real(fd,msg,flags);
}
