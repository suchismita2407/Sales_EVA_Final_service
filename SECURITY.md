# Security Notes

## Dependency advisory

The current ChromaDB release is pinned in `requirements.lock`. As of September 11, 2026, the package index reports advisories `PYSEC-2026-311`, `PYSEC-2026-3813`, `PYSEC-2026-3814`, `PYSEC-2026-3815`, `CVE-2026-45830`, `CVE-2026-45833`, and `CVE-2026-45831` for the available release, with no fixed version available to this project.

CI explicitly records these advisories as accepted upstream blockers while continuing to fail on newly introduced or fixable vulnerabilities. Revisit this exception before production deployment and upgrade ChromaDB as soon as patched releases are available.

Do not expose ChromaDB to the public network. Keep its persistent data directory on a private application volume and restrict service access to the Flask process.