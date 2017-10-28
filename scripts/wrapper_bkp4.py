#!/shared/apps/python/Python-2.7.5/INSTALL/bin/python

import sys,cStringIO,os,glob,signal,fcntl,json,mongolink,re,tempfile;#,linecache,traceback
from pymongo.errors import BulkWriteError;
from time import time,sleep;
from random import randint;
from subprocess import PIPE,Popen;
from threading  import Thread;
from argparse import ArgumentParser,REMAINDER;
try:
    from Queue import Queue,Empty;
except ImportError:
    from queue import Queue,Empty;  # python 3.x

class AsynchronousThreadStreamReader(Thread):
    '''Class to implement asynchronously read output of
    a separate thread. Pushes read lines on a queue to
    be consumed in another thread.
    '''
    def __init__(self, stream, queue):
        assert isinstance(queue, Queue)
        assert callable(stream.readline)
        Thread.__init__(self)
        self._stream = stream
        self._queue = queue
        self.daemon = True

    def run(self):
        '''The body of the thread: read lines and put them on the queue.'''
        for line in iter(self._stream.readline, ''):
            self._queue.put(line)

    def eof(self):
        '''Check whether there is no more content to expect.'''
        return not self.is_alive() and self._queue.empty()

class AsynchronousThreadStatsReader(Thread):
    '''Class to implement asynchronously read output of
    a separate thread. Pushes read lines on a queue to
    be consumed in another thread.
    '''
    def __init__(self, pid, stats):
        Thread.__init__(self)
        self._stream = open("/proc/"+pid+"/smaps","r")
        self._stats = stats
        self.daemon = True

    def run(self):
        '''The body of the thread: read lines and put them on the queue.'''
        while self.is_alive():
            for stat_name in self._stats.keys():
                self._stats[stat_name] = 0
            self._stream.seek(0);
            for line in self._stream:
                line_split = line.split()
                if len(line_split) == 3:
                    stat_name, stat_size, stat_unit = line_split
                    stat_name = stat_name.rstrip(':')
                    if stat_name in self._stats.keys():
                        stat_size = float(stat_size)
                        if stat_unit.lower() == 'b':
                            multiplier = 1
                        elif stat_unit.lower() in ['k','kb']:
                            multiplier = 1024
                        elif stat_unit.lower() in ['m','mb']:
                            multiplier = 1000*1024
                        elif stat_unit.lower() in ['g','gb']:
                            multiplier = 1000*1000*1024
                        else:
                            raise Exception(stat_name+" in "+self._stream.name+" has unrecognized unit: "+stat_unit)
                        self._stats[stat_name] += multiplier*stat_size

    def eof(self):
        '''Check whether there is no more content to expect.'''
        return not self.is_alive()

    def stat(self, stat_name):
        '''Check whether there is no more content to expect.'''
        return self._stats[stat_name]

    def stats(self):
        '''Check whether there is no more content to expect.'''
        return self._stats

#def PrintException():
#    "If an exception is raised, print traceback of it to output log."
#    exc_type, exc_obj, tb = sys.exc_info();
#    f = tb.tb_frame;
#    lineno = tb.tb_lineno;
#    filename = f.f_code.co_filename;
#    linecache.checkcache(filename);
#    line = linecache.getline(filename, lineno, f.f_globals);
#    print 'EXCEPTION IN ({}, LINE {} "{}"): {}'.format(filename, lineno, line.strip(), exc_obj);
#    print "More info: ",traceback.format_exc();

#def default_sigpipe():
#    signal.signal(signal.SIGPIPE,signal.SIG_DFL);

#def timeleft(starttime,timelimit):
#    "Determine if runtime limit has been reached."
#    if timelimit=="infinite":
#        return 1;
#    else:
#        return (time()-starttime)<timelimit;

