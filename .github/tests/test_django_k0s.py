"""Run with kustomize on PATH: uv run --with PyYAML==6.0.3 python this_file.py."""
import os
from pathlib import Path
import subprocess
import tempfile

import yaml

ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = ROOT / ".github/workflows"
workflow = yaml.load((WORKFLOWS / "django--k0s.yml").read_text(), Loader=yaml.BaseLoader)
pin_workflow = yaml.load((WORKFLOWS / "update-deploy-digests.yml").read_text(), Loader=yaml.BaseLoader)
IMAGE = "oci.rrchnm.internal/rrchnm/example"
DIGEST = "sha256:" + "1" * 64


def step(job, name):
    return next(item for item in job["steps"] if item.get("name") == name)["run"]


def run(script, directory, environment):
    return subprocess.run(
        ["bash", "-euo", "pipefail", "-c", script],
        cwd=directory, env={**os.environ, **environment}, capture_output=True, text=True,
    )


test = workflow["jobs"]["test"]
publish = workflow["jobs"]["publish"]
pin = workflow["jobs"]["pin"]
assert test["runs-on"] == "ubuntu-latest"
assert publish["runs-on"] == ["self-hosted", "IncusOS"]
assert publish["needs"] == "test"
assert publish["if"].strip() == (
    "(github.event_name == 'push' || github.event_name == 'workflow_dispatch') && "
    "github.ref == format('refs/heads/{0}', inputs.ref)"
)
assert pin["needs"] == "publish" and pin["with"]["guard-newest"] == "true"
assert pin["uses"] == "./.github/workflows/update-deploy-digests.yml"
assert pin_workflow["on"]["workflow_call"]["inputs"]["guard-newest"]["default"] == "false"
for job in (test, publish):
    checkout = job["steps"][0]
    assert checkout["with"]["persist-credentials"] == "false"
assert not any("secrets." in str(item) for item in test["steps"])
for item in test["steps"]:
    if item.get("uses", "").startswith("docker/build-push-action@"):
        assert item["with"]["push"] == "false"

