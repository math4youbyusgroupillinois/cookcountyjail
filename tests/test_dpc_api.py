#
# Tests the web API wiring to class that provides daily population changes
# functionality.
#

from json import loads

from ccj.app import app
from ccj.models.daily_population import DailyPopulation as DPC
from tempfile import mkdtemp
from shutil import rmtree
from helpers import inmate_population, count_population, DAY_BEFORE, change_counts, STARTING_DATE, \
    UpdatePopulationCounts, EXCLUDE_SET, convert_hash_values_to_integers

API_METHOD_NAME = '/daily_population'


class Test_DailyPopulationChanges_API:

    def setup_method(self, method):
        app.testing = True
        self._tmp_dir = mkdtemp(dir='/tmp')
        app.config['DPC_DIR_PATH'] = self._tmp_dir
        self.dpc = DPC(self._tmp_dir)
        self.client = app.test_client()

    def _store_starting_population(self):
        inmates = inmate_population()
        population_counts = count_population(inmates)
        population_counts['date'] = DAY_BEFORE
        self.dpc.store_starting_population(population_counts)
        return population_counts

    def teardown_method(self, method):
        rmtree(self._tmp_dir)

    def test_fetch_with_nothing_stored_returns_empty_array(self):
        expected = '[]'
        result = self.client.get(API_METHOD_NAME)
        assert result.status_code == 200
        assert result.data == expected

    def test_post_with_one_entry_should_store_result(self):
        starting_population_counts = self._store_starting_population()
        starting_day_inmates = inmate_population()
        population_change_counts = change_counts(starting_day_inmates, STARTING_DATE)
        with self.dpc.writer() as f:
            f.store(population_change_counts)
        expected = UpdatePopulationCounts(starting_population_counts, population_change_counts).dpc_format()
        result = self.client.get(API_METHOD_NAME)
        assert result.status_code == 200
        fetched_data = self._parseJSON(loads(result.data)[0])
        convert_hash_values_to_integers(fetched_data, EXCLUDE_SET)
        assert fetched_data == expected

    def test_external_post_fails(self):
        result = self.client.post(API_METHOD_NAME, data={})
        assert result.status_code == 405

    def _parseJSON(self, obj):
        if isinstance(obj, dict):
            newobj = {}
            for key, value in obj.iteritems():
                key = str(key)
                newobj[key] = self._parseJSON(value)
        elif isinstance(obj, list):
            newobj = []
            for value in obj:
                newobj.append(self._parseJSON(value))
        elif isinstance(obj, unicode):
            newobj = str(obj)
        else:
            newobj = obj
        return newobj