from __future__ import annotations

import unittest

from hapa_graphify.mcp import call_mcp_tool, list_mcp_tools


class McpToolTests(unittest.TestCase):
    def test_tool_list_includes_query_first_rule(self) -> None:
        result = list_mcp_tools()
        self.assertTrue(result["ok"], result)
        names = {tool["name"] for tool in result["tools"]}
        self.assertIn("hapa_graph_query", names)
        self.assertIn("query_first_rule", result)

    def test_filtered_query(self) -> None:
        result = call_mcp_tool("hapa_graph_query", {
            "q": "hapa-graphify",
            "node_type": "kanban_card",
            "limit": 10,
        })
        self.assertTrue(result["ok"], result)
        self.assertGreaterEqual(result["match_count"], 1)
        self.assertTrue(all(item["node"]["type"] == "kanban_card" for item in result["matches"]))

    def test_oversized_graph_guard(self) -> None:
        result = call_mcp_tool("hapa_graph_query", {
            "q": "hapa",
            "max_nodes": 1,
        })
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "graph_too_large")


if __name__ == "__main__":
    unittest.main()
