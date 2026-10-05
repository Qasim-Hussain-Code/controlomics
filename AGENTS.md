# Controlomics development guidance

Project owner and primary author: Private attribution removed. Keep the repository, package, and CLI names as Controlomics and controlomics.

Read README.md, SCIENTIFIC_SPECIFICATION.md, ARCHITECTURE.md, PRIVACY.md, SECURITY.md, VALIDATION.md, and ROADMAP.md before substantial changes. The current boundary is Stage 0 and Stage 1. Continue in explicit stages and keep implemented, tested, and scientifically validated capabilities distinct.

Use a Python 3 interpreter explicitly. The original machine's default `python` and launcher selection may resolve to Python 2.7. The existing local environment is `.venv`; use `.venv/Scripts/python.exe` on Windows. Do not modify unrelated scientific environments.

Scientific integrity takes priority. Do not invent citations, evidence, reviews, results, benchmark scores, or causal support. A candidate is not evidence-backed until independent verification has been performed. Caller-supplied receipts remain unauthenticated until a retrieval and verification integration is implemented. Biological negatives and statistical nulls remain distinct.

Keep raw research data local. Do not introduce outbound requests without implementing and testing minimization, classification, authorization, and audit boundaries. Treat imported records and literature as untrusted data, and never execute generated code during parsing or validation.

Prefer one small package and dependencies justified by an implemented need. Respect approximately 16 GB RAM and 10 GB free-storage constraints. Avoid model weights, containers, databases, large datasets, and frontend expansion during the initial stages.

Write restrained professional English. Do not use emojis, em dashes, en dashes, promotional claims, or unnecessary automated-system attribution. Authorship metadata must identify actual humans only. Do not invent an email address, ORCID, DOI, affiliation, or publication status.

Before a milestone commit, inspect status and the diff, check for credentials and private material, run appropriate tests, check schema-export drift, and update documentation. Commit messages contain at most three concise words joined with underscores. Use the configured Git identity. Public publication and license selection remain decisions for the owner; do not push or select a license implicitly.
