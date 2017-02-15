#!/shared/apps/python/Python-2.7.5/INSTALL/bin/python

import sys;
from pymongo import MongoClient;
from math import ceil;
from . import tools;
from . import parse;

def collectionfind(db,collection,query,projection,formatresult="string"):
    "Query specific collection in database."
    if projection=="count":
        result=db[collection].find(query).count();
    else:
        stringresult=list(db[collection].find(query,projection));
        if formatresult=="string":
            result=stringresult;
        elif formatresult=="expression":
            result=string2expression(stringresult);
        else:
            result=None;
    #return [dict(zip(y.keys(),[mat2py(y[x]) for x in y.keys()])) for y in result];
    return result;

def gettiers(db):
    "Return all tiers (i.e. collections) of database."
    return [x["TIER"] for x in collectionfind(db,"TIERS",{},{"_id":0,"TIER":1})];

#def getindexes(db,collection="all"):
#    "Return all indexes for a collection."
#    if collection=="all":
#        query={};
#    else:
#        query={"TIER":collection};
#    result=tools.deldup([x["INDEX"] for x in collectionfind(db,"INDEXES",query,{"_id":0,"INDEX":1})]);
#    return result;

def getintersectionindexes(db,*collections):
    if len(collections)==0:
        return tools.deldup([x["INDEX"] for x in collectionfind(db,"INDEXES",{},{"_id":0,"INDEX":1})]);
    else:
        result=[x["INDEX"] for x in collectionfind(db,"INDEXES",{"TIER":collections[0]},{"_id":0,"INDEX":1})];
        for i in range(1,len(collections)):
            result=[y for y in result if y in [x["INDEX"] for x in collectionfind(db,"INDEXES",{"TIER":collections[i]},{"_id":0,"INDEX":1})]];
        return tools.deldup(result);

def getunionindexes(db,*collections):
    if len(collections)==0:
        return tools.deldup([x["INDEX"] for x in collectionfind(db,"INDEXES",{},{"_id":0,"INDEX":1})]);
    else:
        result=[x["INDEX"] for x in collectionfind(db,"INDEXES",{"TIER":collections[0]},{"_id":0,"INDEX":1})];
        for i in range(1,len(collections)):
            result+=[x["INDEX"] for x in collectionfind(db,"INDEXES",{"TIER":collections[i]},{"_id":0,"INDEX":1})];
        return tools.deldup(result);

def getcomplementindexes(db,*collections):
    return [x for x in getunionindexes(db,*collections) if x not in getintersectionindexes(db,*collections)];

def gettierfromdoc(db,doc):
    tiers=gettiers(db);
    indexes=getintersectionindexes(db);
    dbindexes=[x for x in doc.keys() if x in indexes];
    i=0;
    tierindexes=getintersectionindexes(db,tiers[i]);
    while (i<len(tiers)) and not (all([x in tierindexes for x in dbindexes]) and all([x in dbindexes for x in tierindexes])):
        i+=1;
        tierindexes=getintersectionindexes(db,tiers[i]);
    if i<len(tiers):
        return tiers[i];
    else:
        return "";

def collectionfieldexists(db,collection,field):
    "Check if specific field exists in the collection."
    result=db[collection].find({},{"_id":0,field:1}).limit(1).next()!={};
    return result;

#def listindexes(db,intersectionindexes,distribfilter,filters):
#    "List the minimal sets of indexes from one collection's query required to specify documents in the next collection's query."
#    if len(intersectionindexes)==0:
#        indexlist=distribfilter;
#    else:
#        #indexlist=tools.deldup([dict([(x,z[x]) for x in trueindexes if all([x in y.keys() for y in filters])]) for z in filters]);
#        indexlist=[{"$and":[dict([z]) for z in distribfilter.items()]+[{x:y[x]} for x in intersectionindexes]} for y in filters];
#    return indexlist;

def listindexes(db,distribfilter,intersectionindexes,filters):
    "List the minimal sets of indexes from one collection's query required to specify documents in the next collection's query."
    if len(intersectionindexes)==0:
        indexlist=distribfilter;
    else:
        #indexlist=tools.deldup([dict([(x,z[x]) for x in trueindexes if all([x in y.keys() for y in filters])]) for z in filters]);
        indexlist={"$or":[{"$and":[dict([z]) for z in distribfilter.items()]+[{x:y[x]} for x in intersectionindexes]} for y in filters]};
    return indexlist;

#def sameindexes(filter1,filter2,indexes):
#    "Check whether documents from two different collection's queries share the same minimal indexes and should be concatenated."
#    return all([filter1[x]==filter2[x] for x in filter1 if (x in indexes) and (x in filter2)]);

