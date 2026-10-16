"""Verify offline installs, drift rejection, pinned upgrades and file ownership."""
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

import sync_consumers as sync


class SyncTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'source'
        self.source.mkdir()
        shutil.copytree(sync.SOURCE / 'references', self.source / 'references')
        shutil.copy2(sync.SOURCE / 'module.json', self.source / 'module.json')
        subprocess.run(['git', 'init', '-q'], cwd=self.source, check=True)
        self.commit()
        self.target = self.root / 'consumer'
        self.target.mkdir()
        (self.target / 'SKILL.md').write_text('Keep workflow entrypoint unchanged.\n')
        (self.target / 'state.json').write_text('{"accepted": false}\n')

    def commit(self):
        subprocess.run(['git', 'add', '.'], cwd=self.source, check=True)
        subprocess.run(['git', '-c', 'user.name=test', '-c', 'user.email=test@example.invalid',
                        'commit', '-qm', 'fixture'], cwd=self.source, check=True)

    def test_install_pin_and_upgrade_preserve_consumer_state(self):
        payload, lock = sync.load_source(self.source)
        sync.sync(self.target, payload, lock)
        sync.sync(self.target, payload, lock, check=True)
        self.assertEqual((self.target / 'state.json').read_text(), '{"accepted": false}\n')
        document = self.source / 'references/evidence.md'
        document.write_text(document.read_text() + '\nNew evidence rule.\n')
        manifest = json.loads((self.source / 'module.json').read_text())
        manifest['version'] = '1.0.1'
        manifest['files']['references/evidence.md'] = sync.digest(document.read_bytes())
        (self.source / 'module.json').write_text(json.dumps(manifest))
        self.commit()
        new_payload, new_lock = sync.load_source(self.source)
        with self.assertRaises(ValueError):
            sync.sync(self.target, new_payload, new_lock, check=True)
        sync.sync(self.target, new_payload, new_lock)
        sync.sync(self.target, new_payload, new_lock, check=True)
        self.assertNotEqual(lock['source_commit'], new_lock['source_commit'])
        self.assertEqual((self.target / 'SKILL.md').read_text(), 'Keep workflow entrypoint unchanged.\n')

    def test_refuse_silent_overwrite_of_consumer_edits(self):
        payload, lock = sync.load_source(self.source)
        sync.sync(self.target, payload, lock)
        (self.target / 'shared/research-core/references/evidence.md').write_text('local edit')
        with self.assertRaisesRegex(ValueError, 'local module edits'):
            sync.sync(self.target, payload, lock)

    def test_source_must_be_committed_and_hash_valid(self):
        p = self.source / 'references/evidence.md'
        p.write_text('changed outside the manifest')
        with self.assertRaisesRegex(ValueError, 'hash mismatch'):
            sync.load_source(self.source)

    def test_untracked_vendor_file_is_not_deleted(self):
        payload, lock = sync.load_source(self.source)
        sync.sync(self.target, payload, lock)
        extra = self.target / 'shared/research-core/notes.md'
        extra.write_text('keep my notes')
        with self.assertRaisesRegex(ValueError, 'Untracked'):
            sync.sync(self.target, payload, lock)
        self.assertEqual(extra.read_text(), 'keep my notes')


if __name__ == '__main__':
    unittest.main()
