"""Tests for _apply_host_default_when_no_node_in_prompt — 'if prompt doesn't say which node, use host'."""
from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from urirun.host.chat_orchestrator import _apply_host_default_when_no_node_in_prompt


def _deps(alias_map: dict) -> MagicMock:
    d = MagicMock()
    d.node_alias_map_fn.return_value = alias_map
    return d


ALIAS = {"lenovo": "lenovo", "laptop": "lenovo"}


class TestHostDefault(unittest.TestCase):

    def _call(self, prompt, selected_nodes, selected_targets, alias_map=None):
        deps = _deps(alias_map or ALIAS)
        return _apply_host_default_when_no_node_in_prompt(
            prompt, selected_nodes, selected_targets, None, None, deps)

    def test_no_node_in_prompt_strips_remote(self):
        nodes, targets = self._call(
            "opublikuj post na LinkedIn",
            ["lenovo"], ["host", "node:lenovo"])
        self.assertEqual(targets, ["host"])
        self.assertEqual(nodes, [])

    def test_node_name_in_prompt_keeps_remote(self):
        nodes, targets = self._call(
            "opublikuj post na LinkedIn na lenovo",
            ["lenovo"], ["host", "node:lenovo"])
        self.assertEqual(targets, ["host", "node:lenovo"])

    def test_alias_in_prompt_keeps_remote(self):
        # "laptop" (exact alias) must appear; inflected "laptopie" does NOT match
        nodes, targets = self._call(
            "otwórz stronę na laptop",
            ["lenovo"], ["host", "node:lenovo"])
        self.assertEqual(targets, ["host", "node:lenovo"])

    def test_remote_keyword_keeps_remote(self):
        nodes, targets = self._call(
            "zrób zrzut ekranu na zdalnym komputerze",
            ["lenovo"], ["host", "node:lenovo"])
        self.assertEqual(targets, ["host", "node:lenovo"])

    def test_local_keyword_already_host_unchanged(self):
        nodes, targets = self._call(
            "zrób zrzut ekranu na lokalnym komputerze",
            [], ["host"])
        self.assertEqual(targets, ["host"])
        self.assertEqual(nodes, [])

    def test_already_host_only_unchanged(self):
        nodes, targets = self._call(
            "zrób cokolwiek",
            [], ["host"])
        self.assertEqual(targets, ["host"])

    def test_remote_keyword_zdalny(self):
        nodes, targets = self._call(
            "otwórz zdalny terminal",
            ["lenovo"], ["host", "node:lenovo"])
        self.assertEqual(targets, ["host", "node:lenovo"])


if __name__ == "__main__":
    unittest.main()
