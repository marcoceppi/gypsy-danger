#!/bin/bash


source $HOME/archive-anon-cdo-jujucharms-ro.novarc

FILES=`cat logs1.list`
cd 1/
for f in $FILES
do
  echo "swift download $f"
  swift download production-juju-ps45-cdo-jujucharms-machine-1.canonical.com $f
done

FILES=`cat logs2.list`
cd 2/
for f in $FILES
do
  echo "swift download $f"
  swift download production-juju-ps45-cdo-jujucharms-machine-2.canonical.com $f
done