def mergenextquery(db,intersectionindexes,nextquery,prevresult,chunk=100,formatresult="string"):
    n=int(ceil(float(len(prevresult))/float(chunk)));
    totalresult=[];
    for k in range(n):
        chunkprevresult=prevresult[k*chunk:(k+1)*chunk];
        chunkindexlist=listindexes(db,nextquery[1],intersectionindexes,chunkprevresult);
        chunknextresult=collectionfind(db,nextquery[0],chunkindexlist,nextquery[2],formatresult=formatresult);
        chunktotalresult=[dict(x.items()+y.items()) for x in chunkprevresult for y in chunknextresult if all([x[z]==y[z] for z in intersectionindexes])];
        #print str(k+1)+" of "+str(n);
        totalresult+=chunktotalresult;
    return totalresult;

#def querydatabase(db,queries,formatresult="string"):
#    "Query all collections in the database and concatenate the documents of each that refer to the same object."
#    tiersord=dict([(x["TIER"],x["TIERID"]) for x in collectionfind(db,"TIERS",{},{"_id":0,"TIER":1,"TIERID":1})]);
#    indexes=getintersectionindexes(db);
#    maxquerylen=max([len(x[1]) for x in queries]);
#    sortedprojqueries=sorted([y for y in queries if y[2]!="count"],key=lambda x: (maxquerylen-len(x[1]),tiersord[x[0]]));
#    maxcountquery=[] if len(queries)==len(sortedprojqueries) else [max([y for y in queries if y not in sortedprojqueries],key=lambda x: len(x[1]))];
#    sortedqueries=sortedprojqueries+maxcountquery;
#    totalresult=collectionfind(db,*sortedqueries[0],formatresult=formatresult);
#    if sortedqueries[0][2]=="count":
#        return totalresult;
#    for i in range(1,len(sortedqueries)):
#        indexlist=listindexes(db,[x[0] for x in sortedqueries[:i+1]],totalresult,indexes);
#        if len(indexlist)==0:
#            orgroup=sortedqueries[i][1];
#        else:
#            orgroup=dict(sortedqueries[i][1].items()+{"$or":indexlist}.items());
#        nextresult=collectionfind(db,sortedqueries[i][0],orgroup,sortedqueries[i][2],formatresult=formatresult);
#        if sortedqueries[i][2]=="count":
#            return nextresult;
#        totalresult=[dict(x.items()+y.items()) for x in totalresult for y in nextresult if sameindexes(x,y,indexes)];
#    return totalresult;

def querydatabase(db,queries,chunk=100,formatresult="string"):
    "Query all collections in the database and concatenate the documents of each that refer to the same object."
    tiersord=dict([(x["TIER"],x["TIERID"]) for x in collectionfind(db,"TIERS",{},{"_id":0,"TIER":1,"TIERID":1})]);
    maxquerylen=max([len(x[1]) for x in queries]);
    sortedprojqueries=sorted([y for y in queries if y[2]!="count"],key=lambda x: (maxquerylen-len(x[1]),tiersord[x[0]]));
    maxcountquery=[] if len(queries)==len(sortedprojqueries) else [max([y for y in queries if y not in sortedprojqueries],key=lambda x: len(x[1]))];
    sortedqueries=sortedprojqueries+maxcountquery;
    totalresult=collectionfind(db,*sortedqueries[0],formatresult=formatresult);
    if sortedqueries[0][2]=="count":
        return len(totalresult);
    for i in range(1,len(sortedqueries)):
        prevcollections=[x[0] for x in sortedqueries[:i+1]];
        intersectionindexes=getintersectionindexes(db,*prevcollections);
        totalresult=mergenextquery(db,intersectionindexes,sortedqueries[i],totalresult,chunk=chunk,formatresult=formatresult);
        if sortedqueries[i][2]=="count":
            return len(totalresult);
    return totalresult;

def printasfunc(*args):
    print list(args)[-1];
    sys.stdout.flush();