#def execscript(scriptcommand,bufsize=1,stdout=PIPE,stderr=PIPE,close_fds=False):
#    p=Popen(scriptcommand,stdout=stdout,stderr=stderr,bufsize=bufsize,close_fds=close_fds);
#    q=Queue();
#    t=Thread(target=enqueue_output,args=(p.stdout,q));
#    t.daemon=True; # thread dies with the program
#    t.start();
#    #jobstring=scriptcommandflags+" \""+scriptpath+"/"+scriptfile+"\" "+" ".join(["\""+str(x)+"\"" for x in args]);
#    #job=Popen(jobstring,shell=True,stdout=outstream,stderr=errstream,preexec_fn=default_sigpipe);
#    return (p,q,t);

#def getstats(command,fields,stepid):
#    statsstring=command+" -n -o '"+",".join(fields)+"' -j \""+str(stepid)+"\" | sed 's/G/MK/g' | sed 's/M/KK/g' | sed 's/K/000/g' | sed 's/\s\s*/ /g' | cut -d' ' -f1 --complement | head -c -2";
#    stats=Popen(statsstring,shell=True,stdout=PIPE).communicate()[0].split(" ");
#    return stats;

def getstat(pid,statname):
    statstring="echo \"($(cat /proc/"+str(pid)+"/smaps 2>/dev/null | grep -E '^"+str(statname)+":' | sed 's/\s\s*/ /g' | cut -d' ' -f2 | tr '\n' '+' | head -c -1))*1024\" | bc";
    stat=Popen(statstring,shell=True,stdout=PIPE).communicate()[0];
    if stat.isdigit():
        return eval(stat);
    else:
        raise ValueError;

#def enqueue_output(out,queue):
#    for line in iter(out.readline,b''):
#        queue.put(line);
#    out.close();

#ON_POSIX=('posix' in sys.builtin_module_names);

parser=ArgumentParser();
parser.add_argument('--controller','-c',dest='controllername',action='store',default=None,help='');
parser.add_argument('--jobnum','-j',dest='jobnum',action='store',default=None,help='');
parser.add_argument('--stepid','-i',dest='stepid',action='store',default=None,help='');
parser.add_argument('--nbatch','-n',dest='nbatch',action='store',default=1,help='');
parser.add_argument('--nworkers','-N',dest='nworkers',action='store',default=1,help='');
#parser.add_argument('--basecoll','-b',dest='basecoll',action='store',default=None,help='');
#parser.add_argument('--dbindexes','-i',dest='dbindexes',nargs='+',default=None,help='');
parser.add_argument('--dburi','-U',dest='dburi',action='store',default=None,help='');
parser.add_argument('--dbname','-d',dest='dbname',action='store',default=None,help='');
parser.add_argument('--dbusername','-u',dest='dbusername',action='store',default=None,help='');
parser.add_argument('--dbpassword','-p',dest='dbpassword',action='store',default=None,help='');
parser.add_argument('--markdone','-M',dest='markdone',action='store',default="MARK",help='');
parser.add_argument('--write-local','-w',dest='writelocal',action='store_true',default=False,help='');
parser.add_argument('--write-db','-W',dest='writedb',action='store_true',default=False,help='');
parser.add_argument('--stats-local','-s',dest='statslocal',action='store_true',default=False,help='');
parser.add_argument('--stats-db','-S',dest='statsdb',action='store_true',default=False,help='');
parser.add_argument('--module','-m', dest='scriptcommand',nargs=REMAINDER,required=True,help='');

kwargs=vars(parser.parse_known_args()[0]);
#tempiostream.write(kwargs+"\n");
#sys.stdout.flush();
scriptcommand=kwargs['scriptcommand'];
del kwargs['scriptcommand'];

mainpath=Popen("echo \"$SLURMONGO_ROOT\" | head -c -1",shell=True,stdout=PIPE).communicate()[0];

modname=scriptcommand[1].split('/')[-1].split('.')[0];

if any([kwargs[x] for x in ['statslocal','statsdb']]) and ((kwargs['controllername']==None) or (kwargs['stepid']==None) or (kwargs['jobnum']==None)):
    parser.error("--stats-local and --stats-db require --controllername, --stepid, and --jobnum.");

