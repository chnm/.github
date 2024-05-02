#!/bin/sh

# this shell script will validate inputs used in the reusable workflows located
# under .github/workflows/* and expects the inputs to be passed via environment variables.
# i.e. hacky way to restrict input values

# validate website-fqdn input used in hugo build-release-deploy workflow
if [ -n "$WEBSITE_FQDN" ]; then
  case "$WEBSITE_FQDN" in
    "connectingthreads.co.uk"|\
    "datascribe.tech"|\
    "dev.connectingthreads.co.uk"|\
    "deathbynumbers.org"|\
    "dev.deathbynumbers.org"|\
    "earlymodernviolence.org"|\
    "dev.earlymodernviolence.org"|\
    "dev.lasfera.rrchnm.org"|\
    "mathhumanists.org"|\
    "religiousecologies.org"|\
    "dev.religiousecologies.org"|\
    "test1.rrchnm.org")
        exit 0
    ;;
    *)
        exit 1
    ;;
  esac
fi

exit 1