with tempfile.TemporaryDirectory() as temporary:
    directory = Path(temporary)
    (directory / "k8s").mkdir()
    (directory / "Dockerfile").write_text("FROM scratch\n")
    original = (
        "apiVersion: kustomize.config.k8s.io/v1beta1\nkind: Kustomization\nimages:\n"
        f"  - name: {IMAGE}\n    digest: sha256:" + "0" * 64 + "\n"
    )
    overlay = directory / "k8s/kustomization.yaml"
    overlay.write_text(original)
    validation = step(test, "Validate deployment inputs")
    base = {"IMAGE": "rrchnm/example", "CONTEXT": ".", "OVERLAY": "k8s", "REF": "main"}
    assert run(validation, directory, base).returncode == 0
    for invalid in (
        {"IMAGE": "ghcr.io/chnm/example"}, {"IMAGE": "rrchnm/example:latest"},
        {"OVERLAY": "../k8s"}, {"OVERLAY": "/tmp/k8s"}, {"REF": "main bad"},
        {"CONTEXT": "../app"}, {"CONTEXT": "https://example.invalid/app.git"},
    ):
        assert run(validation, directory, {**base, **invalid}).returncode != 0, invalid

    # Mock remote Git only; use real Kustomize to verify the pinned artifact.
    (directory / "initial.yaml").write_text(original)
    binaries = directory / "bin"
    binaries.mkdir()
    git = binaries / "git"
    git.write_text("""#!/bin/bash
printf '%s\\n' "$*" >> "$MOCK_GIT_LOG"
case "$1" in
  fetch) echo fetch >> "$MOCK_ROOT/fetches" ;;
  merge-base) exit "${ANCESTOR_EXIT:-0}" ;;
  log)
    if [ "${REJECT_ONCE:-0}" = 1 ] && [ "$(wc -l < "$MOCK_ROOT/fetches")" -gt 1 ]; then
      echo "new source after a rejected push"
    else
      printf '%s\\n' "${NEWER_COMMITS:-}"
    fi ;;
  reset) cp "$MOCK_ROOT/initial.yaml" "$MOCK_ROOT/k8s/kustomization.yaml" ;;
  diff) cmp -s "$MOCK_ROOT/initial.yaml" "$MOCK_ROOT/k8s/kustomization.yaml" ;;
  push)
    if [ "${REJECT_ONCE:-0}" = 1 ] && ! [ -f "$MOCK_ROOT/rejected" ]; then
      touch "$MOCK_ROOT/rejected"
      exit 1
    fi ;;
esac
""")
    git.chmod(0o755)
    sleep = binaries / "sleep"
    sleep.write_text("#!/bin/sh\nexit 0\n")
    sleep.chmod(0o755)
    environment = {
        "PATH": str(binaries) + os.pathsep + os.environ["PATH"],
        "MOCK_ROOT": str(directory), "MOCK_GIT_LOG": str(directory / "git.log"),
        "DIGESTS": IMAGE + "@" + DIGEST, "OVERLAY": "k8s", "REF": "main",
        "GUARD_NEWEST": "true", "GITHUB_SHA": "a" * 40,
        "GITHUB_REPOSITORY": "chnm/example",
        "GIT_USER_NAME": "RRCHNM-Systems", "GIT_USER_EMAIL": "syschnm@gmu.edu",
    }
    script = step(pin_workflow["jobs"]["pin"], "Pin digests (re-edit on current tip + push, retried)")
    for overrides, expect_push in (
        ({}, True),
        ({"NEWER_COMMITS": "deploy: pin another/overlay images to 12345678"}, True),
        ({"NEWER_COMMITS": "fix: newer source"}, False),
        ({"ANCESTOR_EXIT": "1"}, False),
        ({"GUARD_NEWEST": "false", "NEWER_COMMITS": "fix: newer source"}, True),
        ({"DIGESTS": IMAGE + "-unknown@" + DIGEST}, False),
        ({"REJECT_ONCE": "1"}, True),
    ):
        for path in ("git.log", "fetches", "rejected"):
            (directory / path).unlink(missing_ok=True)
        overlay.write_text(original)
        result = run(script, directory, {**environment, **overrides})
        assert result.returncode == 0, result.stderr
        commands = (directory / "git.log").read_text().splitlines()
        assert any(command.startswith("push ") for command in commands) == expect_push, overrides
        if expect_push:
            document = yaml.safe_load(overlay.read_text())
            assert document["images"][0]["digest"] == DIGEST
            assert "add -- k8s/kustomization.yaml" in commands
        else:
            assert overlay.read_text() == original
        if overrides.get("REJECT_ONCE") == "1":
            assert sum(command.startswith("push ") for command in commands) == 1
            assert "newer source commits" in result.stdout

    docker = binaries / "docker"
    docker.write_text("""#!/bin/bash
[ "$*" = "login oci.rrchnm.internal --username ci --password-stdin" ] || exit 1
[ "$(cat)" = "test-only-token" ] || exit 1
printf '{}\\n' > "$DOCKER_CONFIG/config.json"
""")
    docker.chmod(0o755)
    credentials = step(publish, "Prepare isolated registry authentication")
    metadata = directory / "environment"
    outputs = directory / "outputs"
    auth_environment = {
        **environment, "RUNNER_TEMP": str(directory), "HOME": str(directory / "home"),
        "GITHUB_ENV": str(metadata), "GITHUB_OUTPUT": str(outputs),
        "BUILDX_BUILDER": "builder-test", "ZOT_TOKEN": "test-only-token",
    }
    for missing in ("ZOT_TOKEN", "BUILDX_BUILDER"):
        result = run(credentials, directory, {**auth_environment, missing: ""})
        assert result.returncode != 0
        assert not outputs.exists()
    result = run(credentials, directory, auth_environment)
    assert result.returncode == 0, result.stderr
    auth_directory = outputs.read_text().strip().removeprefix("directory=")
    assert Path(auth_directory, "config.json").exists()
    assert "test-only-token" not in metadata.read_text() + outputs.read_text()
    assert f"BUILDX_CONFIG={directory}/home/.docker/buildx" in metadata.read_text()
    result = run(step(publish, "Remove registry credentials"), directory, {"AUTH_DIRECTORY": auth_directory})
    assert result.returncode == 0 and not Path(auth_directory).exists()

print("Runner/event policy, input validation, seven pin scenarios, and credential cleanup pass.")
