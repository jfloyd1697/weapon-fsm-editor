# weapon-fsm-starter

Starter monorepo for a dual-state-machine weapon editor:

- `weapon_fsm_core`: pure Python domain/application/infrastructure package
- `weapon_fsm_editor`: PyQt6 dashboard package using the core library
- `demos/weapon_profile.yaml`: example editable profile

## What is included

- Gun FSM and behavior FSM definitions
- Event dispatch pipeline from gun -> emitted events -> behavior
- YAML schema using `mashumaro` mixins
- Profile repository and mapping layer
- Minimal PyQt6 dashboard with:
  - file editor
  - gun machine view
  - behavior machine view
  - event buttons
  - simulation summary
  - log output
- Pytest coverage for the core package

## Install

Create a virtual environment and install both editable packages:

```bash
pip install -e ./libs/weapon_fsm_core -e ./libs/weapon_fsm_editor
```

Or install dev dependencies for the repo root:

```bash
pip install -r requirements-dev.txt
```

## Run tests

```bash
pytest libs/weapon_fsm_core/tests
```

## Run the demo editor

```bash
python -m weapon_fsm_editor.app demos/weapon_profile.yaml
```

## Notes

This is intentionally a starter scaffold, not a finished editor. The graph rendering uses a simple scene layout and is designed to be easy to extend.