if any([kwargs[x] for x in ['writedb','statsdb']]) and ((kwargs['controllername']==None) and ((kwargs['dburi']==None) or (kwargs['dbname']==None) or (kwargs['dbusername']==None) or (kwargs['dbpassword']==None))):
    parser.error("--writedb and --statsdb requires either the option: --controllername, or the options: --dburi, --dbname, --dbusername, and --dbpassword.");

if (kwargs['controllername']==None) or (kwargs['stepid']==None) or (kwargs['jobnum']==None):
    stepname=modname;
else:
    stepnum=str(int(kwargs['stepid'].split('.')[1])+1);
    stepname=modname+"_"+kwargs['controllername']+"_job_"+kwargs['jobnum']+"_step_"+stepnum;

if (kwargs['controllername']==None):
    workpath=mainpath+"/modules/"+modname;
    dburi=kwargs['dburi'];
    dbname=kwargs['dbname'];
    dbusername=kwargs['dbusername'];
    dbpassword=kwargs['dbpassword'];
else:
    controllerpath=mainpath+"/modules/"+modname+"/"+kwargs['controllername'];
    workpath=controllerpath+"/jobs"
    controllerfile=controllerpath+"/controller_"+modname+"_"+kwargs['controllername']+".job";
    dburifile=mainpath+"/state/mongouri";

    with open(controllerfile,"r") as controllerstream:
        for controllerline in controllerstream:
            if "dbname=" in controllerline:
                dbname=controllerline.split("=")[1].lstrip("\"").rstrip("\"\n");
            elif "dbusername=" in controllerline:
                dbusername=controllerline.split("=")[1].lstrip("\"").rstrip("\"\n");
                if dbusername=="":
                    dbusername=None;
            elif "dbpassword=" in controllerline:
                dbpassword=controllerline.split("=")[1].lstrip("\"").rstrip("\"\n");
                if dbpassword=="":
                    dbpassword=None;

    with open(dburifile,"r") as dburistream:
        dburi=dburistream.readline().rstrip("\n");

if dbusername!=None:
    dburi=dburi.replace("mongodb://","mongodb://"+dbusername+":"+dbpassword+"@");
    dbclient=mongolink.MongoClient(dburi+dbname+"?authMechanism=SCRAM-SHA-1");
else:
    dbclient=mongolink.MongoClient(dburi+dbname);

db=dbclient[dbname];

process=Popen(scriptcommand,stdout=PIPE,stderr=PIPE,bufsize=1);

stdout_queue=Queue();
stdout_reader=AsynchronousThreadStreamReader(process.stdout,stdout_queue);
stdout_reader.start();

stderr_queue=Queue();
stderr_reader=AsynchronousThreadStreamReader(process.stderr,stderr_queue);
stderr_reader.start();

