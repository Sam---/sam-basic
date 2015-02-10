#!/bin/sh

deploydest="/home/$USER/bin/sambasic" 

if [ -L "$deploydest" -o ! -e "$deploydest" ]
then
    unlink "$deploydest"
    ln "sambasic.py" "$deploydest"
elif [ -e "$deploydest" ]
    echo File exists
    exit 1
else 
