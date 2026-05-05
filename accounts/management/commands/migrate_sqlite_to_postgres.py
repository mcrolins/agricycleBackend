import tempfile
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Create the PostgreSQL schema and load data from the existing SQLite database."

    def add_arguments(self, parser):
        parser.add_argument(
            "--flush-target",
            action="store_true",
            help="Clear the PostgreSQL database before loading SQLite data.",
        )
        parser.add_argument(
            "--keep-fixture",
            action="store_true",
            help="Keep the generated JSON fixture for inspection.",
        )

    def handle(self, *args, **options):
        default_engine = settings.DATABASES["default"]["ENGINE"]
        if default_engine != "django.db.backends.postgresql":
            raise CommandError("The default database must be configured for PostgreSQL.")

        sqlite_name = settings.DATABASES["sqlite_source"]["NAME"]
        sqlite_path = Path(sqlite_name)
        if not sqlite_path.exists():
            raise CommandError(f"SQLite source database was not found: {sqlite_path}")

        self.stdout.write("Applying migrations to PostgreSQL...")
        call_command("migrate", database="default", interactive=False, verbosity=1)

        if options["flush_target"]:
            self.stdout.write("Flushing PostgreSQL target database...")
            call_command("flush", database="default", interactive=False, verbosity=1)

        fixture = tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".json",
            prefix="agricycle-sqlite-export-",
            delete=not options["keep_fixture"],
        )

        with fixture:
            self.stdout.write(f"Exporting SQLite data from {sqlite_path}...")
            call_command(
                "dumpdata",
                database="sqlite_source",
                natural_foreign=True,
                natural_primary=True,
                exclude=["contenttypes", "auth.Permission"],
                indent=2,
                stdout=fixture,
                verbosity=0,
            )
            fixture.flush()

            self.stdout.write("Loading data into PostgreSQL...")
            call_command("loaddata", fixture.name, database="default", verbosity=1)

            if options["keep_fixture"]:
                self.stdout.write(f"Kept fixture at {fixture.name}")

        self.stdout.write(self.style.SUCCESS("SQLite data was migrated to PostgreSQL."))
