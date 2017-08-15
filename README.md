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


Getting setup
~~~~

  make sysdeps
  make .venv
  source ~/path/to/novarc/for/swift
  source .venv/bin/activate
  make get-logs
  make _initdb
  make updatedb


Loading new logs
~~~~

Once running you can download the latest log files and update your database
with the following:

  source ~/path/to/novarc/for/swift
  source .venv/bin/activate
  make get-logs
  make updatedb
