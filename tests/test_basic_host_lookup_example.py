import sys
import unittest

if sys.version_info[0] > 2:
    import builtins # pylint: disable=import-error, unused-import
else:
    import __builtin__ # pylint: disable=import-error
    builtins = __builtin__ # pylint: disable=invalid-name

# pylint: disable=wrong-import-position
from mock import patch
import dxlmaxmindservice

def _license_key_configured(config_file):
    """Whether the service configuration contains a non-empty licenseKey."""
    try:
        with open(config_file) as handle:
            for line in handle:
                key, sep, value = line.partition("=")
                if sep and key.strip() == "licenseKey":
                    return bool(value.strip())
    except OSError:
        pass
    return False


class StringMatches(str):
    def __eq__(self, other):
        return self in other


class StringDoesNotMatch(str):
    def __eq__(self, other):
        return self not in other


class BasicHostLookupExample(unittest.TestCase):
    def test_basic_host_lookup_example(self): # pylint: disable=no-self-use
        # The service downloads the GeoLite2 database with a MaxMind license
        # key; without one (e.g. forks without the CI secret) the test cannot run.
        if not _license_key_configured("config/dxlmaxmindservice.config"):
            self.skipTest("MaxMind license key not configured "
                          "(licenseKey in config/dxlmaxmindservice.config)")
        sample_file = "sample/basic/basic_host_lookup_example.py"
        sample_globals = {"__file__": sample_file}
        with dxlmaxmindservice.MaxMindGeolocationService("config") as app:
            app.run()
            with open(sample_file) as f, \
                patch.object(builtins, 'print') as mock_print:
                exec(f.read(), sample_globals) # pylint: disable=exec-used
        mock_print.assert_called_with(StringMatches("registered_country"))
        mock_print.assert_called_with(
            StringDoesNotMatch("Error invoking service"))
