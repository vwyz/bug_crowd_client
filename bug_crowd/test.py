import datetime
import unittest
import uuid

import mock
import requests
from six.moves.urllib.parse import quote as url_quote

from .client import BugcrowdClient


class BugcrowdClientTest(unittest.TestCase):
    """ Tests for BugcrowdClient. """

    def setUp(self):
        self.api_token = 'api-token-%s' % uuid.uuid4()
        self.client = BugcrowdClient(self.api_token)
        self._bounty = get_example_bounty()

    def test_get_api_uri(self):
        """ tests that the get_api_uri method works as expected. """
        path = '<eg>'
        expected = self.client.base_uri + url_quote(path)
        self.assertEqual(self.client.get_api_uri(path), expected)

    def test_get_api_uri_for_bounty_submissions(self):
        """ tests that the get_api_uri_for_bounty_submissions method works
            as expected.
        """
        expected_url = self.client.base_uri + (
            'bounties/%s/submissions' % url_quote(self._bounty['uuid']))
        url = self.client.get_api_uri_for_bounty_submissions(self._bounty)
        self.assertEqual(url, expected_url)

    def test_get_api_uri_for_submission(self):
        """ tests that the get_api_uri_for_submission method works
            as expected.
        """
        submission = get_example_submission()
        expected_url = self.client.base_uri + (
            'submissions/%s' % url_quote(submission['uuid']))
        self.assertEqual(
            self.client.get_api_uri_for_submission(submission), expected_url)

    @mock.patch.object(requests.Session, 'get')
    def test_get_bounties(self, mocked_method):
        """ tests that the get_bounties method works as expected."""
        url = self.client.get_api_uri('bounties')
        expected_bounties = [self._bounty]
        setup_example_bounties_response(mocked_method, expected_bounties)
        self.assertEqual(self.client.get_bounties(), expected_bounties)
        mocked_method.assert_called_once_with(url)

    @mock.patch.object(requests.Session, 'get')
    def test_get_submissions_default_params(self, mocked_method):
        """ tests that the default parameters used in the get_submissions
            method match those expected.
        """
        expected_params = {'sort': 'newest', 'offset': 0}
        setup_example_submission_response(mocked_method)
        url = self.client.get_api_uri_for_bounty_submissions(self._bounty)
        list(self.client.get_submissions(self._bounty))
        mocked_method.assert_called_once_with(url, params=expected_params)

    @mock.patch.object(requests.Session, 'get')
    def test_get_submissions_uses_given_params(self, mocked_method):
        """ tests that params provided to get_submissions are used. """
        expected_params = {'sort': 'newest', 'offset': 25}
        setup_example_submission_response(mocked_method)
        list(self.client.get_submissions(self._bounty, params=expected_params))
        mocked_method.assert_called_once_with(mock.ANY, params=expected_params)

    @mock.patch.object(requests.Session, 'get')
    def test_get_submissions_retrieval_one_page(self, mocked_method):
        """ tests that the get_submissions method correctly retrieves
            submissions when there is only one page of submissions.
        """
        expected_submissions = [get_example_submission()]
        content = [create_bounty_submissions_response(expected_submissions)]
        setup_mock_response(mocked_method, content)
        submissions = list(self.client.get_submissions(self._bounty))
        self.assertEqual(submissions, expected_submissions)
        mocked_method.assert_called_once_with(mock.ANY, params=mock.ANY)

    @mock.patch.object(requests.Session, 'get')
    def test_get_submissions_retrieval_multiple_pages(self, mocked_method):
        """ tests that the get_submissions method correctly retrieves
            submissions when there are multiple pages of submissions.
        """
        num_submissions = 26
        expected_submissions = [get_example_submission(uuid=str(x))
                                for x in range(0, num_submissions)]
        json_res_one = create_bounty_submissions_response(
            expected_submissions[:-1], count=25, total_hits=num_submissions)
        json_res_two = create_bounty_submissions_response(
            expected_submissions[-1:], count=1, total_hits=num_submissions,
            offset=25)
        setup_mock_response(mocked_method, [json_res_one, json_res_two])
        submissions = list(self.client.get_submissions(self._bounty))
        self.assertEqual(submissions, expected_submissions)
        self.assertEqual(len(submissions), num_submissions)
        self.assertTrue(len(mocked_method.mock_calls) > 1)
        seen_offsets = set()
        for name, args, kwargs in mocked_method.mock_calls:
            offset = kwargs['params']['offset']
            self.assertFalse(offset in seen_offsets)
            seen_offsets.add(offset)

    @mock.patch.object(requests.Session, 'post')
    def test_create_submission(self, mocked_method):
        """ tests that the create_submission method works as expected. """
        fields = {'title': uuid.uuid4(),
                  'submitted_at': datetime.datetime.now().isoformat()}
        self.client.create_submission(self._bounty, fields)
        expected_url = self.client.get_api_uri_for_bounty_submissions(
            self._bounty)
        mocked_method.assert_called_once_with(
            expected_url, json={'submission': fields})

    def test_create_submission_checks_required_fields(self):
        """ tests that the create_submission method checks that required
            fields have been supplied.
        """
        fields = {'title': 'submission without submitted_at'}
        with self.assertRaises(ValueError):
            self.client.create_submission(self._bounty, fields)


def setup_example_bounties_response(mocked_method, bounties=None):
    """ setups up an example bounties response. """
    if bounties is None:
        bounties = get_example_bounty()
    content = [create_bounty_bounties_response(bounties)]
    setup_mock_response(mocked_method, content)
    return mocked_method


def setup_example_submission_response(mocked_method):
    """ setups up an example submissions response. """
    content = [create_bounty_submissions_response([get_example_submission()])]
    setup_mock_response(mocked_method, content)
    return mocked_method


def create_bounty_bounties_response(bounties, **kwargs):
    """ returns a submission response from the given submissions. """
    return {
        'bounties': bounties,
    }


def create_bounty_submissions_response(submissions, **kwargs):
    """ returns a submission response from the given submissions. """
    return {
        'submissions': submissions,
        'meta': {
            'count': kwargs.get('count', len(submissions)),
            'offset': kwargs.get('offset', None),
            'total_hits': kwargs.get('total_hits', len(submissions)),
        },
    }


def get_example_bounty():
    """ returns an example bounty. """
    return {
        'uuid': 'bounty-uuid-%s' % uuid.uuid4(),
        'name': 'example',
    }


def get_example_submission(**kwargs):
    """ returns an example submission. """
    return {
        'uuid': 'submission-uuid-%s' % kwargs.get('uuid', uuid.uuid4()),
        'title': 'example',
    }


def setup_mock_response(mocked_method, json_contents, headers=None):
    """ setups up a mock response for testing purposes. """
    m_async_request = mock.Mock(name='async_request')
    mocked_method.return_value = m_async_request
    m_response = mock.Mock(name='response')
    m_response.json.side_effect = json_contents
    m_async_request.result.return_value = m_response
    return mocked_method


if __name__ == '__main__':
    unittest.main()