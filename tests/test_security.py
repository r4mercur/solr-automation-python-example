import os
import time
import unittest
import requests

from requests.auth import HTTPBasicAuth
from testcontainers.compose import DockerCompose

from solr import security_main_for_test
from solr.util import with_env


class TestSecuritySolrCloud(unittest.TestCase):
    @classmethod
    @with_env(required_variables=["SOLR_URL"])
    def setUp(cls):
        cls.compose = DockerCompose(os.path.dirname(__file__),
                                    compose_file_name='docker-compose.test.yml')
        cls.compose.start()

        cls.solr_url = os.getenv('SOLR_URL')
        time.sleep(3)


    @classmethod
    def tearDown(cls):
        cls.compose.stop()


    def test_upload_security_to_zookeeper(self):
        security_main_for_test(password='password')

        with open(os.path.join(os.path.dirname(__file__), '../json/security.json'), 'r', encoding='utf-8') as security_file:
            security = security_file.read()
            self.assertIn('solr', security)

    def test_verify_security_is_enabled(self):
        security_main_for_test(password='password')

        request_with_auth = requests.get(f'{self.solr_url}/admin/authentication',
                                         auth=HTTPBasicAuth('solr', 'password'))
        self.assertEqual(request_with_auth.status_code, 200)

        request_with_no_auth = requests.get(f'{self.solr_url}/admin/authentication')
        self.assertEqual(request_with_no_auth.status_code, 401)
