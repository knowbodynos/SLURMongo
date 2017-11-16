# DBCrunch
This package is an API linking the SLURM workload manager with MongoDB, in order to optimize the staged, parallel processing of large amounts of data.
The data is streamed directly from a remote MongoDB database, processed on a high-performance computing cluster running SLURM, and fed directly back to the remote database along with statistics such as CPU time, max memory used, and storage.

------------------------------------------------------------------------------------------------------------

Installation instructions for the Massachusetts Green High Performance Computing Center's Discovery cluster:

1) Make sure that the directory `/gss_gpfs_scratch/${USER}` exists. If not, then create it using:

```
   mkdir /gss_gpfs_scratch/${USER}
```

2) Add the following lines to `${HOME}/.bashrc`:

```
   module load gnu-4.4-compilers 
   module load fftw-3.3.3
   module load platform-mpi
   module load perl-5.20.0
   module load slurm-14.11.8
   module load gnu-4.8.1-compilers
   module load boost-1.55.0
   module load python-2.7.5
   module load oracle_java_1.7u40
   module load hadoop-2.4.1
   module load mathematica-10
   module load cuda-7.0
   module load sage-7.4

   export USER_LOCAL=${HOME}/opt
   #export SAGE_ROOT=/shared/apps/sage/sage-5.12
   export SAGE_ROOT=/shared/apps/sage-7.4
   export CRUNCH_ROOT=/gss_gpfs_scratch/${USER}/DBCrunch
   export PATH=${USER_LOCAL}/bin:${CRUNCH_ROOT}/bin:${PATH}
```

3) Restart your Discovery session OR run the command `source ${HOME}/.bashrc`.

4) Activate Mathematica 10.0.2 by performing the following steps:
    
   a) SSH into Discovery using the "-X" flag (i.e. `ssh -X (your_username)@discovery2.neu.edu`)

   b) Allocate a node on some partition (e.g. `interactive-10g`) for an interactive job using the command:

   ```
      salloc --no-shell -N 1 --exclusive -p (some_partition)
   ```

   After a moment, you will see the message *salloc: Granted job allocation (some_JOBID)*.

   c) Enter the command:

   ```
      squeue -u ${USER} -o "%.100N" -j (some_JOBID)
   ```

   In the column labeled *NODELIST*, you will see the hostname of your allocated interactive job.

   d) Login to this host with the command:
    
   ```
      ssh -X (some_hostname)
   ```

   e) Launch the Mathematica 10.0 GUI using the command:

   ```
      mathematica &
   ```
   
      You will see an "*Activate online*" window. Select the "*Other ways to activate*" button. Then select the third option "*Connect to a network license server*". In the Server name box enter `discovery2` and then select the "*Activate*" button. After this check the "*I accept the terms of the agreement*" box and select the "*OK*" button. Now your user account is configured to use Mathematica 10.0.2 on the Discovery Cluster.

5) Install Mathematica and Python components by running the command `${CRUNCH_ROOT}/install.bash` from a login node.


6) View the available modules using `ls ${CRUNCH_ROOT}/templates` and choose the module (i.e., *controller_(some_module_name)_template.job*) that you wish to run.

   The MongoDB database name, username, and password will be defined in this file (dbname, dbusername, dbpassword). If your database is unauthenticated, leave dbusername blank.

   For testing purposes, please modify `controller_(some_module_name)_template.job` by finding the lines defining the variables *dbpush* and *markdone*. Change them to:

```
   writedb="False"
   statsdb="False"
   markdone=""
```

   This prevents the controller from writing the results back to the remote MongoDB database. When you are finished testing, you can change these back to:
   
```
   writedb="True"
   statsdb="True"
   markdone="MARK"
```

7) To copy the template to a usable format, run the following command:
   
```
   ${CRUNCH_ROOT}/scripts/tools/copy_template.bash (some_module_name) (some_controller_name)
```
   
   where, in practice, *(some_controller_name)* is the value of H11 (i.e., 1 through 6) that we wish to run the module on.

   *(Note: If you choose to copy the template manually, you will also have to expand `${CRUNCH_ROOT}` inside the `#SBATCH -D` keyword of the `controller_(some_module_name)_template.job` file in order for SLURM to be able to process it.)*

