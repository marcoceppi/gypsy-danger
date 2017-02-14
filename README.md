Pull various Juju KPI data in and report on it
=====

The goal of this project is to provide tools and scripts to help measure the
trend of Juju usage, interaction, and growth.

Long running instance data
------
This script is used to check our API logs for api.jujucharms.com and to judge
how many anonymous models are running, how long they've been up for, what
versions of juju they're on, and what clouds/regions are they located in.

To get started you need to get the log files onto the system. For this you
need credentials to the charmstore logs via swift. These can be obtained by
getting them created in enigma via an RT ticket.


Steps to get the system setup for reporting:

  make sysdeps
  make
  source ~/path/to/novarc/for/swift
  make get-logs
  make _initdb
  make longrunning


make longrunning
~~~~~
This triggers the longrunning.py script which will dump all known data out to
the terminal. This is made up of many different queries that can be made
against the log data that's been pulled down and put parsed with `_initdb`.

  long-running/longrunning.py run summary
  long-running/longrunning.py run latest-summary
  long-running/longrunning.py run model-ages
  long-running/longrunning.py run models-per-day
  long-running/longrunning.py run latest-versions
  long-running/longrunning.py run latest-clouds
  long-running/longrunning.py run latest-clouds-regions


- summary: how many models have we seen in the db 
- latest-summary: for the latest day, how many models were seen
- model-ages: for all model uuids found how many days old are they
- models-per-day: for each day how many models were seen on each day
- latest-versions: for the latest day, how many models are on which versions of Juju
- latest-clouds: for the latest day, what clouds were those models on
- latest-clouds-regions: latest-clouds with a breakdown per region of the cloud