bulkdict={};
#tempiostream=open(workpath+"/"+stepname+".temp","w");
iostream=cStringIO.StringIO();
bsonsize=0;
countresult=0;
nbatch=randint(1,int(kwargs['nbatch']));
totcputime=0;
while (not stdout_reader.eof()) or (not stderr_reader.eof()):
    while not stdout_queue.empty():
        with open(workpath+"/"+stepname+".temp","a") as tempiostream:
            while (not stdout_queue.empty()) and ((countresult<nbatch) or (len(glob.glob(workpath+"/*.lock"))>=kwargs['nworkers'])):
                line=stdout_queue.get().rstrip("\n");
                linehead=re.sub("^([-+&@].*?>|None).*",r"\1",line);
                linemarker=linehead[0];
                if linemarker=="-":
                    newcollection,strindexdoc=linehead[1:-1].split(".");
                    newindexdoc=json.loads(strindexdoc);
                    linedoc=re.sub("^[-+&@].*?>","",line).rstrip("\n");
                    doc=json.loads(linedoc);
                    bsonsize-=mongolink.bsonsize(doc);
                    if kwargs['writedb']:
                        if newcollection not in bulkdict.keys():
                            bulkdict[newcollection]=db[newcollection].initialize_unordered_bulk_op();
                        bulkdict[newcollection].find(newindexdoc).update({"$unset":doc});
                    if kwargs['writelocal']:
                        tempiostream.write(line+"\n");
                        tempiostream.flush();
                        iostream.write(line+"\n");
                        iostream.flush();
                elif linemarker=="+":
                    #tempiostream.write(linehead[1:-1].split(".")+"\n");
                    #sys.stdout.flush();
                    newcollection,strindexdoc=linehead[1:-1].split(".");
                    newindexdoc=json.loads(strindexdoc);
                    linedoc=re.sub("^[-+&@].*?>","",line).rstrip("\n");
                    doc=json.loads(linedoc);
                    bsonsize+=mongolink.bsonsize(doc);
                    if kwargs['writedb']:
                        if newcollection not in bulkdict.keys():
                            bulkdict[newcollection]=db[newcollection].initialize_unordered_bulk_op();
                        bulkdict[newcollection].find(newindexdoc).upsert().update({"$set":doc});
                    if kwargs['writelocal']:
                        tempiostream.write(line+"\n");
                        tempiostream.flush();
                        iostream.write(line+"\n");
                        iostream.flush();
                elif linemarker=="&":
                    newcollection,strindexdoc=linehead[1:-1].split(".");
                    newindexdoc=json.loads(strindexdoc);
                    linedoc=re.sub("^[-+&@].*?>","",line).rstrip("\n");
                    doc=json.loads(linedoc);
                    bsonsize+=mongolink.bsonsize(doc);
                    if kwargs['writedb']:
                        if newcollection not in bulkdict.keys():
                            bulkdict[newcollection]=db[newcollection].initialize_unordered_bulk_op();
                        bulkdict[newcollection].find(newindexdoc).upsert().update({"$addToSet":doc});
                    if kwargs['writelocal']:
                        tempiostream.write(line+"\n");
                        tempiostream.flush();
                        iostream.write(line+"\n");
                        iostream.flush();
                elif linemarker=="@":
                    if kwargs['statslocal'] or kwargs['statsdb']:
                        stats=getstats("sstat",["MaxRSS","MaxVMSize"],kwargs['stepid']);
                        if (len(stats)==1) and (stats[0]==""):
                            newtotcputime,maxrss,maxvmsize=[eval(x) for x in getstats("sacct",["CPUTimeRAW","MaxRSS","MaxVMSize"],kwargs['stepid'])];
                        else:
                            newtotcputime=eval(getstats("sacct",["CPUTimeRAW"],kwargs['stepid'])[0]);
                            maxrss,maxvmsize=stats;
                        cputime=newtotcputime-totcputime;
                        totcputime=newtotcputime;
                    newcollection,strindexdoc=linehead[1:].split("<")[0].split(".");
                    newindexdoc=json.loads(strindexdoc);
                    if kwargs['writelocal']:
                        tempiostream.write(line+"\n");
                        tempiostream.flush();
                        iostream.write(line+"\n");
                        iostream.flush();
                    if kwargs['statslocal']:
                        tempiostream.write("CPUTime: "+str(cputime)+" seconds\n");
                        tempiostream.write("MaxRSS: "+str(maxrss)+" bytes\n");
                        tempiostream.write("MaxVMSize: "+str(maxvmsize)+" bytes\n");
                        tempiostream.write("BSONSize: "+str(bsonsize)+" bytes\n");
                        tempiostream.flush();
                        iostream.write("CPUTime: "+str(cputime)+" seconds\n");
                        iostream.write("MaxRSS: "+str(maxrss)+" bytes\n");
                        iostream.write("MaxVMSize: "+str(maxvmsize)+" bytes\n");
                        iostream.write("BSONSize: "+str(bsonsize)+" bytes\n");
                        iostream.flush();
                    if kwargs['statsdb']:
                        statsmark={};
                        statsmark.update({modname+"STATS":{"CPUTIME":cputime,"MAXRSS":maxrss,"MAXVMSIZE":maxvmsize,"BSONSIZE":bsonsize}});
                        if kwargs['markdone']!="":
                            statsmark.update({modname+kwargs['markdone']:True});
                        if len(statsmark)>0:
                            if newcollection not in bulkdict.keys():
                                bulkdict[newcollection]=db[newcollection].initialize_unordered_bulk_op();
                            bulkdict[newcollection].find(newindexdoc).upsert().update({"$set":statsmark});
                    bsonsize=0;
                else:
                    if kwargs['writelocal']:
                        tempiostream.write(line+"\n");
                        tempiostream.flush();
                        iostream.write(line+"\n");
                        iostream.flush();
                countresult+=1;
                #if len(glob.glob(workpath+"/*.lock"))<kwargs['nworkers']:
                #    lockfile=workpath+"/"+kwargs['stepid']+".lock";
                #    with open(lockfile,'w') as lockstream:
                #        lockstream.write(str(countresult));
                #        lockstream.flush();
                #    for bulkcoll in bulkdict.keys():
                #        try:
                #            bulkdict[bulkcoll].execute();
                #        except BulkWriteError as bwe:
                #            pprint(bwe.details);
                #    while True:
                #        try:
                #            fcntl.flock(sys.stdout,fcntl.LOCK_EX | fcntl.LOCK_NB);
                #            break;
                #        except IOError:
                #            sleep(0.01);
                #    sys.stdout.write(tempiostream.getvalue());
                #    sys.stdout.flush();
                #    fcntl.flock(sys.stdout,fcntl.LOCK_UN);
                #    bulkdict={};
                #    tempiostream=cStringIO.StringIO();
                #    countresult=0;
                #    os.remove(lockfile);
        if (countresult>=nbatch) and (len(glob.glob(workpath+"/*.lock"))<kwargs['nworkers']):
            #if len(glob.glob(workpath+"/*.lock"))>=kwargs['nworkers']:
            #    overlocked=True;
            #    os.kill(process.pid,signal.SIGSTOP);
            #    while len(glob.glob(workpath+"/*.lock"))>=kwargs['nworkers']:
            #        sleep(0.01);
            #else:
            #    overlocked=False;
            lockfile=workpath+"/"+kwargs['stepid']+".lock";
            with open(lockfile,'w') as lockstream:
                lockstream.write(str(countresult));
                lockstream.flush();
            for bulkcoll in bulkdict.keys():
                try:
                    bulkdict[bulkcoll].execute();
                except BulkWriteError as bwe:
                    pprint(bwe.details);
            #while True:
            #    try:
            #        fcntl.flock(sys.stdout,fcntl.LOCK_EX | fcntl.LOCK_NB);
            #        break;
            #    except IOError:
            #        sleep(0.01);
            #tempiostream.close();
            #with open(workpath+"/"+stepname+".temp","r") as tempiostream, open(workpath+"/"+stepname+".out","a") as iostream:
            #    for line in tempiostream:
            #        iostream.write(line);
            #        iostream.flush();
            #    os.remove(tempiostream.name);
            #sys.stdout.write(tempiostream.getvalue());
            #sys.stdout.flush();
            os.remove(workpath+"/"+stepname+".temp");
            with open(workpath+"/"+stepname+".out","a") as outiostream:
                outiostream.write(iostream.getvalue());
                outiostream.flush();
            #fcntl.flock(sys.stdout,fcntl.LOCK_UN);
            bulkdict={};
            #tempiostream=open(workpath+"/"+stepname+".temp","w");
            iostream=cStringIO.StringIO();
            countresult=0;
            nbatch=randint(1,int(kwargs['nbatch']));
            os.remove(lockfile);
            #if overlocked:
            #    os.kill(process.pid,signal.SIGCONT);

    while not stderr_queue.empty():
        stderr_line=stderr_queue.get();
        while True:
            try:
                fcntl.flock(sys.stderr,fcntl.LOCK_EX | fcntl.LOCK_NB);
                break;
            except IOError:
                sleep(0.01);
        sys.stderr.write(stderr_line);
        sys.stderr.flush();
        fcntl.flock(sys.stderr,fcntl.LOCK_UN);

    sleep(0.01);

stdout_reader.join();
stderr_reader.join();

process.stdout.close();
process.stderr.close();