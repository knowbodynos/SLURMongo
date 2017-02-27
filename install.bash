#!/bin/bash

initfile=$(math -noprompt -run "WriteString[\$Output,\$UserBaseDirectory<>\"/Kernel/init.m\"];Exit[];")
echo $(cat $initfile | grep -v "SLURMONGO_ROOT") > $initfile
echo "AppendTo[\$Path, Environment[\"SLURMONGO_ROOT\"]<>\"/packages/Mathematica/cohomCalg\"]" >> $initfile
echo "AppendTo[\$Path, Environment[\"SLURMONGO_ROOT\"]<>\"/packages/Mathematica/MongoLink\"]" >> $initfile

pythonpath="${SLURMONGO_ROOT}/packages/python"

currdir=$(pwd)
cd ${pythonpath}
rm -r ${pythonpath}/mongo-python-driver-2.8 2>/dev/null
wget https://github.com/mongodb/mongo-python-driver/archive/2.8.tar.gz
wait
tar xzfv 2.8
rm 2.8
cd mongo-python-driver-2.8
python setup.py install --user --record filespy.txt
sage --python setup.py install --user --record filessage.txt
cd ${pythonpath}/mongolink
python setup.py install --user --record filespy.txt
sage --python setup.py install --user --record filessage.txt
cd ${currdir}