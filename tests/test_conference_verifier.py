"""The portable upgrade must carry both actual exercise scenarios and inputs."""

import json
from pathlib import Path
import shutil
import tempfile
import unittest

from scripts.check_conference_package import load_recorded_scenarios


ROOT = Path(__file__).resolve().parents[1]


class ConferenceScenarioVerificationTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.destination = Path(self.temporary.name)
        (self.destination / 'samples').mkdir()

    def copy_sample(self, name):
        shutil.copyfile(ROOT / f'frontend/web/public/samples/{name}.json',
                        self.destination / f'samples/{name}.json')

    def test_both_actual_scenarios_retain_exact_frames_and_latched_control_history(self):
        self.copy_sample('demo-bench')
        self.copy_sample('demo-curl')
        scenarios = load_recorded_scenarios(self.destination)
        self.assertEqual({'bench_press', 'bicep_curl'}, set(scenarios))
        for kind, recording in scenarios.items():
            self.assertEqual(kind, recording['metadata']['exercise'])
            self.assertEqual(201, len(recording['frames']))
            self.assertEqual(201, len(recording['metadata']['control_history']))

    def test_missing_curl_is_not_reported_as_a_complete_upgraded_package(self):
        self.copy_sample('demo-bench')
        with self.assertRaises(FileNotFoundError):
            load_recorded_scenarios(self.destination)

    def test_wrong_task_or_unaligned_feedback_is_rejected(self):
        self.copy_sample('demo-bench')
        self.copy_sample('demo-curl')
        path = self.destination / 'samples/demo-curl.json'
        recording = json.loads(path.read_text())
        recording['metadata']['exercise'] = 'bench_press'
        path.write_text(json.dumps(recording))
        with self.assertRaises(ValueError):
            load_recorded_scenarios(self.destination)
        recording['metadata']['exercise'] = 'bicep_curl'
        recording['metadata']['control_history'][1]['step'] = 0
        path.write_text(json.dumps(recording))
        with self.assertRaises(ValueError):
            load_recorded_scenarios(self.destination)