8) The template has now been copied to the directory `${CRUNCH_ROOT}/modules/(some_module_name)/(some_controller_name)`. Navigate here, and you can now submit the job using the command:

```
   sbatch controller_(some_module_name)_(some_controller_name).job
```
   
9) If you need to cancel and completely reset the controller job to initial conditions, make sure you run the command:

```
   ./reset.bash
```
   
   before resubmitting the job.
   
------------------------------------------------------------------------------------------------------------

Some useful aliases to keep in the `${HOME}/.bashrc` file:

```
#Functions
_scancelgrep() {
    nums=$(squeue -h -u ${USER} -o "%.100P %.100j %.100i %.100t %.100T" | grep $1 | sed "s/\s\s\s*//g" | cut -d" " -f1)
    for n in $nums
    do
        scancel $n
    done
}

_sfindpart() {
    greppartitions="ser-par-10g|ser-par-10g-2|ser-par-10g-3|ser-par-10g-4|ht-10g|interactive-10g"

    partitionsidle=$(sinfo -h -o '%t %c %D %P' | grep -E "(${greppartitions})\*?\s*$" | grep 'idle' | awk '$0=$1" "$2*$3" "$4' | sort -k2,2nr | cut -d' ' -f3 | sed 's/\*//g' | tr '\n' ' ' | head -c -1)
    partitionscomp=$(sinfo -h -o '%t %c %D %P' | grep -E "(${greppartitions})\*?\s*$" | grep 'comp' | awk '$0=$1" "$2*$3" "$4' | sort -k2,2nr | cut -d' ' -f3 | sed 's/\*//g' | tr '\n' ' ' | head -c -1)
    read -r -a orderedpartitions <<< "${partitionsidle} ${partitionscomp}"

    for i in "${!orderedpartitions[@]}"
    do
        flag=true
        for partition in "${orderedpartitions[@]::$i}"
        do
            [[ "$partition" == "${orderedpartitions[$i]}" ]] && flag=false
        done
        if [ "$flag" = true ]
        then
            echo ${orderedpartitions[$i]}
        fi
    done
}

_sfindpartall() {
    greppartitions="ser-par-10g|ser-par-10g-2|ser-par-10g-3|ser-par-10g-4|ht-10g|interactive-10g"

    partitionsidle=$(sinfo -h -o '%t %c %D %P' | grep -E "(${greppartitions})\*?\s*$" | grep 'idle' | awk '$0=$1" "$2*$3" "$4' | sort -k2,2nr | cut -d' ' -f3 | sed 's/\*//g' | tr '\n' ' ' | head -c -1)
    partitionscomp=$(sinfo -h -o '%t %c %D %P' | grep -E "(${greppartitions})\*?\s*$" | grep 'comp' | awk '$0=$1" "$2*$3" "$4' | sort -k2,2nr | cut -d' ' -f3 | sed 's/\*//g' | tr '\n' ' ' | head -c -1)
    partitionsrun=$(squeue -h -o '%L %T %P' | grep -E "(${greppartitions})\*?\s*$" | grep 'RUNNING' | sed 's/^\([0-9][0-9]:[0-9][0-9]\s\)/00:\1/g' | sed 's/^\([0-9]:[0-9][0-9]:[0-9][0-9]\s\)/0\1/g' | sed 's/^\([0-9][0-9]:[0-9][0-9]:[0-9][0-9]\s\)/0-\1/g' | sort -k1,1 | cut -d' ' -f3 | tr '\n' ' ' | head -c -1)
    partitionspend=$(sinfo -h -o '%t %c %P' --partition=$(squeue -h -o '%T %P' | grep -E "(${greppartitions})\*?\s*$" | grep 'PENDING' | sort -k2,2 -u | cut -d' ' -f2 | tr '\n' ',' | head -c -1) | grep 'alloc' | sort -k2,2n | cut -d' ' -f3 | sed 's/\*//g' | tr '\n' ' ' | head -c -1)

    read -r -a orderedpartitions <<< "${partitionsidle} ${partitionscomp} ${partitionsrun} ${partitionspend}"

    for i in "${!orderedpartitions[@]}"
    do
        flag=true
        for partition in "${orderedpartitions[@]::$i}"
        do
            [[ "$partition" == "${orderedpartitions[$i]}" ]] && flag=false
        done
        if [ "$flag" = true ]
        then
            echo ${orderedpartitions[$i]}
        fi
    done
}

_sinteract(){
    jobnum=$(echo $(salloc --no-shell -N 1 --exclusive -p $1 2>&1) | sed "s/.* allocation \([0-9]*\).*/\1/g"); ssh -X $(squeue -h -u ${USER} -j $jobnum -o %.100N | sed "s/\s\s\s*/ /g" | rev | cut -d" " -f1 | rev); scancel $jobnum;
}

_watchjobs() {
    jobs=$(squeue -u ${USER} -o "%.10i %.13P %.130j %.8u %.2t %.10M %.6D %R" -S "P,-t,-p" | tr '\n' '!' 2>/dev/null)
    njobs=$(echo ${jobs} | tr '!' '\n' 2>/dev/null | grep "_steps_" | wc -l)
    if [ "${njobs}" -gt 0 ]
    then
        nrunjobs=$(echo ${jobs} | tr '!' '\n' 2>/dev/null | grep "_steps_" | grep " R " | wc -l)
        npendjobs=$(echo ${jobs} | tr '!' '\n' 2>/dev/null | grep "_steps_" | grep " PD " | wc -l)
        steps=$(sacct -o "JobID%30,JobName%130,State" --jobs=$(echo ${jobs} | tr '!' '\n' 2>/dev/null | grep "_steps_" | sed "s/\s\s*/ /g" | cut -d" " -f2 | tr '\n' ',' | head -c -1) 2>/dev/null | grep -v "stats_" | grep -E "\."  | tr '\n' '!' 2>/dev/null)
        nrunsteps=$(echo ${steps} | tr '!' '\n' 2>/dev/null | grep "RUNNING" | wc -l)
        pendsteps=$(echo ${jobs} | tr '!' '\n' 2>/dev/null | grep "_steps_" | grep " PD " | sed "s/\s\s*/ /g" | cut -d" " -f4 | rev | cut -d"_" -f1 | rev | sed 's/^\(.*\)$/\1-1/g' | tr "\n" "+" | head -c -1)
        if [[ "${pendsteps}" == "" ]]
        then
            npendsteps=0
        else
            npendsteps=$(echo "-(${pendsteps})" | bc)
        fi
    else
        nrunjobs=0
        npendjobs=0
        nrunsteps=0
        npendsteps=0
    fi
    nsteps=$(($nrunsteps+$npendsteps))
    echo "# Jobs: ${njobs}   # Run Jobs: ${nrunjobs}   # Pend Jobs: ${npendjobs}"
    echo "# Steps: ${nsteps}   # Run Steps: ${nrunsteps}   # Pend Steps: ${npendsteps}"
    echo ""
    #squeue -u ${USER} -o "%.10i %.13P %.130j %.8u %.2t %.10M %.6D %R" -S "P,-t,-p"
    echo "${jobs}" | tr '!' '\n' 2>/dev/null
}
export -f _watchjobs

_swatch() {
    watch -n$1 bash -c "_watchjobs"
}

_bwatchjobs() {
    jobs=$(squeue -u ${USER} -o "%.10i %.13P %.130j %.8u %.2t %.10M %.6D %R" -S "P,-t,-p" | tr '\n' '!' 2>/dev/null)

    for controller in $(echo ${jobs} | tr '!' '\n' 2>/dev/null | tail -n +2 | grep " controller_" | sed 's/\s\s*/ /g' | cut -d' ' -f4 | cut -d'_' -f2,3)
    do
        modname=$(echo ${controller} | cut -d'_' -f1)
        controllername=$(echo ${controller} | cut -d'_' -f2)
        workpath="${CRUNCH_ROOT}/modules/${modname}/${controllername}/jobs"
        temps=$(cat ${workpath}/*.log 2>/dev/null | grep "<TEMP" | wc -l)
        outs=$(cat ${workpath}/*.log 2>/dev/null | grep "<OUT" | wc -l)
        docs=$(cat ${workpath}/*.docs 2>/dev/null | wc -l)
        echo "${controller}"
        if [ "${docs}" -gt 0 ]
        then 
            tempsperc=$(echo "scale=2;(100*${temps})/${docs}" | bc)
            echo "${tempsperc}% Processing: ${temps} of ${docs}"
            outsperc=$(echo "scale=2;(100*${outs})/${docs}" | bc)
            echo "${outsperc}% Finished: ${outs} of ${docs}"
        fi
        echo "Size: $(du -ch ${workpath} 2>/dev/null | tail -n1 | sed 's/\s\s*/ /g' | cut -d' ' -f1)"
        echo ""
    done
    njobs=$(echo ${jobs} | tr '!' '\n' 2>/dev/null | grep "_steps_" | wc -l)
    if [ "${njobs}" -gt 0 ]
    then
        nrunjobs=$(echo ${jobs} | tr '!' '\n' 2>/dev/null | grep "_steps_" | grep " R " | wc -l)
        npendjobs=$(echo ${jobs} | tr '!' '\n' 2>/dev/null | grep "_steps_" | grep " PD " | wc -l)
        steps=$(sacct -o "JobID%30,JobName%130,State" --jobs=$(echo ${jobs} | tr '!' '\n' 2>/dev/null | grep "_steps_" | sed "s/\s\s*/ /g" | cut -d" " -f2 | tr '\n' ',' | head -c -1) 2>/dev/null | grep -v "stats_" | grep -E "\."  | tr '\n' '!' 2>/dev/null)
        nrunsteps=$(echo ${steps} | tr '!' '\n' 2>/dev/null | grep "RUNNING" | wc -l)
        pendsteps=$(echo ${jobs} | tr '!' '\n' 2>/dev/null | grep "_steps_" | grep " PD " | sed "s/\s\s*/ /g" | cut -d" " -f4 | rev | cut -d"_" -f1 | rev | sed 's/^\(.*\)$/\1-1/g' | tr "\n" "+" | head -c -1)
        if [[ "${pendsteps}" == "" ]]
        then
            npendsteps=0
        else
            npendsteps=$(echo "-(${pendsteps})" | bc)
        fi
    else
        nrunjobs=0
        npendjobs=0
        nrunsteps=0
        npendsteps=0
    fi
    nsteps=$(($nrunsteps+$npendsteps))
    echo "# Jobs: ${njobs}   # Run Jobs: ${nrunjobs}   # Pend Jobs: ${npendjobs}"
    echo "# Steps: ${nsteps}   # Run Steps: ${nrunsteps}   # Pend Steps: ${npendsteps}"
    echo ""
    #squeue -u ${USER} -o "%.10i %.13P %.130j %.8u %.2t %.10M %.6D %R" -S "P,-t,-p"
    echo "${jobs}" | tr '!' '\n' 2>/dev/null
}
export -f _bwatchjobs

_bwatch() {
    watch -n$1 bash -c "_bwatchjobs"
}

_watchoutput() {
    jobdir=$1
    nlines=$2
    isreload=$3
    permspace=$(du -ch ${jobdir}/*.log ${jobdir}/*.job ${jobdir}/*.err ${jobdir}/*.docs ${jobdir}/*.merge.*.out 2>/dev/null | tail -n1 | sed 's/\s\s*/ /g' | cut -d' ' -f1)
    tempspace=$(du -ch ${jobdir}/*.batch.*.temp ${jobdir}/*.batch.*.out ${jobdir}/*.merge.*.in ${jobdir}/*.merge.*.temp ${jobdir}/*.err.docs ${jobdir}/*.err.out 2>/dev/null | tail -n1 | sed 's/\s\s*/ /g' | cut -d' ' -f1)
    datetime=$(date '+%Y.%m.%d:%H.%M.%S')
    #loglines=$(cat ${jobdir}/*.log 2>/dev/null | sort -t':' -s -k1,2 -k3,3n -k4,4n)
    logfirstlines=$(for logfile in $(ls ${jobdir}/*.log 2>/dev/null); do head -n 1 ${logfile}; done | sort -t':' -s -k1,2 -k3,3n -k4,4n)
    lognextlines=$(for logfile in $(ls ${jobdir}/*.log 2>/dev/null); do tail -n $((${nlines}-13)) ${logfile}; done | sort -t':' -s -k1,2 -k3,3n -k4,4n)
    firstline=$(echo "${logfirstlines}" | head -n 1)
    nextlines=$(echo "${lognextlines}" | tail -n +2 | tail -n $((${nlines}-13)))
    docsproc=$(find ${jobdir}/ -maxdepth 1 -type f -regextype posix-egrep -regex ".*_step_[0-9]+\.batch\.[0-9]+\.(temp|out)" 2>/dev/null | xargs cat 2>/dev/null | grep "@" | wc -l)
    docscoll=$(find ${jobdir}/ -maxdepth 1 -type f -regex ".*\.merge\.[0-9]+\.in" 2>/dev/null | xargs cat 2>/dev/null | grep "@" | wc -l)
    docscomp=$(find ${jobdir}/ -maxdepth 1 -type f -regex ".*\.merge\.[0-9]+\.out" 2>/dev/null | xargs cat 2>/dev/null | grep "@" | wc -l)
    docswrit=$(($docscomp+$(find ${jobdir}/ -maxdepth 1 -type f -regex ".*\.merge\.[0-9]+\.temp" 2>/dev/null | xargs cat 2>/dev/null | grep "@" | wc -l)))
    if [ "${isreload}" == 1 ]
    then
        docsrem=$(find ${jobdir}/ -maxdepth 1 -type f -regextype posix-egrep -regex "(.*_step_[0-9]+\.docs|.*_step_[0-9]+\.batch\.[0-9]+\.docs|.*\.merge\.[0-9]+\.in)" 2>/dev/null | xargs cat 2>/dev/null | grep "@" | wc -l)
        batchesfail=$(find ${jobdir}/ -maxdepth 1 -type f -regex ".*_step_[0-9]+\.batch\.[0-9]+\.err\.docs" 2>/dev/null | xargs cat 2>/dev/null | grep "@" | wc -l)
        mergesfail=$(find ${jobdir}/ -maxdepth 1 -type f -regex ".*\.merge\.[0-9]+\.err\.docs" 2>/dev/null | xargs cat 2>/dev/null | grep "@" | wc -l)
    elif [ "${isreload}" == 0 ]
    then
        docsrembatch=$(find ${jobdir}/ -maxdepth 1 -type f -regextype posix-egrep -regex "(.*_step_[0-9]+\.docs|.*_step_[0-9]+\.batch\.[0-9]+\.docs)" 2>/dev/null | xargs cat 2>/dev/null | wc -l)
        docsrem=$((${docsrembatch}+${docscoll}))
        batchesfail=$(find ${jobdir}/ -maxdepth 1 -type f -regex ".*_step_[0-9]+\.batch\.[0-9]+\.err\.docs" 2>/dev/null | xargs cat 2>/dev/null | wc -l)
        mergesfail=$(find ${jobdir}/ -maxdepth 1 -type f -regex ".*\.merge\.[0-9]+\.err\.docs" 2>/dev/null | xargs cat 2>/dev/null | wc -l)
    fi
    echo "${firstline}"
    echo "${nextlines}"
    echo ""
    echo "${datetime}: ${permspace} Permanent Space"
    echo "${datetime}: ${tempspace} Temporary Space"
    echo "${datetime}: ${docsproc} Documents Processed"
    echo "${datetime}: ${docscoll} Documents Collected"
    echo "${datetime}: ${docswrit} Documents Written (In Progress)"
    echo "${datetime}: ${docscomp} Documents Written (Complete)"
    echo "${datetime}: ${docsrem} Documents Remaining"
    echo "${datetime}: ${batchesfail} Batches Failed"
    echo "${datetime}: ${mergesfail} Merges Failed"
}
export -f _watchoutput

_owatch() {
    nseconds=$3
    nlines=$2
    modname=$(echo $1 | rev | cut -d'/' -f2 | rev)
    controllername=$(echo $1 | rev | cut -d'/' -f1 | rev)
    jobdir=$1/jobs
    queries=$(cat "$1/controller_${modname}_${controllername}.job" | grep "queries=" | cut -d'=' -f2)
    if [[ "${queries}" =~ .*'RELOAD'.* ]]
    then
        isreload=1
    else
        isreload=0
    fi   
    watch -n$nseconds "_watchoutput $jobdir $nlines $isreload"
}

_siwatch(){
    jobnum=$(echo $(salloc --no-shell -N 1 --exclusive -p $1 2>&1) | sed "s/.* allocation \([0-9]*\).*/\1/g");
    ssh -t -X $(squeue -h -u ${USER} -j $jobnum -o %.100N | sed "s/\s\s\s*/ /g" | rev | cut -d" " -f1 | rev) "watch -n$2 bash -c \"_watchjobs\""
    scancel $jobnum
}

_step2job(){
    jobstepname=$1
    modname=$(echo ${jobstepname} | cut -d'_' -f1)
    controllername=$(echo ${jobstepname} | cut -d'_' -f2)

    herepath=$(pwd)
    if [[ "${modname}" == "" ]] || [[ "${controllername}" == "" ]]
    then
        if [[ "${herepath}" == "${CRUNCH_ROOT}/modules/"* ]]
        then
            read modname controllername <<<$(echo "${herepath/${CRUNCH_ROOT}\/modules\//}" | tr '/' ' ' | cut -d' ' -f1,2)
            if [[ "${modname}" != "" ]] && [[ "${controllername}" != "" ]]
            then
                parentids=$(cat "${CRUNCH_ROOT}/modules/${modname}/${controllername}/controller_${modname}_${controllername}.out" | grep "${jobstepname}" | perl -pe 's/^.*job step (.*?)\..*$/\1/g' | tr '\n' '|' | head -c -1)
                cat "${CRUNCH_ROOT}/modules/${modname}/${controllername}/controller_${modname}_${controllername}.out" | grep -E "Submitted batch job (${parentids})" | perl -pe 's/^.* as (.*?) on.*$/\1/g'
            fi
        fi
    else
        parentids=$(cat "${CRUNCH_ROOT}/modules/${modname}/${controllername}/controller_${modname}_${controllername}.out" | grep "${jobstepname}" | perl -pe 's/^.*job step (.*?)\..*$/\1/g' | tr '\n' '|' | head -c -1)
        cat "${CRUNCH_ROOT}/modules/${modname}/${controllername}/controller_${modname}_${controllername}.out" | grep -E "Submitted batch job (${parentids})" | perl -pe 's/^.* as (.*?) on.*$/\1/g'
    fi
}

_requeuedocs(){
    #loadfilenames=$(find ./jobs/ -maxdepth 1 -type f -name "*.docs" | rev | cut -d'/' -f1 | rev | tr '\n' ',')
    loadfilenames=$(find ./jobs/ -maxdepth 1 -type f -name "*.docs" | rev | cut -d'/' -f1 | rev)
    #loadfilejobpatt=$(echo ${loadfilenames} | tr ',' '\n' | sed 's/\(.*_job_[0-9]*\).*/\1/g' | sort -u)
    #mkdir ./jobs/requeued 2>/dev/null
    #for patt in ${loadfilejobpatt}
    #do
    #    mv ./jobs/${patt}* ./jobs/requeued/ 2>/dev/null
    #done
    #for loadfilename in $(echo ${loadfilenames} | tr ',' '\n')
    for loadfilename in ${loadfilenames}
    do
        if [[ "${loadfilename}" =~ .*".err".* ]]
        then
            #errcode=$(cat ./jobs/requeued/${loadfilename/.docs/.out} | grep "ExitCode: " | cut -d' ' -f2)
            errcode=$(cat ./jobs/${loadfilename/.docs/.out} | grep "ExitCode: " | cut -d' ' -f2)
        else
            errcode="-1:0"
        fi
        echo "${loadfilename},${errcode},True"
    done >> ./skippedstate
}

#Aliases
#alias sage='source /shared/apps/sage/sage-5.12/sage'
alias lsx='watch -n 5 "ls"'
alias sjob='squeue -u ${USER} -o "%.10i %.13P %.130j %.8u %.2t %.10M %.6D %R" -S "P,-t,-p"'
alias djob='jobids=$(squeue -h -u ${USER} | grep -v "(null)" | sed "s/\s\s\s*//g" | cut -d" " -f1); for job in $jobids; do scancel $job; echo "Cancelled Job $job."; done'
alias scancelgrep='_scancelgrep'
alias sfindpart='_sfindpart'
alias sfindpartall='_sfindpartall'
alias sinteract='_sinteract'
alias swatch='_swatch'
alias bwatch='_bwatch'
alias owatch='_owatch $(pwd) ${LINES}'
alias siwatch='_siwatch'
alias scratch='cd /gss_gpfs_scratch/${USER}'
alias quickclear='perl -e "for(<*>){((stat)[9]<(unlink))}"'
alias step2job='_step2job'
alias statreset='cat *.stat | sed "s/False/True/g" >> ../skippedstate'
alias requeuedocs='_requeuedocs'
```
