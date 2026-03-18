from logging.config import fileConfig

# Import all models so Base.metadata is populated for autogenerate.
# Add new model imports here as they are created in future phases.
import app.models  # noqa: F401
from alembic import context
from app.core.config import settings
from app.core.database import Base
from sqlalchemy import engine_from_config, pool

config = context.config

# Override sqlalchemy.url from application settings
config.set_main_option("sqlalchemy.url", settings.sync_database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# LangGraph checkpoint tables are managed by AsyncPostgresSaver.setup(),
# not by Alembic. Exclude them from autogenerate detection.
EXCLUDE_TABLES = {"checkpoints", "checkpoint_blobs", "checkpoint_writes", "checkpoint_migrations"}

target_metadata = Base.metadata


def include_object(object, name, type_, reflected, compare_to):
    if type_ == "table" and name in EXCLUDE_TABLES:
        return False
    return True


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
