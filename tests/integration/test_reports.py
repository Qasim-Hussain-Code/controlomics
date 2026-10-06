import json
import unittest
from html.parser import HTMLParser

from controlomics.execution import ExecutionConfig, execute_local
from controlomics.privacy import PreparedRequest, SafeField
from controlomics.project import parse_project_json
from controlomics.reports import render_report
from controlomics.workflow import audit_project, propose, review_methods
from tests.fixtures import ROOT, payload


class ReportLinks(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids, self.targets = [], []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if 'id' in attributes:
            self.ids.append(attributes['id'])
        if tag == 'a' and attributes.get('href', '').startswith('#'):
            self.targets.append(attributes['href'][1:])


class ReportTests(unittest.TestCase):
    def project(self):
        data = payload()
        data['candidates'] = []
        return audit_project(review_methods(propose(parse_project_json(json.dumps(data)))))

    def test_empty_sections_and_summary_do_not_imply_results(self):
        report = render_report(self.project())
        self.assertIn('No control result is recorded', report)
        self.assertIn('No publication identity is recorded', report)
        self.assertIn('Completed executions</span><strong>0</strong>', report)
        self.assertIn('An empty ledger does not prove', report)
        self.assertIn('@media print', report)
        links = ReportLinks()
        links.feed(report)
        self.assertEqual(len(links.ids), len(set(links.ids)))
        self.assertTrue(set(links.targets).issubset(set(links.ids)))

    def test_execution_is_bound_to_control_claim_plan_and_rule(self):
        project = self.project()
        config = ExecutionConfig(kind='REFERENCE', expected_difference=2.0, assumptions=('Synthetic report fixture only.',))
        project = audit_project(execute_local(project, project.controls[0].control_id, config, (ROOT / 'examples' / 'positive_reference.csv').read_bytes()))
        report = render_report(project)
        self.assertIn(project.execution_plans[0].code_sha256, report)
        self.assertIn('Prespecified decision rule', report)
        self.assertIn(project.results[0].result_id, report)
        self.assertIn('Completed executions</span><strong>1</strong>', report)
        self.assertIn('Claim challenged', report)
        self.assertIn('Claim assessed', report)
        links = ReportLinks()
        links.feed(report)
        self.assertTrue(set(links.targets).issubset(set(links.ids)))

    def test_report_rejects_credential_headers_and_raw_body_in_ledger(self):
        request = PreparedRequest('LITERATURE', 'GET', 'https://api.crossref.org/works/10.1000%2Fexample', (SafeField('public_identifier', '10.1000/example', 'SAFE'),))
        event = {**request.preview(), 'request_sha256': request.approval_hash, 'sent_at': '2026-10-06T01:00:00Z', 'status': 'FAILED', 'body_sha256': None, 'credential_supplied': False, 'payload_transmission': 'NOT_STARTED'}
        self.assertIn('NOT_STARTED', render_report(self.project(), [event]))
        for addition in ({'Authorization': 'synthetic_private_sentinel'}, {'body': 'synthetic_private_sentinel'}):
            with self.assertRaises(ValueError):
                render_report(self.project(), [{**event, **addition}])
