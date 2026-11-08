# Optional Astryx comparison source

The classic viewer remains the default. `/astryx/` uses React 19.3.1 and actual Astryx
0.7.11 `Theme`, `Button`, `TextInput`, `Badge`, `Link` with neutralTheme/built, its prebuilt
CSS, and supported token overrides. No fonts CSS or runtime CDN is imported. The pure
KnowledgeMap module is generated verbatim from the classic source, with an export line;
it is not a copied or independently maintained projection.

Python users run the normal CLI and need neither Node nor an internet install. Fixed
prebuilt assets and notices live in `src/local_knowledge_wiki/web/astryx/`. This source,
package-lock.json and license fallbacks are committed; node_modules must stay outside
the checkout. The exact package versions are in package.json; transitive versions and
integrities are pinned by lockfile v3. No install lifecycle scripts are needed.

From the repository root, using Node >=22.13 and npm for developer builds:

```sh
python scripts/build_astryx.py --workspace /absolute/external/astryx-build --write
python scripts/build_astryx.py --workspace /absolute/external/astryx-build --check
node --test frontend/astryx/test.mjs
```

The builder stages known source files, adds the exact shared projection, runs `npm ci
--ignore-scripts --no-audit --no-fund` and a production esbuild build. It confines npm
cache, dependencies and temp files to that external workspace. `--check` rebuilds without
rewriting shipped files and compares every fixed asset, including the hash manifest.
`tests/test_astryx_assets.py` checks source/lock/shared-projection and dist hashes even
without Node. The manifest has no timestamps or absolute machine paths. Only a finite
list of shipped assets is served by Python; no generic file-path handler exists.

For local design-system documentation, after staging dependencies, use the installed
scoped CLI file (never `npx astryx`):

```sh
cd /absolute/external/astryx-build/staging
node node_modules/@astryxdesign/cli/clients/cli/bin/astryx.mjs --version
node node_modules/@astryxdesign/cli/clients/cli/bin/astryx.mjs component Button
```

Do not run init/global configuration as part of this viewer build. The CLI is a dev-only
documentation/build aid and is not shipped in Python runtime assets. Runtime notices are
generated from the actual bundled package graph. Astryx core and StyleX's published
packages omit license files; `licenses/` holds their upstream MIT texts. Other bundled
notices come from the lock-installed packages. There are no experimental chart packages.

Comparison scope is overview, search/topic filtering, stable current graph, selected
excerpt and accessible list. It does not port the classic hop/zoom/pan or full status
filter controls. Original/source/history reading goes through validated fixed hash state
into classic Explorer. Back to `/` is the explicit rollback choice; there is no migration.
