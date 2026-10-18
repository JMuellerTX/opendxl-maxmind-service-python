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

    def test_update_database_cleans_temp_file_and_redacts_license_key(self):
        import io
        import os
        import tarfile
        import tempfile
        from mock import MagicMock
        from dxlmaxmindservice.app import MaxMindDatabase

        # Create a tar.gz without any .mmdb file
        tar_buf = io.BytesIO()
        with tarfile.open(fileobj=tar_buf, mode="w:gz") as tar:
            info = tarfile.TarInfo(name="README.txt")
            data = b"not an mmdb"
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
        tar_bytes = tar_buf.getvalue()

        created_paths = []
        orig_mkstemp = tempfile.mkstemp

        def tracking_mkstemp(*args, **kwargs):
            fd, path = orig_mkstemp(*args, **kwargs)
            created_paths.append(path)
            return fd, path

        md5_resp = MagicMock()
        md5_resp.content = b"abcd1234"
        md5_resp.raise_for_status = MagicMock()

        tar_resp = MagicMock()
        tar_resp.content = tar_bytes
        tar_resp.raise_for_status = MagicMock()

        with patch("dxlmaxmindservice.app.requests.get", side_effect=[md5_resp, tar_resp]), \
                patch("dxlmaxmindservice.app.tempfile.mkstemp", side_effect=tracking_mkstemp):
            db = MaxMindDatabase(60, "", "secret-license-key-999")
            try:
                self.assertEqual(1, len(created_paths))
                self.assertFalse(os.path.exists(created_paths[0]))
                self.assertIsNotNone(db._update_thread)
                self.assertNotIn("secret-license-key-999",
                                 db._redact("Error for key secret-license-key-999"))
            finally:
                db.close()
                self.assertIsNone(db._update_thread)

