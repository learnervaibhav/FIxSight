"""Script to generate and run Alembic migrations."""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from alembic.config import Config
from alembic import command

# Create an Alembic config object
alembic_cfg = Config(str(project_root / "alembic.ini"))

# Generate the initial migration
print("Generating initial migration...")
command.revision(alembic_cfg, autogenerate=True, message="initial_schema")
print("Migration generated successfully!")

# Run the migration
print("Running migration...")
command.upgrade(alembic_cfg, "head")
print("Migration applied successfully!")
