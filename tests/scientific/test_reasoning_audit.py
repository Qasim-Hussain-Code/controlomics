import json
import unittest

from controlomics.models import DesignReasoner
from controlomics.project import parse_project_json
from controlomics.reasoning import describe_design
from tests.fixtures import payload


class ReasoningAuditTests(unittest.TestCase):
    def project(self, method, independence=(), category="DESCRIPTIVE"):
        value = payload()
        value["analysis"].update(analysis_description=method, methods=[method])
        value["analysis"]["design"]["independence_assumptions"] = list(independence)
        value["claims"][0].update(statement="A supplied descriptive summary.",
                                  category=category, computational_support="DESCRIPTIVE",
                                  assumptions=[])
        return parse_project_json(json.dumps(value))

    def facets(self, project):
        return {cue.facet for cue in describe_design(project.analysis, project.claims[0]).cues}

    def test_rank_test_names_do_not_propose_reference_ranking_controls(self):
        for method in ("Wilcoxon rank-sum test", "Wilcoxon rank sum test",
                       "Wilcoxon signed-rank test", "Wilcoxon signed rank test"):
            with self.subTest(method=method):
                project = self.project(method)
                self.assertNotIn("RANKING", self.facets(project))
                proposals = DesignReasoner().propose(project.analysis, project.claims[0])
                self.assertNotIn("Matched reference discrimination challenge",
                                 {control.name for control in proposals.controls})

    def test_genetic_instrument_phrase_does_not_imply_model_training(self):
        for method in ("Association with genetically predicted exposure",
                       "Association with GENETICALLY   PREDICTED exposure"):
            with self.subTest(method=method):
                project = self.project(method)
                self.assertNotIn("PREDICTION", self.facets(project))
                proposals = DesignReasoner().propose(project.analysis, project.claims[0])
                self.assertNotIn("Training-partition leakage challenge",
                                 {control.name for control in proposals.controls})

    def test_independence_assumptions_do_not_declare_an_association_analysis(self):
        project = self.project("A supplied summary", ("Units may be correlated within donor.",))
        self.assertNotIn("ASSOCIATION", self.facets(project))

    def test_actual_operations_and_supplied_categories_remain_visible(self):
        for method, facet in (("Rank genes by a supplied score", "RANKING"),
                              ("Fit a prediction model with cross-validation", "PREDICTION"),
                              ("Estimate an association with regression", "ASSOCIATION")):
            with self.subTest(method=method):
                self.assertIn(facet, self.facets(self.project(method)))
        self.assertIn("ASSOCIATION", self.facets(self.project("A supplied summary", category="ASSOCIATIONAL")))
        dependent = self.project("A supplied summary", ("Repeated measurements within donor.",))
        self.assertIn("DEPENDENT_UNITS", self.facets(dependent))