def dbdive(db,queries,filepath,inputfunc=lambda:{"nsteps":1},inputdoc={"nsteps":1},action=printasfunc,writeform=lambda x:x,readform=lambda x:eval(x),stopat=lambda:False,batchcounter=1,stepcounter=1,toplevel=True):
    prevfilters=[];
    docbatch=[];

    iostream=open(filepath,"a+");

    thiscollindexes=getunionindexes(db,queries[0][0]);

    if toplevel:
        allcollindexes=getunionindexes(db,*[x[0] for x in queries]);
        iostream.seek(0,0);
        for line in iostream:
            linedoc=readform(line.rstrip("\n"));
            linefilter={"$or":[{x:{"$ne":linedoc[x]}} for x in thiscollindexes]};
            prevfilters+=[linefilter];
        thisquery=[queries[0][0],{"$and":[dict([x]) for x in queries[0][1].items()]+prevfilters[:-1]},queries[0][2]];
    else:
        thisquery=queries[0];
    
    docs=collectionfind(db,*thisquery);
    
    i=0;
    while (i<len(docs)) and not stopat():
        doc=docs[i];

        if len(queries)>1:
            subdocbatch=[];

            intersectionindexes=getintersectionindexes(db,queries[0][0],queries[1][0]);
            unionindexes=getunionindexes(db,queries[0][0],queries[1][0]);
            nextcollindexes=getunionindexes(db,queries[1][0]);
            newnextcollindexes=[x for x in unionindexes if ((x in nextcollindexes) and (x not in intersectionindexes))];

            while ((i==0) or (len(subdocbatch)>0)) and not stopat():
                if i==0:
                    iostream.seek(0,0);
                    for line in iostream:
                        linedoc=readform(line.rstrip("\n"));
                        if all([linedoc[x]==doc[x] for x in intersectionindexes]):
                            linefilter={"$or":[{x:{"$ne":linedoc[x]}} for x in newnextcollindexes if x in linedoc.keys()]};
                            if len(linefilter["$or"])>0:
                                prevfilters+=[linefilter];

                print "Collection: "+str(queries[1][0]);
                print "To Include: "+str([{x:doc[x]} for x in intersectionindexes]);
                print "To Skip: "+str(prevfilters);
                print "";
                sys.stdout.flush();

                nextqueries=[[queries[1][0],{"$and":[dict([x]) for x in queries[1][1].items()]+[{x:doc[x]} for x in intersectionindexes]+prevfilters},queries[1][2]]]+queries[2:];
                newinputdoc=inputdoc.copy();
                newinputdoc["nsteps"]-=len(docbatch);
                subdocbatch=dbdive(db,nextqueries,filepath,inputfunc=inputfunc,inputdoc=newinputdoc,action=action,writeform=writeform,readform=readform,stopat=stopat,batchcounter=batchcounter,stepcounter=stepcounter,toplevel=False);
                
                if not stopat():
                    docbatch+=[dict(doc.items()+x.items()) for x in subdocbatch];
                    if len(docbatch)==inputdoc["nsteps"]:
                        if toplevel:
                            action(batchcounter,stepcounter,inputdoc,docbatch);
                            inputdoc.update(inputfunc());
                            for linedoc in docbatch:
                                iostream.seek(0,2);
                                linedoctrim=dict([(x,linedoc[x]) for x in allcollindexes]);
                                iostream.write(str(writeform(linedoctrim)).replace(" ","")+"\n");
                                iostream.flush();
                                if len(subdocbatch)==0:
                                    linefilter={"$or":[{x:{"$ne":linedoctrim[x]}} for x in thiscollindexes]};
                                    prevfilters+=[linefilter];
                            if len(subdocbatch)==0:
                                prevfilters=tools.deldup(prevfilters);
                            batchcounter+=1;
                            stepcounter+=len(docbatch);
                            docbatch=[];
                        else:
                            iostream.close();
                            return docbatch;
                    else:
                        break;
        else:
            docbatch+=[doc];
            if len(docbatch)==inputdoc["nsteps"]:
                if toplevel:
                    action(batchcounter,stepcounter,inputdoc,docbatch);
                    inputdoc.update(inputfunc());
                    for linedoc in docbatch:
                        iostream.seek(0,2);
                        linedoctrim=dict([(x,linedoc[x]) for x in allcollindexes]);
                        iostream.write(str(writeform(linedoctrim)).replace(" ","")+"\n");
                        iostream.flush();
                    batchcounter+=1;
                    stepcounter+=len(docbatch);
                    docbatch=[];
                else:
                    iostream.close();
                    return docbatch;
        i+=1;
    
    if toplevel:
        if not stopat():
            if len(docbatch)>0:
                action(batchcounter,stepcounter,inputdoc,docbatch);
                for linedoc in docbatch:
                    iostream.seek(0,2);
                    linedoctrim=dict([(x,linedoc[x]) for x in allcollindexes]);# if x in linedoc.keys()]);
                    iostream.write(str(writeform(linedoctrim)).replace(" ","")+"\n");
                    iostream.flush();
                batchcounter+=1;
                stepcounter+=len(docbatch);

        iostream.close();
        return [batchcounter,stepcounter];
    else:
        iostream.close();
        return docbatch;

'''
username="frontend";
password="password";
server="129.10.135.170";
port="27017";
dbname="ToricCY";

client=MongoClient("mongodb://"+username+":"+password+"@"+server+":"+port+"/"+dbname);
db=client[dbname];

statepath="/gss_gpfs_scratch/altman.ro/ToricCY/packages/state/";

tiersstream=open(statepath+"tiers","r");
ToricCYTiers=[x.rstrip("\n") for x in tiersstream.readlines()];
tiersstream.close();

indexesstream=open(statepath+"indexes","r");
ToricCYIndexes=[x.rstrip("\n") for x in indexesstream.readlines()];
indexesstream.close();
'''