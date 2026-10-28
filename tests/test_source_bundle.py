"""Prove that the repository's compact representation restores exact source bytes."""
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'src'))
from rn_public.bundle import restore_sources, sha256


class SourceBundle(unittest.TestCase):
    def test_byte_identical_round_trip(self):
        source=root/'data/packed/source_bundle.json'
        manifest=json.loads(source.read_text())
        with tempfile.TemporaryDirectory() as temporary:
            target=Path(temporary)
            (target/'data/packed').mkdir(parents=True)
            shutil.copyfile(source,target/'data/packed/source_bundle.json')
            for item in manifest['parts']:
                os.link(root/item['path'],target/item['path'])
            result=restore_sources(target)
            self.assertEqual(result['restored_files'],len(manifest['members']))
            for item in manifest['members']:
                self.assertEqual(sha256(target/item['path']),item['sha256'])
            self.assertEqual(restore_sources(target)['restored_files'],0)
