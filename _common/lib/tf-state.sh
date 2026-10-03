#!/usr/bin/env bash
# Shared Terraform state helpers for per-provider plugin commands.
# Provider-agnostic: each per-provider command supplies its own stack
# candidate paths.
#
# Usage:
#   . plugins/providers/_common/lib/tf-state.sh
#
# Functions: eve_tf_attr, eve_tf_state_json

EVE_TM_READ_FLAGS=(
  --disable-safeguards=git-untracked
  --disable-safeguards=git-uncommitted
  --disable-safeguards=git-out-of-sync
  --disable-safeguards=outdated-code
)

# eve_tf_attr <state_json> <address> <attribute>
# Pulls a single attribute from a terraform-show JSON blob.
eve_tf_attr() {
  local json="$1" address="$2" attr="$3"
  printf '%s' "$json" | jq -r --arg addr "$address" --arg attr "$attr" \
    '[((.values // {} | .root_module // {} | .resources // [])
       | map(select(.address == $addr))
       | map(.values[$attr])[]?),
      ((.resources // [])
       | map(select((.type + "." + .name) == $addr))
       | map(.instances[]?.attributes[$attr])[]?)]
     | map(select(. != null and . != ""))
     | first // ""' 2>/dev/null
}

# eve_tf_state_json <tags> <stack-candidate-1> [<stack-candidate-2> ...]
# Returns the terraform state JSON for the instance. In instance mode, reads the
# explicit state path first; otherwise generates Terramate code and asks
# terraform for normalized state JSON.
eve_tf_state_json() {
  local tags="$1"; shift
  local candidates=("$@")
  local state_json="" state_path="" workspace="${TF_WORKSPACE:-default}"

  if [ -n "${EVE_TF_STATE_BASE:-}" ]; then
    local candidate
    for candidate in "${candidates[@]}"; do
      state_path="${EVE_TF_STATE_BASE}/${candidate}/workspaces/${workspace}/terraform.tfstate"
      if [ -f "$state_path" ]; then
        cat "$state_path"
        return 0
      fi

      state_path="${EVE_TF_STATE_BASE}/${candidate}/default.tfstate"
      if [ -f "$state_path" ]; then
        cat "$state_path"
        return 0
      fi
    done
    # An explicit instance state directory with no state is an absent instance.
    # Do not query a different backend or workspace behind the caller's back.
    return 0
  fi

  terramate generate >/dev/null || return $?
  state_json=$(terramate run "${EVE_TM_READ_FLAGS[@]}" --quiet --tags="$tags-services" -- terraform show -json) || return $?
  if [ -z "$state_json" ]; then
    return 0
  fi
  if printf '%s\n' "$state_json" | jq -e . >/dev/null 2>&1; then
    printf '%s\n' "$state_json"
    return 0
  fi
  echo "Cannot parse Terraform state response" >&2
  return 1
}
