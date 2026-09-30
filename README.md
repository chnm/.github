# .github

Shared GitHub Actions for RRCHNM repositories. Legacy Django/Compose workflows
remain unchanged; Kubernetes migrations use `django--k0s.yml`.

The reusable runs the caller's Dockerfile `test` stage and builds the final
runtime image without publishing on GitHub-hosted runners. Only a push or manual dispatch on the configured trusted branch builds/pushes
the final image on `[self-hosted, IncusOS]`. It uses the runner's persistent
Buildx builder and normal internal CA trust. Argo reads the caller's GitHub
`k8s/` overlay; no Forgejo source mirror or Ansible deployment is involved.

Caller example (replace the reusable revision with a reviewed commit SHA):

```yaml
on:
  push:
    branches: [main]
    paths-ignore: [k8s/kustomization.yaml]
  pull_request:
    branches: [main]
  workflow_dispatch:
permissions:
  contents: write
jobs:
  deployment:
    uses: chnm/.github/.github/workflows/django--k0s.yml@<reviewed-commit-sha>
    with:
      image: rrchnm/apiary-django
    secrets:
      ZOT_TOKEN: ${{ secrets.ZOT_TOKEN }}
```

Inputs: `image` (required hosted Zot path), `context` (`.`), `test-target`
(`test`), `overlay` (`k8s`), and `ref` (`main`). Tests must not need internal
registries, deployment secrets, or a live database. The overlay must already
declare the full `oci.rrchnm.internal/<image>` name with a digest.

Grant the caller access to the IncusOS runner group and the Zot `ci-github` credential
(the `ZOT_TOKEN` org secret, minted by infra `scripts/rotate-zot-ci-token.sh --user ci-github`).
Only reviewed code belongs on the publishing branch. Digest pins use the caller's
`GITHUB_TOKEN`; branch rules must allow those commits. Otherwise require a
promotion-PR flow before adopting this workflow. No registry credentials remain
on the runner after the job. Failed tests/builds never pin; stale builds cannot
roll back a newer source revision. Existing multi-image pin callers retain their
behavior unless they enable the new `guard-newest` option.

Checks require Kustomize 5.4.3 on PATH:
`uv run --with PyYAML==6.0.3 python .github/tests/test_django_k0s.py`.
Infrastructure deployment/recovery gates:
https://docs.rrchnm.org/subsystems/reverse-proxy/k0s-public-edge/
