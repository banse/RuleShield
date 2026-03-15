"""Prompt Template Optimizer -- extracts templates from recurring similar prompts.

Analyzes request_log for prompt clusters that share common structure
but differ in specific values. Extracts parameterized templates and
caches known variable->response mappings.

Example:
  Prompts: "What is the capital of France?", "What is the capital of Germany?"
  Template: "What is the capital of {country}?"
  Cache: {"France": "Paris", "Germany": "Berlin"}
  New: "What is the capital of Japan?" -> only send "Japan" context to LLM
"""

import re
import json
import sqlite3
import logging
from pathlib import Path
from collections import defaultdict
from difflib import SequenceMatcher

logger = logging.getLogger("ruleshield.template_optimizer")


class PromptTemplate:
    """A discovered prompt template with variable slots."""

    def __init__(self, template: str, variables: list[str], examples: list[dict]):
        self.template = template          # "What is the capital of {var_1}?"
        self.variables = variables         # ["var_1"]
        self.examples = examples           # [{"var_1": "France", "response": "Paris"}, ...]
        self.hit_count = len(examples)
        self.id = self._generate_id()

    def _generate_id(self) -> str:
        """Generate a stable ID from the template."""
        import hashlib
        return "tpl_" + hashlib.sha256(self.template.encode()).hexdigest()[:12]

    def match(self, prompt: str) -> dict | None:
        """Try to match a prompt against this template.

        Returns {"var_1": "value", ...} on match, None on miss.
        """
        # Convert template to regex: "What is {var_1}?" -> "What is (.+?)\\?"
        pattern = re.escape(self.template)
        for var in self.variables:
            pattern = pattern.replace(re.escape("{" + var + "}"), "(.+?)")
        pattern = "^" + pattern + "$"

        m = re.match(pattern, prompt, re.IGNORECASE)
        if m:
            return {var: m.group(i + 1) for i, var in enumerate(self.variables)}
        return None

    def get_cached_response(self, variables: dict) -> str | None:
        """Look up a cached response for known variable values."""
        for ex in self.examples:
            if all(ex.get(var) == val for var, val in variables.items()):
                return ex.get("response")
        return None

    def add_example(self, variables: dict, response: str):
        """Add a new variable->response mapping."""
        example = {**variables, "response": response}
        if example not in self.examples:
            self.examples.append(example)
            self.hit_count = len(self.examples)

    def to_dict(self) -> dict:
        """Serialize for JSON storage."""
        return {
            "id": self.id,
            "template": self.template,
            "variables": self.variables,
            "examples": self.examples,
            "hit_count": self.hit_count,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PromptTemplate":
        tpl = cls(data["template"], data["variables"], data.get("examples", []))
        tpl.id = data.get("id", tpl.id)
        return tpl


class TemplateOptimizer:
    """Discovers and manages prompt templates from request history."""

    def __init__(self, db_path: str = "~/.ruleshield/cache.db",
                 templates_path: str = "~/.ruleshield/templates.json"):
        self.db_path = str(Path(db_path).expanduser())
        self.templates_path = str(Path(templates_path).expanduser())
        self.templates: list[PromptTemplate] = []

    def load_templates(self):
        """Load saved templates from JSON file."""
        path = Path(self.templates_path)
        if path.exists():
            try:
                with open(path) as f:
                    data = json.load(f)
                self.templates = [PromptTemplate.from_dict(t) for t in data]
                logger.info("Loaded %d templates", len(self.templates))
            except Exception as e:
                logger.warning("Failed to load templates: %s", e)

    def save_templates(self):
        """Save templates to JSON file."""
        path = Path(self.templates_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump([t.to_dict() for t in self.templates], f, indent=2)

    def match(self, prompt: str) -> tuple[PromptTemplate, dict, str | None] | None:
        """Try to match a prompt against known templates.

        Returns (template, variables, cached_response) or None.
        cached_response is None if variables are new (need LLM).
        """
        for tpl in self.templates:
            variables = tpl.match(prompt)
            if variables:
                cached = tpl.get_cached_response(variables)
                return (tpl, variables, cached)
        return None

    def discover_templates(self, min_cluster_size: int = 3,
                           similarity_threshold: float = 0.6) -> list[PromptTemplate]:
        """Analyze request_log and discover new templates.

        Strategy:
        1. Load all unique prompts from request_log
        2. Group prompts by structural similarity
        3. For each group with 3+ members:
           a. Find the common structure (shared words)
           b. Identify variable positions (differing words)
           c. Create a template with variable slots
           d. Map known variable values to their responses

        Returns list of newly discovered templates.
        """
        prompts = self._load_prompts_with_responses()
        if len(prompts) < min_cluster_size:
            return []

        # Group by word count + first/last words (rough structural similarity)
        groups = self._cluster_by_structure(prompts)

        new_templates = []
        for group in groups:
            if len(group) < min_cluster_size:
                continue

            template = self._extract_template(group, similarity_threshold)
            if template and template.variables:  # must have at least one variable
                # Check if template already exists
                existing = False
                for t in self.templates:
                    if t.template == template.template:
                        # Merge examples
                        for ex in template.examples:
                            t.add_example(
                                {k: v for k, v in ex.items() if k != "response"},
                                ex.get("response", "")
                            )
                        existing = True
                        break

                if not existing:
                    self.templates.append(template)
                    new_templates.append(template)

        if new_templates:
            self.save_templates()

        return new_templates

    def _load_prompts_with_responses(self) -> list[dict]:
        """Load unique prompts and their responses from SQLite."""
        if not Path(self.db_path).exists():
            return []

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            cur = conn.execute("""
                SELECT prompt_text, response, COUNT(*) as cnt
                FROM request_log
                WHERE prompt_text IS NOT NULL
                  AND prompt_text != ''
                  AND resolution_type IN ('llm', 'passthrough')
                GROUP BY prompt_text
                ORDER BY cnt DESC
                LIMIT 500
            """)
            results = []
            for row in cur.fetchall():
                text = row["prompt_text"]
                # Strip prefixes like "user: " or "[codex] "
                for prefix in ["user: ", "[codex] ", "[passthrough] ", "[trimmed] "]:
                    if text.startswith(prefix):
                        text = text[len(prefix):]

                response_text = ""
                try:
                    resp = json.loads(row["response"])
                    # Try OpenAI format
                    choices = resp.get("choices", [])
                    if choices:
                        response_text = choices[0].get("message", {}).get("content", "")
                    # Try plain content
                    if not response_text:
                        response_text = resp.get("content", "")
                except (json.JSONDecodeError, TypeError, KeyError):
                    response_text = str(row["response"])[:200] if row["response"] else ""

                results.append({
                    "prompt": text,
                    "response": response_text,
                    "count": row["cnt"],
                })
            return results
        finally:
            conn.close()

    def _cluster_by_structure(self, prompts: list[dict]) -> list[list[dict]]:
        """Group prompts by structural similarity."""
        groups = defaultdict(list)

        for p in prompts:
            words = p["prompt"].lower().split()
            if len(words) < 3:
                continue
            # Key: word count + first 2 words + last word
            key = f"{len(words)}_{words[0]}_{words[1]}_{words[-1]}"
            groups[key].append(p)

        return list(groups.values())

    def _extract_template(self, group: list[dict],
                          similarity_threshold: float) -> PromptTemplate | None:
        """Extract a template from a group of similar prompts."""
        if len(group) < 2:
            return None

        prompts = [p["prompt"] for p in group]

        # Tokenize all prompts
        tokenized = [p.split() for p in prompts]

        # Find common words at each position
        max_len = max(len(t) for t in tokenized)
        min_len = min(len(t) for t in tokenized)

        if min_len != max_len:
            # Different lengths -- try to find common prefix/suffix
            return self._extract_template_difflib(group, similarity_threshold)

        template_parts = []
        variables = []
        var_count = 0
        examples_data = defaultdict(dict)

        for pos in range(max_len):
            words_at_pos = [t[pos] for t in tokenized]
            unique_words = set(w.lower() for w in words_at_pos)

            if len(unique_words) == 1:
                # Same word at this position -- it's part of the template
                template_parts.append(tokenized[0][pos])
            else:
                # Different words -- this is a variable
                var_name = f"var_{var_count + 1}"
                var_count += 1
                template_parts.append("{" + var_name + "}")
                variables.append(var_name)

                # Record the variable values per prompt
                for i, word in enumerate(words_at_pos):
                    examples_data[i][var_name] = word

        if not variables:
            return None

        template_str = " ".join(template_parts)

        # Build examples with responses
        examples = []
        for i, p in enumerate(group):
            ex = dict(examples_data.get(i, {}))
            ex["response"] = p.get("response", "")
            examples.append(ex)

        return PromptTemplate(template_str, variables, examples)

    def _extract_template_difflib(self, group: list[dict],
                                  threshold: float) -> PromptTemplate | None:
        """Extract template using difflib for variable-length prompts."""
        prompts = [p["prompt"] for p in group]

        # Use first prompt as reference
        ref = prompts[0]

        # Check similarity of all prompts to reference
        for p in prompts[1:]:
            ratio = SequenceMatcher(None, ref.lower(), p.lower()).ratio()
            if ratio < threshold:
                return None

        # Find the longest common substring as template base
        # Simple approach: word-level diff between first two prompts
        words1 = ref.split()
        words2 = prompts[1].split()

        matcher = SequenceMatcher(None, words1, words2)
        matching_blocks = matcher.get_matching_blocks()

        if not matching_blocks or matching_blocks[0].size < 2:
            return None

        # Build template from matching blocks
        template_parts = []
        variables = []
        var_count = 0
        last_end = 0

        for block in matching_blocks:
            if block.size == 0:
                continue

            # Gap before this block = variable
            if block.a > last_end:
                var_name = f"var_{var_count + 1}"
                var_count += 1
                template_parts.append("{" + var_name + "}")
                variables.append(var_name)

            # Matching block = template text
            template_parts.extend(words1[block.a:block.a + block.size])
            last_end = block.a + block.size

        # Trailing gap = variable
        if last_end < len(words1):
            var_name = f"var_{var_count + 1}"
            var_count += 1
            template_parts.append("{" + var_name + "}")
            variables.append(var_name)

        if not variables:
            return None

        template_str = " ".join(template_parts)

        # Build examples
        tpl = PromptTemplate(template_str, variables, [])
        for p in group:
            matched = tpl.match(p["prompt"])
            if matched:
                tpl.add_example(matched, p.get("response", ""))

        return tpl

    def get_stats(self) -> dict:
        """Return template stats."""
        total_examples = sum(t.hit_count for t in self.templates)
        return {
            "total_templates": len(self.templates),
            "total_cached_examples": total_examples,
            "templates": [
                {
                    "id": t.id,
                    "template": t.template,
                    "variables": t.variables,
                    "examples": t.hit_count,
                }
                for t in self.templates
            ],
        }
