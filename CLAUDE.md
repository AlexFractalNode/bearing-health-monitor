# bearing-health-monitor

- Read `docs/PROJECT_BRIEF.md` first: goals, dataset, phases, evaluation rules and open questions.
- Chat with Alexander in German; code, comments, docstrings, README and commit messages in English.
- Never commit raw data (`data/raw/`, `IMS.zip`) or trained model files.
- Work phase by phase as in the brief (section 7); one commit per phase, short report after each phase.
- No data leakage: time-ordered splits only, fit scalers and thresholds on training data only.
