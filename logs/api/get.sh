#!/bin/bash

# Example pulling down the list of logs and then downloading from that list
# here.
# swift list production-juju-ps45-cdo-jujucharms-machine-1.canonical.com G 201610 G api.jujucharms.com.log > logs1.list
# swift list production-juju-ps45-cdo-jujucharms-machine-2.canonical.com G 201610 G api.jujucharms.com.log > logs2.list

ERROR="Need to source the novarc"
: ${NOVA_USERNAME:?$ERROR}

FILES=`cat logs1.list`
cd 1
for f in $FILES
do
  echo "swift download $f"
  swift download production-juju-ps45-cdo-jujucharms-machine-1.canonical.com $f
done

cd ..
FILES=`cat logs2.list`
cd 2
for f in $FILES
do
  echo "swift download $f"
  swift download production-juju-ps45-cdo-jujucharms-machine-2.canonical.com $f
done
