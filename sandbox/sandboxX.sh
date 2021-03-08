#!/bin/bash
trap "" TERM
context=`id -Z | secon -t -l -P`
export TITLE="Sandbox $context -- `grep ^#TITLE: ~/.sandboxrc | /usr/bin/cut -b8-80`"
[ -z $1 ] && export SCREENSIZE="1000x700" || export SCREENSIZE="$1"
[ -z $2 ] && export DPI="96" || export DPI="$2"
trap "exit 0" HUP

(/usr/bin/Xephyr -resizeable -title "$TITLE" -terminate -reset -screen $SCREENSIZE -dpi $DPI -nolisten tcp -displayfd 5 5>&1 2>/dev/null) | while read D; do
    export DISPLAY=:$D
    cat > ~/seremote << __EOF
#!/bin/sh
DISPLAY=$DISPLAY "\$@"
__EOF
    chmod +x ~/seremote
    /usr/share/sandbox/start $HOME/.sandboxrc
    export EXITCODE=$?
    kill -TERM 0
    break
done
exit 0
