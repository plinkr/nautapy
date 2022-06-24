#!/bin/bash
killall openvpn 2> /dev/null
while killall -q -0 openvpn; do
  sleep 1
done
exit 0
