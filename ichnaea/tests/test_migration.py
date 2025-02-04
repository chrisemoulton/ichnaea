import os.path

from alembic import command as alembic_command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.ddl.impl import _type_comparators
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy.schema import MetaData
from sqlalchemy.sql import sqltypes

# make sure all models are imported
from ichnaea.models import _Model  # NOQA

from ichnaea.tests.base import (
    _make_db,
    DATA_DIRECTORY,
    DBTestCase,
    setup_package,
    TestCase,
)

_compare_attrs = {
    sqltypes._Binary: ('length', ),
    sqltypes.Date: (),
    sqltypes.DateTime: ('fsp', 'timezone'),
    sqltypes.Integer: ('display_width', 'unsigned', 'zerofill'),
    sqltypes.String: ('binary', 'charset', 'collation', 'length', 'unicode'),
}

SQL_BASE12 = os.path.join(DATA_DIRECTORY, 'base12.sql')
SQL_BASE13 = os.path.join(DATA_DIRECTORY, 'base13.sql')


def db_compare_type(context, inspected_column,
                    metadata_column, inspected_type, metadata_type):
    # return True if the types are different, False if not, or None
    # to allow the default implementation to compare these types
    expected = metadata_column.type
    migrated = inspected_column.type

    # this extends the logic in alembic.ddl.impl.DefaultImpl.compare_type
    type_affinity = migrated._type_affinity
    compare_attrs = _compare_attrs.get(type_affinity, None)
    if compare_attrs is not None:
        if type(expected) != type(migrated):
            return True
        for attr in compare_attrs:
            if getattr(expected, attr, None) != getattr(migrated, attr, None):
                return True
        return False

    # fall back to limited alembic type comparison
    comparator = _type_comparators.get(type_affinity, None)
    if comparator is not None:
        return comparator(expected, migrated)
    raise AssertionError('Unsupported DB type comparison.')


class MigrationTest(object):

    base = None
    rev = None

    def setUp(self):
        super(MigrationTest, self).setUp()
        self.db = _make_db()
        # capture state of fresh database
        self.head_metadata = self.inspect_db()
        DBTestCase.cleanup_tables(self.db.engine)

    def tearDown(self):
        super(MigrationTest, self).tearDown()
        self.db.engine.pool.dispose()
        del self.db
        # setup normal database schema again
        setup_package(None)

    def alembic_config(self):
        alembic_cfg = Config()
        alembic_cfg.set_section_option(
            'alembic', 'script_location', 'alembic')
        alembic_cfg.set_section_option(
            'alembic', 'sqlalchemy.url', str(self.db.engine.url))
        alembic_cfg.set_section_option(
            'alembic', 'sourceless', 'true')
        return alembic_cfg

    def alembic_script(self):
        return ScriptDirectory.from_config(self.alembic_config())

    def current_db_revision(self):
        with self.db.engine.connect() as conn:
            result = conn.execute('select version_num from alembic_version')
            alembic_rev = result.first()
        if alembic_rev is None:
            return None
        return alembic_rev[0]

    def inspect_db(self):
        metadata = MetaData()
        metadata.reflect(bind=self.db.engine)
        return metadata

    def setup_base_db(self):
        with open(self.base) as fd:
            sql_text = fd.read()
        with self.db.engine.connect() as conn:
            conn.execute(sql_text)

    def run_migration(self, target='head'):
        with self.db.engine.connect() as conn:
            trans = conn.begin()
            alembic_command.upgrade(self.alembic_config(), target)
            trans.commit()

    def stamp_db(self):
        if self.rev:
            with self.db.engine.connect() as conn:
                trans = conn.begin()
                alembic_command.stamp(self.alembic_config(), self.rev)
                trans.commit()

    def test_migration(self):
        self.setup_base_db()
        # we have no alembic base revision
        self.assertTrue(self.current_db_revision() is None)

        # stamp the database with the correct version
        self.stamp_db()

        # run the migration, afterwards the DB is stamped
        self.run_migration()
        db_revision = self.current_db_revision()
        self.assertTrue(db_revision is not None)

        # db revision matches latest alembic revision
        alembic_head = self.alembic_script().get_current_head()
        self.assertEqual(db_revision, alembic_head)

        # compare the db schema from a migrated database to
        # one created fresh from the model definitions
        opts = {
            'compare_type': db_compare_type,
            'compare_server_default': True,
        }
        with self.db.engine.connect() as conn:
            context = MigrationContext.configure(connection=conn, opts=opts)
            metadata_diff = compare_metadata(context, self.head_metadata)

        self.assertEqual(metadata_diff, [])


class TestMigration12(MigrationTest, TestCase):

    base = SQL_BASE12
    rev = None


class TestMigration13(MigrationTest, TestCase):

    base = SQL_BASE13
    rev = 'b24dbb9ccfe'
