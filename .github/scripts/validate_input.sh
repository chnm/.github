#!/bin/sh

if [ -n "$WEBSITE_FQDN" ]; then
  case "$WEBSITE_FQDN" in
    "deathbynumbers.org"|\
    "mathhumanists.org"|\
    "test1.rrchnm.org")
        exit 0
    ;;
    *)
        exit 1
    ;;
  esac
fi

exit 1

