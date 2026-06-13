#!/bin/sh
set -eu

# Validates inputs used by the reusable workflows under .github/workflows/*.
# Inputs are passed via environment variables; this is a deliberately strict
# allowlist that restricts which values the deploy jobs are permitted to act on.
#
# Currently validated:
#   WEBSITE_FQDN  -- must exactly match an entry in scripts/allowed_fqdns.txt
#
# Exit status: 0 if every checked input is valid, 1 otherwise (with a reason
# printed to stderr so failures are diagnosable from the workflow log).

ALLOWLIST="$(dirname "$0")/allowed_fqdns.txt"

# Validate WEBSITE_FQDN against the allowlist file. Comments (#... ), blank
# lines and surrounding whitespace are ignored; matching is case-insensitive
# and exact (no globbing), so grouping/annotating the list is free.
validate_website_fqdn() {
  value="${WEBSITE_FQDN:-}"
  if [ -z "$value" ]; then
    echo "validate_inputs: WEBSITE_FQDN is empty or unset" >&2
    return 1
  fi

  if [ ! -r "$ALLOWLIST" ]; then
    echo "validate_inputs: allowlist not found or unreadable: $ALLOWLIST" >&2
    return 1
  fi

  needle="$(printf '%s' "$value" | tr '[:upper:]' '[:lower:]')"
  while IFS= read -r line || [ -n "$line" ]; do
    entry="${line%%#*}"                                   # strip inline/full comments
    entry="$(printf '%s' "$entry" | tr -d '[:space:]')"   # trim all whitespace
    [ -n "$entry" ] || continue
    entry="$(printf '%s' "$entry" | tr '[:upper:]' '[:lower:]')"
    if [ "$entry" = "$needle" ]; then
      return 0
    fi
  done < "$ALLOWLIST"

  echo "validate_inputs: WEBSITE_FQDN '$value' is not in the allowlist ($ALLOWLIST)" >&2
  return 1
}

validate_website_fqdn
