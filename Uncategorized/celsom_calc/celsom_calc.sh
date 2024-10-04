#!/bin/bash

Executable="$(realpath "$0")"
Basedir="$(dirname "$Executable")"

cd "$Basedir"
./celsom_calc.py
exit $?
