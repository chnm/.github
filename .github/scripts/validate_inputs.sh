#!/bin/sh

# this shell script will validate inputs used in the reusable workflows located
# under .github/workflows/* and expects the inputs to be passed via environment variables.
# i.e. hacky way to restrict input values

# validate website-fqdn input used in hugo build-release-deploy workflow
if [ -n "$WEBSITE_FQDN" ]; then
  case "$WEBSITE_FQDN" in
    "data.chnm.org"|\
    "dev.apiary.rrchnm.org"|\
    "civilwargraffiti.org"|\
    "dev.civilwargraffiti.org"|\
    "connectingthreads.co.uk"|\
    "dev.connectingthreads.co.uk"|\
    "dev.connectingthreads.rrchnm.org"|\
    "crdh.rrchnm.org"|\
    "cyh.rrchnm.org"|\
    "dev.crdh.rrchnm.org"|\
    "datascribe.tech"|\
    "deathbynumbers.org"|\
    "dev.deathbynumbers.org"|\
    "denigmanuscript.org"|\
    "digitalcampus.tv"|\
    "earlymodernviolence.org"|\
    "dev.earlymodernviolence.org"|\
    "dev.lasfera.rrchnm.org"|\
    "lasfera.rrchnm.org"|\
    "mathhumanists.org"|\
    "dev.outandabout.rrchnm.org"|\
    "religiousecologies.org"|\
    "dev.religiousecologies.org"|\
    "database.religiousecologies.org"|\
    "dev.database.religiousecologies.org"|\
    "dev.winterthur.rrchnm.org"|\
    "static.rrchnm.org"|\
    "test.rrchnm.site"|\
    "devl.rrchnm.site")
        exit 0
    ;;
    *)
        exit 1
    ;;
  esac
fi

exit 1

