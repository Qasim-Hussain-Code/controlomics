"""Static browser build checks that need no download."""

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('build_browser', ROOT / 'scripts' / 'build_browser.py')
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)


class BrowserBuildTests(unittest.TestCase):
    def test_page_uses_relative_assets_the_policy_and_the_runtime_before_the_interface(self):
        page = build.page((ROOT / 'src' / 'controlomics' / 'web' / 'index.html').read_text(encoding='utf-8'))
        self.assertIn('href="style.css"', page)
        self.assertNotIn('"/app.js"', page)
        self.assertIn('content="' + build.POLICY + '"', page)
        self.assertIn('<meta name="referrer" content="no-referrer">', page)
        self.assertLess(page.index('src="browser.js"'), page.index('src="app.js"'))
        self.assertNotIn("'unsafe-inline'", build.POLICY)
        self.assertNotIn("'unsafe-eval'", build.POLICY)

    def test_page_rewrite_refuses_changed_markup(self):
        with self.assertRaises(ValueError):
            build.page('<html><head><script src="/other.js"></script></head></html>')

    def test_dependencies_resolve_through_either_name_separator(self):
        lock = {'packages': {'pydantic': {'depends': ['pydantic_core', 'typing-extensions']},
                             'pydantic-core': {'depends': ['typing_extensions']}, 'typing-extensions': {'depends': []}}}
        self.assertEqual(set(build.required_packages(lock, ('pydantic',))), {'pydantic', 'pydantic-core', 'typing-extensions'})

    def test_core_files_are_pinned_by_sha256(self):
        self.assertEqual(set(build.CORE), {'pyodide.mjs', 'pyodide.asm.mjs', 'pyodide.asm.wasm', 'python_stdlib.zip', 'pyodide-lock.json'})
        for digest in build.CORE.values():
            self.assertRegex(digest, r'^[0-9a-f]{64}$')


if __name__ == '__main__':
    unittest.main()
