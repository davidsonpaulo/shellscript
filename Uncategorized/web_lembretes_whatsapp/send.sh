#!/bin/bash

FileList=(
    "./app.py"
    "./common.py"
    "./config.txt"
    "./requirements.txt"
    "./snippets.txt"
    "./static/css/style.css"
    "./static/js/main.js"
    "./templates/index.html"
    "./templates.txt"
)


for (( i=0 ; i<${#FileList[@]} ; i++ )) ; do
    File="${FileList[$i]}"
    Destination="send/$(basename "$File")"
    Extension="$(echo "$File" | rev | cut -d. -f1 | rev)"
    
    if [ "$Extension" != "txt" ] ; then
        Destination="${Destination}.txt"
    fi

    cp -v "$File" "$Destination"
done

exit 0
