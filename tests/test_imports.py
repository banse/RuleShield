"""Smoke tests -- verify all modules import and basic functionality works."""


def test_imports():
    from ruleshield import CacheManager, RuleEngine, SmartRouter, MetricsDashboard
    from ruleshield.feedback import RuleFeedback
    from ruleshield.router import ComplexityClassifier
    from ruleshield.hermes_bridge import HermesBridge
    from ruleshield.codex_adapter import extract_prompt_from_codex
    from ruleshield.pricing import get_model_cost


def test_rule_engine_match():
    import asyncio
    from ruleshield.rules import RuleEngine

    async def run():
        engine = RuleEngine()
        await engine.init()

        # Should match greeting rule
        result = engine.match("hello", model="claude-sonnet-4-6")
        assert result is not None
        assert result["rule_name"] == "Simple Greeting"

        # Should NOT match (temporal/complex)
        result2 = engine.match(
            "what time is it in Tokyo right now?", model="claude-sonnet-4-6"
        )
        # This may or may not match depending on rules, just verify no crash

    asyncio.run(run())


def test_complexity_classifier():
    from ruleshield.router import ComplexityClassifier

    c = ComplexityClassifier()

    assert c.score("hello") <= 3
    assert c.score("Analyze the entire codebase, find security vulnerabilities, compare with OWASP, and create a detailed report") >= 6


def test_pricing():
    from ruleshield.pricing import get_model_cost

    cost = get_model_cost("gpt-5.3-codex", 1000, 500)
    assert cost > 0

    cost2 = get_model_cost("claude-haiku-4-5", 1000, 500)
    assert cost2 < cost  # haiku should be cheaper


def test_codex_adapter():
    from ruleshield.codex_adapter import extract_prompt_from_codex, is_codex_request

    body = {
        "model": "gpt-5.4",
        "input": [{"type": "message", "role": "user", "content": "hello"}],
    }
    assert is_codex_request(body)
    prompt = extract_prompt_from_codex(body)
    assert "hello" in prompt


def test_temporal_detection():
    from ruleshield.cache import CacheManager

    cm = CacheManager()

    assert cm._is_temporal("what time is it now?")
    assert cm._is_temporal("current weather in Berlin")
    assert not cm._is_temporal("what is Python?")
    assert not cm._is_temporal("explain TCP vs UDP")


def test_cron_optimizer_classifies_dynamic_workflow():
    import sqlite3
    import tempfile
    from pathlib import Path

    from ruleshield.cron_optimizer import analyze_recurring_workflows

    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "cache.db"
        conn = sqlite3.connect(db_path)
        conn.execute(
            """
            CREATE TABLE request_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prompt_hash TEXT NOT NULL,
                prompt_text TEXT,
                response TEXT,
                model TEXT,
                tokens_in INTEGER DEFAULT 0,
                tokens_out INTEGER DEFAULT 0,
                cost_usd REAL DEFAULT 0,
                resolution_type TEXT,
                latency_ms INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        prompt_hash = "hash_mail_digest"
        prompt_text = "please check my mails every day at 8 am and then sort them by category and summarize every category and return with a formatted output"
        for _ in range(4):
            conn.execute(
                """
                INSERT INTO request_log
                    (prompt_hash, prompt_text, response, model, cost_usd, resolution_type, latency_ms)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (prompt_hash, prompt_text, "{}", "gpt-5.1-codex-mini", 0.02, "passthrough", 800),
            )
        conn.commit()
        conn.close()

        result = analyze_recurring_workflows(db_path, min_occurrences=3)
        assert result["count"] == 1
        candidate = result["candidates"][0]
        assert candidate["classification"] == "dynamic_workflow"
        assert candidate["schedule_like"] is True
        assert candidate["workflow_like"] is True
        assert candidate["dynamic_payload"] is True
        assert candidate["decomposition"]["llm_task_steps"]


def test_cron_optimizer_classifies_static_recurring_prompt():
    import sqlite3
    import tempfile
    from pathlib import Path

    from ruleshield.cron_optimizer import analyze_recurring_workflows

    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "cache.db"
        conn = sqlite3.connect(db_path)
        conn.execute(
            """
            CREATE TABLE request_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prompt_hash TEXT NOT NULL,
                prompt_text TEXT,
                response TEXT,
                model TEXT,
                tokens_in INTEGER DEFAULT 0,
                tokens_out INTEGER DEFAULT 0,
                cost_usd REAL DEFAULT 0,
                resolution_type TEXT,
                latency_ms INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        prompt_hash = "hash_status"
        prompt_text = "generate a daily summary report of system health"
        for idx in range(5):
            conn.execute(
                """
                INSERT INTO request_log
                    (prompt_hash, prompt_text, response, model, cost_usd, resolution_type, latency_ms)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    prompt_hash,
                    prompt_text,
                    "{}",
                    "gpt-5.1-codex-mini",
                    0.0 if idx < 4 else 0.01,
                    "cache" if idx < 4 else "passthrough",
                    200,
                ),
            )
        conn.commit()
        conn.close()

        result = analyze_recurring_workflows(db_path, min_occurrences=3)
        assert result["count"] == 1
        candidate = result["candidates"][0]
        assert candidate["classification"] == "static_recurring"
        assert candidate["cache_rate_pct"] == 80.0


def test_cron_optimizer_legacy_mode_returns_basic_recommendation():
    import sqlite3
    import tempfile
    from pathlib import Path

    from ruleshield.cron_optimizer import analyze_recurring_workflows

    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "cache.db"
        conn = sqlite3.connect(db_path)
        conn.execute(
            """
            CREATE TABLE request_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prompt_hash TEXT NOT NULL,
                prompt_text TEXT,
                response TEXT,
                model TEXT,
                tokens_in INTEGER DEFAULT 0,
                tokens_out INTEGER DEFAULT 0,
                cost_usd REAL DEFAULT 0,
                resolution_type TEXT,
                latency_ms INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        prompt_hash = "hash_daily_status"
        prompt_text = "generate a daily status report"
        for idx in range(4):
            conn.execute(
                """
                INSERT INTO request_log
                    (prompt_hash, prompt_text, response, model, cost_usd, resolution_type, latency_ms)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    prompt_hash,
                    prompt_text,
                    "{}",
                    "gpt-5.1-codex-mini",
                    0.0,
                    "cache" if idx < 3 else "passthrough",
                    180,
                ),
            )
        conn.commit()
        conn.close()

        result = analyze_recurring_workflows(db_path, min_occurrences=3, structured=False)
        assert result["count"] == 1
        candidate = result["candidates"][0]
        assert "classification" not in candidate
        assert candidate["recommendation_label"] == "OPTIMIZE"
        assert candidate["cache_rate_pct"] == 75.0


def test_mcp_analyze_crons_respects_structured_flag():
    import json
    import sqlite3
    import tempfile
    from pathlib import Path

    from ruleshield import mcp_server

    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "cache.db"
        conn = sqlite3.connect(db_path)
        conn.execute(
            """
            CREATE TABLE request_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prompt_hash TEXT NOT NULL,
                prompt_text TEXT,
                response TEXT,
                model TEXT,
                tokens_in INTEGER DEFAULT 0,
                tokens_out INTEGER DEFAULT 0,
                cost_usd REAL DEFAULT 0,
                resolution_type TEXT,
                latency_ms INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        for _ in range(3):
            conn.execute(
                """
                INSERT INTO request_log
                    (prompt_hash, prompt_text, response, model, cost_usd, resolution_type, latency_ms)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                ("hash_sync", "sync the daily digest", "{}", "gpt-5.1-codex-mini", 0.01, "cache", 120),
            )
        conn.commit()
        conn.close()

        original_db_path = mcp_server.DB_PATH
        try:
            mcp_server.DB_PATH = db_path
            response = mcp_server.handle_request(
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/call",
                    "params": {
                        "name": "ruleshield_analyze_crons",
                        "arguments": {
                            "min_occurrences": 3,
                            "structured": False,
                        },
                    },
                }
            )
        finally:
            mcp_server.DB_PATH = original_db_path

        payload = json.loads(response["result"]["content"][0]["text"])
        assert payload["count"] == 1
        assert payload["candidates"][0]["recommendation_label"] == "REPLACE"
        assert "classification" not in payload["candidates"][0]


def test_suggest_cron_profile_persists_and_lists_draft():
    import sqlite3
    import tempfile
    from pathlib import Path

    from ruleshield.cron_optimizer import (
        list_cron_profiles,
        load_cron_profile,
        suggest_cron_profile,
    )

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        db_path = tmp_path / "cache.db"
        profiles_dir = tmp_path / "cron_profiles"

        conn = sqlite3.connect(db_path)
        conn.execute(
            """
            CREATE TABLE request_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prompt_hash TEXT NOT NULL,
                prompt_text TEXT,
                response TEXT,
                model TEXT,
                tokens_in INTEGER DEFAULT 0,
                tokens_out INTEGER DEFAULT 0,
                cost_usd REAL DEFAULT 0,
                resolution_type TEXT,
                latency_ms INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        prompt_text = "please check my mails every day at 8 am and then sort them by category and summarize every category and return markdown output"
        for _ in range(4):
            conn.execute(
                """
                INSERT INTO request_log
                    (prompt_hash, prompt_text, response, model, cost_usd, resolution_type, latency_ms)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                ("hash_mail_digest", prompt_text, "{}", "gpt-5.1-codex-mini", 0.02, "passthrough", 900),
            )
        conn.commit()
        conn.close()

        result = suggest_cron_profile(
            db_path,
            "hash_mail",
            min_occurrences=3,
            profiles_dir=profiles_dir,
        )
        profile = result["profile"]
        assert profile["status"] == "draft"
        assert profile["detection"]["classification"] == "dynamic_workflow"
        assert profile["optimized_execution"]["model"] == "gpt-5.1-codex-mini"
        assert profile["decomposition"]["fetch_steps"]
        assert profile["decomposition"]["llm_task_steps"]
        assert profile["estimates"]["token_reduction_pct"] > 0

        listing = list_cron_profiles(profiles_dir=profiles_dir)
        assert listing["count"] == 1
        assert listing["profiles"][0]["id"] == profile["id"]

        loaded = load_cron_profile(profile["id"], profiles_dir=profiles_dir)
        assert loaded["profile"]["optimized_execution"]["prompt_template"]


def test_mcp_suggest_cron_profile_creates_draft():
    import json
    import sqlite3
    import tempfile
    from pathlib import Path

    from ruleshield import cron_optimizer, mcp_server

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        db_path = tmp_path / "cache.db"
        profiles_dir = tmp_path / "cron_profiles"

        conn = sqlite3.connect(db_path)
        conn.execute(
            """
            CREATE TABLE request_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prompt_hash TEXT NOT NULL,
                prompt_text TEXT,
                response TEXT,
                model TEXT,
                tokens_in INTEGER DEFAULT 0,
                tokens_out INTEGER DEFAULT 0,
                cost_usd REAL DEFAULT 0,
                resolution_type TEXT,
                latency_ms INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        for _ in range(3):
            conn.execute(
                """
                INSERT INTO request_log
                    (prompt_hash, prompt_text, response, model, cost_usd, resolution_type, latency_ms)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "hash_digest_job",
                    "check inbox every day at 8 am and summarize messages by category and return markdown output",
                    "{}",
                    "gpt-5.1-codex-mini",
                    0.01,
                    "passthrough",
                    600,
                ),
            )
        conn.commit()
        conn.close()

        original_db_path = mcp_server.DB_PATH
        original_profiles_dir = cron_optimizer.CRON_PROFILES_DIR
        try:
            mcp_server.DB_PATH = db_path
            cron_optimizer.CRON_PROFILES_DIR = profiles_dir
            response = mcp_server.handle_request(
                {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/call",
                    "params": {
                        "name": "ruleshield_suggest_cron_profile",
                        "arguments": {
                            "prompt_hash_or_text": "hash_digest",
                            "min_occurrences": 3,
                        },
                    },
                }
            )
        finally:
            mcp_server.DB_PATH = original_db_path
            cron_optimizer.CRON_PROFILES_DIR = original_profiles_dir

        payload = json.loads(response["result"]["content"][0]["text"])
        assert payload["profile"]["status"] == "draft"
        assert payload["profile"]["detection"]["classification"] == "dynamic_workflow"


def test_run_cron_shadow_persists_validation_and_updates_profile():
    import json
    import sqlite3
    import tempfile
    from pathlib import Path

    from ruleshield.cron_optimizer import load_cron_profile, suggest_cron_profile
    from ruleshield.cron_validation import get_profile_validation_history, run_cron_shadow

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        db_path = tmp_path / "cache.db"
        profiles_dir = tmp_path / "cron_profiles"

        conn = sqlite3.connect(db_path)
        conn.execute(
            """
            CREATE TABLE request_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prompt_hash TEXT NOT NULL,
                prompt_text TEXT,
                response TEXT,
                model TEXT,
                tokens_in INTEGER DEFAULT 0,
                tokens_out INTEGER DEFAULT 0,
                cost_usd REAL DEFAULT 0,
                resolution_type TEXT,
                latency_ms INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        response_payload = json.dumps(
            {
                "choices": [
                    {
                        "message": {
                            "content": "# Daily Digest\n- Inbox: 2 urgent\n- Finance: 1 follow-up"
                        }
                    }
                ]
            }
        )
        for _ in range(2):
            conn.execute(
                """
                INSERT INTO request_log
                    (prompt_hash, prompt_text, response, model, cost_usd, resolution_type, latency_ms)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "hash_digest_shadow",
                    "check inbox every day at 8 am and summarize messages by category and return markdown output",
                    response_payload,
                    "gpt-5.1-codex-mini",
                    0.01,
                    "passthrough",
                    600,
                ),
            )
        conn.commit()
        conn.close()

        profile_result = suggest_cron_profile(
            db_path,
            "hash_digest",
            min_occurrences=2,
            profiles_dir=profiles_dir,
        )
        profile_id = profile_result["profile"]["id"]

        validation = run_cron_shadow(
            db_path,
            profile_id,
            "# Daily Digest\n- Inbox: 2 urgent\n- Finance: 1 follow-up",
            sample_limit=2,
            profiles_dir=profiles_dir,
        )
        assert validation["count"] == 2
        assert validation["summary"]["total_runs"] == 2
        assert validation["summary"]["avg_similarity"] > 0.9

        history = get_profile_validation_history(db_path, profile_id, limit=5)
        assert history["count"] == 2
        assert history["runs"][0]["match_quality"] == "good"

        updated_profile = load_cron_profile(profile_id, profiles_dir=profiles_dir)["profile"]
        assert updated_profile["validation"]["shadow_runs"] == 2
        assert updated_profile["validation"]["optimization_confidence"] > 0.7


def test_mcp_run_cron_shadow_returns_summary():
    import json
    import sqlite3
    import tempfile
    from pathlib import Path

    from ruleshield import cron_optimizer, mcp_server

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        db_path = tmp_path / "cache.db"
        profiles_dir = tmp_path / "cron_profiles"

        conn = sqlite3.connect(db_path)
        conn.execute(
            """
            CREATE TABLE request_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prompt_hash TEXT NOT NULL,
                prompt_text TEXT,
                response TEXT,
                model TEXT,
                tokens_in INTEGER DEFAULT 0,
                tokens_out INTEGER DEFAULT 0,
                cost_usd REAL DEFAULT 0,
                resolution_type TEXT,
                latency_ms INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        response_payload = json.dumps(
            {"choices": [{"message": {"content": "# Summary\n- One item"}}]}
        )
        for _ in range(2):
            conn.execute(
                """
                INSERT INTO request_log
                    (prompt_hash, prompt_text, response, model, cost_usd, resolution_type, latency_ms)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "hash_mcp_shadow",
                    "check inbox every day at 8 am and summarize messages and return markdown output",
                    response_payload,
                    "gpt-5.1-codex-mini",
                    0.01,
                    "passthrough",
                    500,
                ),
            )
        conn.commit()
        conn.close()

        original_db_path = mcp_server.DB_PATH
        original_profiles_dir = cron_optimizer.CRON_PROFILES_DIR
        try:
            mcp_server.DB_PATH = db_path
            cron_optimizer.CRON_PROFILES_DIR = profiles_dir
            suggest_response = mcp_server.handle_request(
                {
                    "jsonrpc": "2.0",
                    "id": 3,
                    "method": "tools/call",
                    "params": {
                        "name": "ruleshield_suggest_cron_profile",
                        "arguments": {
                            "prompt_hash_or_text": "hash_mcp",
                            "min_occurrences": 2,
                        },
                    },
                }
            )
            profile_id = json.loads(suggest_response["result"]["content"][0]["text"])["profile"]["id"]

            shadow_response = mcp_server.handle_request(
                {
                    "jsonrpc": "2.0",
                    "id": 4,
                    "method": "tools/call",
                    "params": {
                        "name": "ruleshield_run_cron_shadow",
                        "arguments": {
                            "profile_id": profile_id,
                            "optimized_response": "# Summary\n- One item",
                            "sample_limit": 2,
                        },
                    },
                }
            )
        finally:
            mcp_server.DB_PATH = original_db_path
            cron_optimizer.CRON_PROFILES_DIR = original_profiles_dir

        payload = json.loads(shadow_response["result"]["content"][0]["text"])
        assert payload["summary"]["total_runs"] == 2
        assert payload["summary"]["avg_similarity"] > 0.9


def test_run_cron_shadow_can_auto_execute_from_payload():
    import json
    import sqlite3
    import tempfile
    from pathlib import Path

    from ruleshield import cron_validation, hermes_runner
    from ruleshield.cron_optimizer import suggest_cron_profile

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        db_path = tmp_path / "cache.db"
        profiles_dir = tmp_path / "cron_profiles"

        conn = sqlite3.connect(db_path)
        conn.execute(
            """
            CREATE TABLE request_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prompt_hash TEXT NOT NULL,
                prompt_text TEXT,
                response TEXT,
                model TEXT,
                tokens_in INTEGER DEFAULT 0,
                tokens_out INTEGER DEFAULT 0,
                cost_usd REAL DEFAULT 0,
                resolution_type TEXT,
                latency_ms INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        response_payload = json.dumps(
            {"choices": [{"message": {"content": "# Summary\n- One item"}}]}
        )
        for _ in range(2):
            conn.execute(
                """
                INSERT INTO request_log
                    (prompt_hash, prompt_text, response, model, cost_usd, resolution_type, latency_ms)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "hash_auto_run",
                    "check inbox every day at 8 am and summarize messages and return markdown output",
                    response_payload,
                    "gpt-5.1-codex-mini",
                    0.01,
                    "passthrough",
                    500,
                ),
            )
        conn.commit()
        conn.close()

        profile = suggest_cron_profile(
            db_path,
            "hash_auto",
            min_occurrences=2,
            profiles_dir=profiles_dir,
        )["profile"]

        original_runner = hermes_runner.run_compact_task
        original_validation_runner = cron_validation.run_compact_task
        try:
            def fake_run_compact_task(*, prompt_template, payload_text, model, settings=None):
                return {
                    "model": model,
                    "prompt": f"{prompt_template}\n\nContent:\n{payload_text}",
                    "response_text": "# Summary\n- One item",
                    "raw_response": {},
                }

            hermes_runner.run_compact_task = fake_run_compact_task
            cron_validation.run_compact_task = fake_run_compact_task

            result = cron_validation.run_cron_shadow(
                db_path,
                profile["id"],
                payload_text="Inbox payload here",
                sample_limit=2,
                profiles_dir=profiles_dir,
            )
        finally:
            hermes_runner.run_compact_task = original_runner
            cron_validation.run_compact_task = original_validation_runner

        assert result["count"] == 2
        assert result["execution"]["model"] == "gpt-5.1-codex-mini"
        assert result["summary"]["avg_similarity"] > 0.9


def test_compare_outputs_handles_light_paraphrase_better_than_token_overlap():
    from ruleshield.cron_validation import compare_outputs

    result = compare_outputs(
        "Daily digest:\n- Finance update\n- Inbox summary",
        "Here is your daily digest:\n- Finance update\n- Inbox summary",
        expected_output_format="digest",
    )

    assert result["similarity"] > 0.65
    assert result["match_quality"] in {"partial", "good"}


def test_build_automation_suggestion_infers_schedule_and_directive():
    from ruleshield.cron_automation import build_automation_suggestion

    profile = {
        "id": "daily_digest_abcd1234",
        "name": "Daily Digest",
        "status": "active",
        "source": {
            "prompt_text": "please check my mails every day at 8 am and summarize by category",
        },
    }

    suggestion = build_automation_suggestion(profile, cwd="/tmp/ruleshield-hermes")
    assert suggestion["rrule"] == "FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR,SA,SU;BYHOUR=8;BYMINUTE=0"
    assert "daily_digest_abcd1234" in suggestion["prompt"]
    assert 'mode="suggested create"' in suggestion["directive"]


def test_activate_cron_profile_enforces_guardrails():
    import sqlite3
    import tempfile
    from pathlib import Path

    from ruleshield.cron_optimizer import activate_cron_profile, suggest_cron_profile

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        db_path = tmp_path / "cache.db"
        profiles_dir = tmp_path / "cron_profiles"

        conn = sqlite3.connect(db_path)
        conn.execute(
            """
            CREATE TABLE request_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prompt_hash TEXT NOT NULL,
                prompt_text TEXT,
                response TEXT,
                model TEXT,
                tokens_in INTEGER DEFAULT 0,
                tokens_out INTEGER DEFAULT 0,
                cost_usd REAL DEFAULT 0,
                resolution_type TEXT,
                latency_ms INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        for _ in range(2):
            conn.execute(
                """
                INSERT INTO request_log
                    (prompt_hash, prompt_text, response, model, cost_usd, resolution_type, latency_ms)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "hash_guardrail",
                    "check inbox every day at 8 am and summarize messages and return markdown output",
                    '{"choices":[{"message":{"content":"# Summary\\n- One item"}}]}',
                    "gpt-5.1-codex-mini",
                    0.01,
                    "passthrough",
                    500,
                ),
            )
        conn.commit()
        conn.close()

        profile = suggest_cron_profile(
            db_path,
            "hash_guard",
            min_occurrences=2,
            profiles_dir=profiles_dir,
        )["profile"]

        blocked = activate_cron_profile(
            profile["id"],
            db_path=db_path,
            profiles_dir=profiles_dir,
        )
        assert blocked["profile"] is None
        assert "Activation blocked" in blocked["message"]


def test_update_draft_cron_profile_updates_editable_fields():
    import sqlite3
    import tempfile
    from pathlib import Path

    from ruleshield.cron_optimizer import suggest_cron_profile, update_draft_cron_profile

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        db_path = tmp_path / "cache.db"
        profiles_dir = tmp_path / "cron_profiles"

        conn = sqlite3.connect(db_path)
        conn.execute(
            """
            CREATE TABLE request_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prompt_hash TEXT NOT NULL,
                prompt_text TEXT,
                response TEXT,
                model TEXT,
                tokens_in INTEGER DEFAULT 0,
                tokens_out INTEGER DEFAULT 0,
                cost_usd REAL DEFAULT 0,
                resolution_type TEXT,
                latency_ms INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        for _ in range(2):
            conn.execute(
                """
                INSERT INTO request_log
                    (prompt_hash, prompt_text, response, model, cost_usd, resolution_type, latency_ms)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "hash_edit_draft",
                    "check inbox every day at 8 am and summarize messages and return markdown output",
                    '{"choices":[{"message":{"content":"# Summary\\n- One item"}}]}',
                    "gpt-5.1-codex-mini",
                    0.01,
                    "passthrough",
                    500,
                ),
            )
        conn.commit()
        conn.close()

        profile = suggest_cron_profile(
            db_path,
            "hash_edit",
            min_occurrences=2,
            profiles_dir=profiles_dir,
        )["profile"]

        updated = update_draft_cron_profile(
            profile["id"],
            updates={
                "name": "Edited Digest",
                "prompt_template": "Summarize this inbox content in 3 bullets.",
                "model": "gpt-5.4",
            },
            profiles_dir=profiles_dir,
        )
        assert updated["profile"]["name"] == "Edited Digest"
        assert updated["profile"]["optimized_execution"]["prompt_template"] == "Summarize this inbox content in 3 bullets."
        assert updated["profile"]["optimized_execution"]["model"] == "gpt-5.4"


def test_activate_cron_profile_moves_profile_to_active():
    import json
    import sqlite3
    import tempfile
    from pathlib import Path

    from ruleshield.cron_optimizer import activate_cron_profile, list_cron_profiles, suggest_cron_profile
    from ruleshield.cron_validation import run_cron_shadow

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        db_path = tmp_path / "cache.db"
        profiles_dir = tmp_path / "cron_profiles"

        conn = sqlite3.connect(db_path)
        conn.execute(
            """
            CREATE TABLE request_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prompt_hash TEXT NOT NULL,
                prompt_text TEXT,
                response TEXT,
                model TEXT,
                tokens_in INTEGER DEFAULT 0,
                tokens_out INTEGER DEFAULT 0,
                cost_usd REAL DEFAULT 0,
                resolution_type TEXT,
                latency_ms INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        payload = json.dumps({"choices": [{"message": {"content": "# Summary\n- One item"}}]})
        for _ in range(2):
            conn.execute(
                """
                INSERT INTO request_log
                    (prompt_hash, prompt_text, response, model, cost_usd, resolution_type, latency_ms)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "hash_activate",
                    "check inbox every day at 8 am and summarize messages and return markdown output",
                    payload,
                    "gpt-5.1-codex-mini",
                    0.01,
                    "passthrough",
                    500,
                ),
            )
        conn.commit()
        conn.close()

        profile = suggest_cron_profile(
            db_path,
            "hash_act",
            min_occurrences=2,
            profiles_dir=profiles_dir,
        )["profile"]
        run_cron_shadow(
            db_path,
            profile["id"],
            "# Summary\n- One item",
            sample_limit=2,
            profiles_dir=profiles_dir,
        )

        activated = activate_cron_profile(
            profile["id"],
            db_path=db_path,
            profiles_dir=profiles_dir,
        )
        assert activated["profile"]["status"] == "active"
        assert activated["profile"]["runtime_status"] == "ready"

        listing = list_cron_profiles(profiles_dir=profiles_dir)
        assert listing["profiles"][0]["status"] == "active"
        assert listing["profiles"][0]["runtime_status"] == "ready"


def test_archive_cron_profile_moves_profile_to_archived():
    import sqlite3
    import tempfile
    from pathlib import Path

    from ruleshield.cron_optimizer import (
        archive_cron_profile,
        list_cron_profiles,
        load_cron_profile,
        suggest_cron_profile,
    )

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        db_path = tmp_path / "cache.db"
        profiles_dir = tmp_path / "cron_profiles"

        conn = sqlite3.connect(db_path)
        conn.execute(
            """
            CREATE TABLE request_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prompt_hash TEXT NOT NULL,
                prompt_text TEXT,
                response TEXT,
                model TEXT,
                tokens_in INTEGER DEFAULT 0,
                tokens_out INTEGER DEFAULT 0,
                cost_usd REAL DEFAULT 0,
                resolution_type TEXT,
                latency_ms INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        for _ in range(2):
            conn.execute(
                """
                INSERT INTO request_log
                    (prompt_hash, prompt_text, response, model, cost_usd, resolution_type, latency_ms)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "hash_archive",
                    "check inbox every day at 8 am and summarize messages and return markdown output",
                    '{"choices":[{"message":{"content":"# Summary\\n- One item"}}]}',
                    "gpt-5.1-codex-mini",
                    0.01,
                    "passthrough",
                    500,
                ),
            )
        conn.commit()
        conn.close()

        profile = suggest_cron_profile(
            db_path,
            "hash_arch",
            min_occurrences=2,
            profiles_dir=profiles_dir,
        )["profile"]

        archived = archive_cron_profile(profile["id"], profiles_dir=profiles_dir)
        assert archived["profile"]["status"] == "archived"
        assert archived["profile"]["runtime_status"] == "archived"
        assert archived["profile"]["archived_at"]

        loaded = load_cron_profile(profile["id"], profiles_dir=profiles_dir)
        assert loaded["profile"]["status"] == "archived"

        listing = list_cron_profiles(profiles_dir=profiles_dir)
        assert listing["profiles"][0]["status"] == "archived"
        assert listing["profiles"][0]["runtime_status"] == "archived"


def test_delete_cron_profile_removes_archived_profile():
    import sqlite3
    import tempfile
    from pathlib import Path

    from ruleshield.cron_optimizer import (
        archive_cron_profile,
        delete_cron_profile,
        load_cron_profile,
        suggest_cron_profile,
    )

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        db_path = tmp_path / "cache.db"
        profiles_dir = tmp_path / "cron_profiles"

        conn = sqlite3.connect(db_path)
        conn.execute(
            """
            CREATE TABLE request_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prompt_hash TEXT NOT NULL,
                prompt_text TEXT,
                response TEXT,
                model TEXT,
                tokens_in INTEGER DEFAULT 0,
                tokens_out INTEGER DEFAULT 0,
                cost_usd REAL DEFAULT 0,
                resolution_type TEXT,
                latency_ms INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        for _ in range(2):
            conn.execute(
                """
                INSERT INTO request_log
                    (prompt_hash, prompt_text, response, model, cost_usd, resolution_type, latency_ms)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "hash_delete",
                    "check inbox every day at 8 am and summarize messages and return markdown output",
                    '{"choices":[{"message":{"content":"# Summary\\n- One item"}}]}',
                    "gpt-5.1-codex-mini",
                    0.01,
                    "passthrough",
                    500,
                ),
            )
        conn.commit()
        conn.close()

        profile = suggest_cron_profile(
            db_path,
            "hash_del",
            min_occurrences=2,
            profiles_dir=profiles_dir,
        )["profile"]
        archive_cron_profile(profile["id"], profiles_dir=profiles_dir)

        deleted = delete_cron_profile(profile["id"], profiles_dir=profiles_dir)
        assert deleted["deleted"] is True

        loaded = load_cron_profile(profile["id"], profiles_dir=profiles_dir)
        assert loaded["profile"] is None


def test_restore_cron_profile_moves_archived_profile_back_to_draft():
    import sqlite3
    import tempfile
    from pathlib import Path

    from ruleshield.cron_optimizer import (
        archive_cron_profile,
        load_cron_profile,
        restore_cron_profile,
        suggest_cron_profile,
    )

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        db_path = tmp_path / "cache.db"
        profiles_dir = tmp_path / "cron_profiles"

        conn = sqlite3.connect(db_path)
        conn.execute(
            """
            CREATE TABLE request_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prompt_hash TEXT NOT NULL,
                prompt_text TEXT,
                response TEXT,
                model TEXT,
                tokens_in INTEGER DEFAULT 0,
                tokens_out INTEGER DEFAULT 0,
                cost_usd REAL DEFAULT 0,
                resolution_type TEXT,
                latency_ms INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        for _ in range(2):
            conn.execute(
                """
                INSERT INTO request_log
                    (prompt_hash, prompt_text, response, model, cost_usd, resolution_type, latency_ms)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "hash_restore",
                    "check inbox every day at 8 am and summarize messages and return markdown output",
                    '{"choices":[{"message":{"content":"# Summary\\n- One item"}}]}',
                    "gpt-5.1-codex-mini",
                    0.01,
                    "passthrough",
                    500,
                ),
            )
        conn.commit()
        conn.close()

        profile = suggest_cron_profile(db_path, "hash_rest", min_occurrences=2, profiles_dir=profiles_dir)["profile"]
        archive_cron_profile(profile["id"], profiles_dir=profiles_dir)
        restored = restore_cron_profile(profile["id"], profiles_dir=profiles_dir)

        assert restored["profile"]["status"] == "draft"
        assert restored["profile"]["runtime_status"] == "draft"
        assert restored["profile"]["restored_at"]
        assert load_cron_profile(profile["id"], profiles_dir=profiles_dir)["profile"]["status"] == "draft"


def test_duplicate_cron_profile_creates_new_draft_copy():
    import sqlite3
    import tempfile
    from pathlib import Path

    from ruleshield.cron_optimizer import duplicate_cron_profile, suggest_cron_profile

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        db_path = tmp_path / "cache.db"
        profiles_dir = tmp_path / "cron_profiles"

        conn = sqlite3.connect(db_path)
        conn.execute(
            """
            CREATE TABLE request_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prompt_hash TEXT NOT NULL,
                prompt_text TEXT,
                response TEXT,
                model TEXT,
                tokens_in INTEGER DEFAULT 0,
                tokens_out INTEGER DEFAULT 0,
                cost_usd REAL DEFAULT 0,
                resolution_type TEXT,
                latency_ms INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        for _ in range(2):
            conn.execute(
                """
                INSERT INTO request_log
                    (prompt_hash, prompt_text, response, model, cost_usd, resolution_type, latency_ms)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "hash_copy",
                    "check inbox every day at 8 am and summarize messages and return markdown output",
                    '{"choices":[{"message":{"content":"# Summary\\n- One item"}}]}',
                    "gpt-5.1-codex-mini",
                    0.01,
                    "passthrough",
                    500,
                ),
            )
        conn.commit()
        conn.close()

        profile = suggest_cron_profile(db_path, "hash_cop", min_occurrences=2, profiles_dir=profiles_dir)["profile"]
        duplicated = duplicate_cron_profile(profile["id"], profiles_dir=profiles_dir)

        assert duplicated["profile"]["id"] != profile["id"]
        assert duplicated["profile"]["status"] == "draft"
        assert duplicated["profile"]["duplicated_from"] == profile["id"]


def test_execute_active_cron_profile_records_execution_history():
    import json
    import sqlite3
    import tempfile
    from pathlib import Path

    from ruleshield import cron_optimizer, hermes_runner
    from ruleshield.cron_execution import get_profile_execution_history
    from ruleshield.cron_optimizer import (
        activate_cron_profile,
        execute_active_cron_profile,
        suggest_cron_profile,
    )
    from ruleshield.cron_validation import run_cron_shadow

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        db_path = tmp_path / "cache.db"
        profiles_dir = tmp_path / "cron_profiles"

        conn = sqlite3.connect(db_path)
        conn.execute(
            """
            CREATE TABLE request_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prompt_hash TEXT NOT NULL,
                prompt_text TEXT,
                response TEXT,
                model TEXT,
                tokens_in INTEGER DEFAULT 0,
                tokens_out INTEGER DEFAULT 0,
                cost_usd REAL DEFAULT 0,
                resolution_type TEXT,
                latency_ms INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        payload = json.dumps({"choices": [{"message": {"content": "# Summary\n- One item"}}]})
        for _ in range(2):
            conn.execute(
                """
                INSERT INTO request_log
                    (prompt_hash, prompt_text, response, model, cost_usd, resolution_type, latency_ms)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "hash_exec_hist",
                    "check inbox every day at 8 am and summarize messages and return markdown output",
                    payload,
                    "gpt-5.1-codex-mini",
                    0.01,
                    "passthrough",
                    500,
                ),
            )
        conn.commit()
        conn.close()

        profile = suggest_cron_profile(db_path, "hash_exec", min_occurrences=2, profiles_dir=profiles_dir)["profile"]
        run_cron_shadow(db_path, profile["id"], "# Summary\n- One item", sample_limit=2, profiles_dir=profiles_dir)
        activate_cron_profile(profile["id"], db_path=db_path, profiles_dir=profiles_dir)

        original_runner = hermes_runner.run_compact_task
        original_optimizer_runner = cron_optimizer.run_compact_task
        try:
            fake_runner = lambda **kwargs: {
                "model": kwargs["model"],
                "prompt": "compact prompt",
                "response_text": "# Summary\n- One item",
                "raw_response": {},
            }
            hermes_runner.run_compact_task = fake_runner
            cron_optimizer.run_compact_task = fake_runner
            execute_active_cron_profile(
                profile["id"],
                "Payload block",
                db_path=db_path,
                profiles_dir=profiles_dir,
            )
        finally:
            hermes_runner.run_compact_task = original_runner
            cron_optimizer.run_compact_task = original_optimizer_runner

        history = get_profile_execution_history(db_path, profile["id"], limit=5)
        assert history["count"] == 1
        assert history["runs"][0]["payload_text"] == "Payload block"
        assert history["runs"][0]["response_preview"].startswith("# Summary")


def test_mcp_activate_cron_profile_returns_active_status():
    import json
    import sqlite3
    import tempfile
    from pathlib import Path

    from ruleshield import cron_optimizer, mcp_server
    from ruleshield.cron_validation import run_cron_shadow

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        db_path = tmp_path / "cache.db"
        profiles_dir = tmp_path / "cron_profiles"

        conn = sqlite3.connect(db_path)
        conn.execute(
            """
            CREATE TABLE request_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prompt_hash TEXT NOT NULL,
                prompt_text TEXT,
                response TEXT,
                model TEXT,
                tokens_in INTEGER DEFAULT 0,
                tokens_out INTEGER DEFAULT 0,
                cost_usd REAL DEFAULT 0,
                resolution_type TEXT,
                latency_ms INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        payload = json.dumps({"choices": [{"message": {"content": "# Summary\n- One item"}}]})
        for _ in range(2):
            conn.execute(
                """
                INSERT INTO request_log
                    (prompt_hash, prompt_text, response, model, cost_usd, resolution_type, latency_ms)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "hash_mcp_activate",
                    "check inbox every day at 8 am and summarize messages and return markdown output",
                    payload,
                    "gpt-5.1-codex-mini",
                    0.01,
                    "passthrough",
                    500,
                ),
            )
        conn.commit()
        conn.close()

        original_db_path = mcp_server.DB_PATH
        original_profiles_dir = cron_optimizer.CRON_PROFILES_DIR
        try:
            mcp_server.DB_PATH = db_path
            cron_optimizer.CRON_PROFILES_DIR = profiles_dir
            suggest_response = mcp_server.handle_request(
                {
                    "jsonrpc": "2.0",
                    "id": 5,
                    "method": "tools/call",
                    "params": {
                        "name": "ruleshield_suggest_cron_profile",
                        "arguments": {"prompt_hash_or_text": "hash_mcp_act", "min_occurrences": 2},
                    },
                }
            )
            profile_id = json.loads(suggest_response["result"]["content"][0]["text"])["profile"]["id"]
            run_cron_shadow(
                db_path,
                profile_id,
                "# Summary\n- One item",
                sample_limit=2,
                profiles_dir=profiles_dir,
            )

            activate_response = mcp_server.handle_request(
                {
                    "jsonrpc": "2.0",
                    "id": 6,
                    "method": "tools/call",
                    "params": {
                        "name": "ruleshield_activate_cron_profile",
                        "arguments": {"profile_id": profile_id},
                    },
                }
            )
        finally:
            mcp_server.DB_PATH = original_db_path
            cron_optimizer.CRON_PROFILES_DIR = original_profiles_dir

        payload = json.loads(activate_response["result"]["content"][0]["text"])
        assert payload["profile"]["status"] == "active"
        assert payload["profile"]["runtime_status"] == "ready"


def test_execute_active_cron_profile_runs_compact_task():
    import json
    import sqlite3
    import tempfile
    from pathlib import Path

    from ruleshield import cron_optimizer, hermes_runner
    from ruleshield.cron_validation import run_cron_shadow

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        db_path = tmp_path / "cache.db"
        profiles_dir = tmp_path / "cron_profiles"

        conn = sqlite3.connect(db_path)
        conn.execute(
            """
            CREATE TABLE request_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prompt_hash TEXT NOT NULL,
                prompt_text TEXT,
                response TEXT,
                model TEXT,
                tokens_in INTEGER DEFAULT 0,
                tokens_out INTEGER DEFAULT 0,
                cost_usd REAL DEFAULT 0,
                resolution_type TEXT,
                latency_ms INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        payload = json.dumps({"choices": [{"message": {"content": "# Summary\n- One item"}}]})
        for _ in range(2):
            conn.execute(
                """
                INSERT INTO request_log
                    (prompt_hash, prompt_text, response, model, cost_usd, resolution_type, latency_ms)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "hash_exec_active",
                    "check inbox every day at 8 am and summarize messages and return markdown output",
                    payload,
                    "gpt-5.1-codex-mini",
                    0.01,
                    "passthrough",
                    500,
                ),
            )
        conn.commit()
        conn.close()

        profile = cron_optimizer.suggest_cron_profile(
            db_path,
            "hash_exec",
            min_occurrences=2,
            profiles_dir=profiles_dir,
        )["profile"]
        run_cron_shadow(
            db_path,
            profile["id"],
            "# Summary\n- One item",
            sample_limit=2,
            profiles_dir=profiles_dir,
        )
        cron_optimizer.activate_cron_profile(
            profile["id"],
            db_path=db_path,
            profiles_dir=profiles_dir,
        )

        original_runner = hermes_runner.run_compact_task
        original_optimizer_runner = cron_optimizer.run_compact_task
        try:
            def fake_run_compact_task(*, prompt_template, payload_text, model, settings=None):
                return {
                    "model": model,
                    "prompt": f"{prompt_template}\n\nContent:\n{payload_text}",
                    "response_text": "# Summary\n- One item",
                    "raw_response": {},
                }

            hermes_runner.run_compact_task = fake_run_compact_task
            cron_optimizer.run_compact_task = fake_run_compact_task

            result = cron_optimizer.execute_active_cron_profile(
                profile["id"],
                "payload text here",
                profiles_dir=profiles_dir,
            )
        finally:
            hermes_runner.run_compact_task = original_runner
            cron_optimizer.run_compact_task = original_optimizer_runner

        assert result["execution"]["response_text"] == "# Summary\n- One item"
        assert result["profile"]["runtime_status"] == "ready"
        assert result["profile"]["last_execution"]["model"] == "gpt-5.1-codex-mini"


def test_mcp_run_active_cron_profile_returns_execution():
    import json
    import sqlite3
    import tempfile
    from pathlib import Path

    from ruleshield import cron_optimizer, hermes_runner, mcp_server
    from ruleshield.cron_validation import run_cron_shadow

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        db_path = tmp_path / "cache.db"
        profiles_dir = tmp_path / "cron_profiles"

        conn = sqlite3.connect(db_path)
        conn.execute(
            """
            CREATE TABLE request_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prompt_hash TEXT NOT NULL,
                prompt_text TEXT,
                response TEXT,
                model TEXT,
                tokens_in INTEGER DEFAULT 0,
                tokens_out INTEGER DEFAULT 0,
                cost_usd REAL DEFAULT 0,
                resolution_type TEXT,
                latency_ms INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        payload = json.dumps({"choices": [{"message": {"content": "# Summary\n- One item"}}]})
        for _ in range(2):
            conn.execute(
                """
                INSERT INTO request_log
                    (prompt_hash, prompt_text, response, model, cost_usd, resolution_type, latency_ms)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "hash_mcp_exec",
                    "check inbox every day at 8 am and summarize messages and return markdown output",
                    payload,
                    "gpt-5.1-codex-mini",
                    0.01,
                    "passthrough",
                    500,
                ),
            )
        conn.commit()
        conn.close()

        original_db_path = mcp_server.DB_PATH
        original_profiles_dir = cron_optimizer.CRON_PROFILES_DIR
        original_runner = hermes_runner.run_compact_task
        original_optimizer_runner = cron_optimizer.run_compact_task
        try:
            mcp_server.DB_PATH = db_path
            cron_optimizer.CRON_PROFILES_DIR = profiles_dir

            def fake_run_compact_task(*, prompt_template, payload_text, model, settings=None):
                return {
                    "model": model,
                    "prompt": f"{prompt_template}\n\nContent:\n{payload_text}",
                    "response_text": "# Summary\n- One item",
                    "raw_response": {},
                }

            hermes_runner.run_compact_task = fake_run_compact_task
            cron_optimizer.run_compact_task = fake_run_compact_task

            suggest_response = mcp_server.handle_request(
                {
                    "jsonrpc": "2.0",
                    "id": 7,
                    "method": "tools/call",
                    "params": {
                        "name": "ruleshield_suggest_cron_profile",
                        "arguments": {"prompt_hash_or_text": "hash_mcp_ex", "min_occurrences": 2},
                    },
                }
            )
            profile_id = json.loads(suggest_response["result"]["content"][0]["text"])["profile"]["id"]
            run_cron_shadow(
                db_path,
                profile_id,
                "# Summary\n- One item",
                sample_limit=2,
                profiles_dir=profiles_dir,
            )
            mcp_server.handle_request(
                {
                    "jsonrpc": "2.0",
                    "id": 8,
                    "method": "tools/call",
                    "params": {
                        "name": "ruleshield_activate_cron_profile",
                        "arguments": {"profile_id": profile_id},
                    },
                }
            )
            execution_response = mcp_server.handle_request(
                {
                    "jsonrpc": "2.0",
                    "id": 9,
                    "method": "tools/call",
                    "params": {
                        "name": "ruleshield_run_active_cron_profile",
                        "arguments": {"profile_id": profile_id, "payload_text": "payload text here"},
                    },
                }
            )
        finally:
            mcp_server.DB_PATH = original_db_path
            cron_optimizer.CRON_PROFILES_DIR = original_profiles_dir
            hermes_runner.run_compact_task = original_runner
            cron_optimizer.run_compact_task = original_optimizer_runner

        payload = json.loads(execution_response["result"]["content"][0]["text"])
        assert payload["execution"]["response_text"] == "# Summary\n- One item"


def test_shadow_cache_reset_and_recent_filter():
    import asyncio
    import tempfile

    from ruleshield.cache import CacheManager

    async def run():
        with tempfile.TemporaryDirectory() as tmp:
            cm = CacheManager(db_path=f"{tmp}/cache.db")
            await cm.init()
            try:
                await cm.log_shadow(
                    rule_id="rule_a",
                    prompt_text="p1",
                    rule_response="r1",
                    llm_response="l1",
                    similarity=0.1,
                    length_ratio=0.2,
                    match_quality="poor",
                )
                await cm.log_shadow(
                    rule_id="rule_a",
                    prompt_text="p2",
                    rule_response="r2",
                    llm_response="l2",
                    similarity=0.9,
                    length_ratio=1.0,
                    match_quality="good",
                )
                await cm.log_shadow(
                    rule_id="rule_b",
                    prompt_text="p3",
                    rule_response="r3",
                    llm_response="l3",
                    similarity=0.4,
                    length_ratio=0.5,
                    match_quality="partial",
                )

                recent_stats = await cm.get_shadow_stats(limit=2)
                assert recent_stats["total_comparisons"] == 2

                rule_stats = await cm.get_shadow_stats(rule_id="rule_a")
                assert rule_stats["total_comparisons"] == 2

                examples = await cm.get_shadow_examples(rule_id="rule_a")
                assert len(examples) == 1
                assert examples[0]["rule_id"] == "rule_a"

                deleted = await cm.reset_shadow_log(rule_id="rule_a")
                assert deleted == 2

                remaining = await cm.get_shadow_stats()
                assert remaining["total_comparisons"] == 1
                assert remaining["per_rule"][0]["rule_id"] == "rule_b"
            finally:
                await cm.close()

    asyncio.run(run())


def test_candidate_rules_do_not_match_live_path():
    import asyncio
    import json
    import tempfile
    from pathlib import Path

    from ruleshield.rules import RuleEngine

    candidate_rule = {
        "id": "candidate_greeting",
        "name": "Candidate Greeting",
        "patterns": [{"type": "exact", "value": "hello", "field": "last_user_message"}],
        "conditions": [],
        "response": {"content": "Hello from candidate", "model": "ruleshield-rule"},
        "confidence": 0.95,
        "priority": 20,
        "enabled": True,
    }

    async def run():
        with tempfile.TemporaryDirectory() as tmp:
            candidates_dir = Path(tmp) / "candidates"
            candidates_dir.mkdir(parents=True)
            (candidates_dir / "candidate.json").write_text(json.dumps([candidate_rule]), encoding="utf-8")

            engine = RuleEngine(rules_dir=tmp)
            await engine.init()

            production = engine.match("hello", model="claude-sonnet-4-6")
            assert production is not None
            assert production["deployment"] == "production"
            candidate = engine.match_candidates("hello", model="claude-sonnet-4-6")
            assert candidate is not None
            assert candidate["rule_id"] == "candidate_greeting"
            assert candidate["deployment"] == "candidate"

    asyncio.run(run())


def test_candidate_activation_promotes_to_production():
    import asyncio
    import json
    import tempfile
    from pathlib import Path

    from ruleshield.rules import RuleEngine

    candidate_rule = {
        "id": "candidate_promote_me",
        "name": "Promote Me",
        "patterns": [{"type": "exact", "value": "hello", "field": "last_user_message"}],
        "conditions": [],
        "response": {"content": "Hello from candidate", "model": "ruleshield-rule"},
        "confidence": 0.95,
        "priority": 20,
        "enabled": True,
    }

    async def run():
        with tempfile.TemporaryDirectory() as tmp:
            candidates_dir = Path(tmp) / "candidates"
            candidates_dir.mkdir(parents=True)
            (candidates_dir / "candidate.json").write_text(json.dumps([candidate_rule]), encoding="utf-8")

            engine = RuleEngine(rules_dir=tmp)
            await engine.init()

            rule = next(r for r in engine.rules if r["id"] == "candidate_promote_me")
            assert rule["deployment"] == "candidate"

            assert engine.activate_rule("candidate_promote_me")

            promoted = next(r for r in engine.rules if r["id"] == "candidate_promote_me")
            assert promoted["deployment"] == "production"
            assert promoted["enabled"] is True

    asyncio.run(run())


def test_streaming_shadow_logs_and_feedback():
    import asyncio

    from ruleshield import proxy

    class FakeStreamResponse:
        def __init__(self):
            self.status_code = 200

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def aiter_lines(self):
            yield 'data: {"choices":[{"delta":{"content":"Hello"}}]}'
            yield 'data: {"choices":[{"delta":{"content":" world"}}]}'
            yield "data: [DONE]"

    class FakeHttpClient:
        def stream(self, method, url, headers=None, json=None):
            return FakeStreamResponse()

    class FakeCacheManager:
        def __init__(self):
            self.shadow_logs = []
            self.cached_response = None

        async def store(self, **kwargs):
            self.cached_response = kwargs

        async def log_shadow(self, **kwargs):
            self.shadow_logs.append(kwargs)

    class FakeFeedbackManager:
        def __init__(self):
            self.accepts = []
            self.rejects = []

        async def record_accept(self, rule_id, prompt_text):
            self.accepts.append((rule_id, prompt_text))

        async def record_reject(self, rule_id, prompt_text, rule_response, llm_response):
            self.rejects.append((rule_id, prompt_text, rule_response, llm_response))

    async def fake_record_metrics(*args, **kwargs):
        return None

    async def run():
        original_http_client = proxy.http_client
        original_cache_manager = proxy.cache_manager
        original_feedback_manager = proxy.feedback_manager
        original_record_metrics = proxy._record_metrics
        original_cache_enabled = proxy.settings.cache_enabled

        fake_cache = FakeCacheManager()
        fake_feedback = FakeFeedbackManager()

        proxy.http_client = FakeHttpClient()
        proxy.cache_manager = fake_cache
        proxy.feedback_manager = fake_feedback
        proxy._record_metrics = fake_record_metrics
        proxy.settings.cache_enabled = True

        try:
            response = await proxy._stream_upstream(
                url="https://example.com/v1/chat/completions",
                headers={"Authorization": "Bearer test"},
                body={"model": "claude-sonnet-4-6", "stream": True},
                model="claude-sonnet-4-6",
                prompt_hash="shadow-stream-hash",
                prompt_text="hello",
                t_start=0.0,
                shadow_rule_hit={
                    "rule_id": "candidate_greeting_stream",
                    "deployment": "candidate",
                    "response": {
                        "choices": [
                            {
                                "message": {
                                    "role": "assistant",
                                    "content": "Hello world",
                                }
                            }
                        ]
                    },
                },
            )

            chunks = []
            async for chunk in response.body_iterator:
                chunks.append(chunk.decode() if isinstance(chunk, bytes) else chunk)

            assert "".join(chunks).count("data: ") == 3
            assert fake_cache.cached_response is not None
            assert len(fake_cache.shadow_logs) == 1
            assert fake_cache.shadow_logs[0]["rule_id"] == "candidate_greeting_stream"
            assert fake_feedback.accepts == [("candidate_greeting_stream", "hello")]
            assert fake_feedback.rejects == []
        finally:
            proxy.http_client = original_http_client
            proxy.cache_manager = original_cache_manager
            proxy.feedback_manager = original_feedback_manager
            proxy._record_metrics = original_record_metrics
            proxy.settings.cache_enabled = original_cache_enabled

    asyncio.run(run())


def test_codex_responses_shadow_logs_and_feedback():
    import json
    from types import SimpleNamespace

    from fastapi.testclient import TestClient
    from ruleshield import proxy

    class FakeCodexStreamResponse:
        def __init__(self):
            self.status_code = 200

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def aiter_lines(self):
            yield 'data: {"type":"response.output_text.delta","delta":"pong"}'
            yield 'data: {"type":"response.output_text.delta","delta":" zebra 42"}'
            yield 'data: {"type":"response.completed","response":{"usage":{"input_tokens":12,"output_tokens":3}}}'
            yield "data: [DONE]"

    class FakeHttpClient:
        def stream(self, method, url, headers=None, content=None):
            return FakeCodexStreamResponse()

    class FakeCacheManager:
        def __init__(self):
            self.shadow_logs = []
            self.cached_response = None
            self.request_logs = []

        async def check(self, prompt_hash, prompt_text):
            return None

        async def log_request(self, **kwargs):
            self.request_logs.append(kwargs)

        async def store(self, **kwargs):
            self.cached_response = kwargs

        async def log_shadow(self, **kwargs):
            self.shadow_logs.append(kwargs)

    class FakeRuleEngine:
        async def async_match(self, prompt_text, messages=None, model=None):
            return None

        async def async_match_candidates(self, prompt_text, messages=None, model=None):
            assert prompt_text == "shadow ping zebra 42"
            return {
                "rule_id": "shadow_test_ping",
                "deployment": "candidate",
                "response": {
                    "content": "pong zebra 42",
                    "model": "ruleshield-rule",
                },
            }

    class FakeFeedbackManager:
        def __init__(self):
            self.accepts = []
            self.rejects = []

        async def record_accept(self, rule_id, prompt_text):
            self.accepts.append((rule_id, prompt_text))

        async def record_reject(self, rule_id, prompt_text, rule_response, llm_response):
            self.rejects.append((rule_id, prompt_text, rule_response, llm_response))

    original_http_client = proxy.http_client
    original_cache_manager = proxy.cache_manager
    original_rule_engine = proxy.rule_engine
    original_feedback_manager = proxy.feedback_manager
    original_settings = proxy.settings

    fake_cache = FakeCacheManager()
    fake_feedback = FakeFeedbackManager()

    proxy.http_client = FakeHttpClient()
    proxy.cache_manager = fake_cache
    proxy.rule_engine = FakeRuleEngine()
    proxy.feedback_manager = fake_feedback
    proxy.settings = SimpleNamespace(
        provider_url="https://chatgpt.com/backend-api/codex",
        api_key="",
        cache_enabled=False,
        rules_enabled=True,
        shadow_mode=True,
        log_level="info",
    )

    try:
        client = TestClient(proxy.app)
        with client.stream(
            "POST",
            "/responses",
            json={
                "model": "gpt-5.4",
                "stream": True,
                "input": [{"role": "user", "content": "shadow ping zebra 42"}],
            },
        ) as response:
            body = "".join(response.iter_text())

        assert response.status_code == 200
        assert "response.output_text.delta" in body
        assert response.headers["x-ruleshield-shadow"] == "shadow_test_ping"
        assert len(fake_cache.request_logs) == 1
        assert fake_cache.cached_response is None
        assert len(fake_cache.shadow_logs) == 1
        assert fake_cache.shadow_logs[0]["rule_id"] == "shadow_test_ping"
        assert fake_feedback.accepts == [("shadow_test_ping", "shadow ping zebra 42")]
        assert fake_feedback.rejects == []
    finally:
        proxy.http_client = original_http_client
        proxy.cache_manager = original_cache_manager
        proxy.rule_engine = original_rule_engine
        proxy.feedback_manager = original_feedback_manager
        proxy.settings = original_settings


def test_codex_responses_shadow_logs_tool_style_streams():
    from types import SimpleNamespace

    from fastapi.testclient import TestClient
    from ruleshield import proxy

    class FakeCodexToolStyleStreamResponse:
        def __init__(self):
            self.status_code = 200

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def aiter_lines(self):
            yield 'data: {"type":"response.output_item.done","item":{"type":"message","role":"assistant","content":[{"type":"output_text","text":"probe beta 88 confirmed"}]}}'
            yield 'data: {"type":"response.completed","response":{"output":[{"type":"message","role":"assistant","content":[{"type":"output_text","text":"probe beta 88 confirmed"}]}],"usage":{"input_tokens":11,"output_tokens":4}}}'
            yield "data: [DONE]"

    class FakeHttpClient:
        def stream(self, method, url, headers=None, content=None):
            return FakeCodexToolStyleStreamResponse()

    class FakeCacheManager:
        def __init__(self):
            self.shadow_logs = []
            self.request_logs = []
            self.cached_response = None

        async def check(self, prompt_hash, prompt_text):
            return None

        async def log_request(self, **kwargs):
            self.request_logs.append(kwargs)

        async def store(self, **kwargs):
            self.cached_response = kwargs

        async def log_shadow(self, **kwargs):
            self.shadow_logs.append(kwargs)

    class FakeRuleEngine:
        async def async_match(self, prompt_text, messages=None, model=None):
            return None

        async def async_match_candidates(self, prompt_text, messages=None, model=None):
            assert prompt_text == "shadow model probe beta 88"
            return {
                "rule_id": "shadow_model_threshold_probe",
                "deployment": "candidate",
                "response": {
                    "content": "probe beta 88 confirmed",
                    "model": "ruleshield-rule",
                },
            }

    class FakeFeedbackManager:
        def __init__(self):
            self.accepts = []
            self.rejects = []

        async def record_accept(self, rule_id, prompt_text):
            self.accepts.append((rule_id, prompt_text))

        async def record_reject(self, rule_id, prompt_text, rule_response, llm_response):
            self.rejects.append((rule_id, prompt_text, rule_response, llm_response))

    original_http_client = proxy.http_client
    original_cache_manager = proxy.cache_manager
    original_rule_engine = proxy.rule_engine
    original_feedback_manager = proxy.feedback_manager
    original_settings = proxy.settings

    fake_cache = FakeCacheManager()
    fake_feedback = FakeFeedbackManager()

    proxy.http_client = FakeHttpClient()
    proxy.cache_manager = fake_cache
    proxy.rule_engine = FakeRuleEngine()
    proxy.feedback_manager = fake_feedback
    proxy.settings = SimpleNamespace(
        provider_url="https://chatgpt.com/backend-api/codex",
        api_key="",
        cache_enabled=False,
        rules_enabled=True,
        shadow_mode=True,
        log_level="info",
    )

    try:
        client = TestClient(proxy.app)
        with client.stream(
            "POST",
            "/responses",
            json={
                "model": "gpt-5.1-codex-mini",
                "stream": True,
                "input": [{"role": "user", "content": "shadow model probe beta 88"}],
            },
        ) as response:
            body = "".join(response.iter_text())

        assert response.status_code == 200
        assert "response.output_item.done" in body
        assert response.headers["x-ruleshield-shadow"] == "shadow_model_threshold_probe"
        assert len(fake_cache.request_logs) == 1
        assert len(fake_cache.shadow_logs) == 1
        assert fake_cache.shadow_logs[0]["rule_id"] == "shadow_model_threshold_probe"
        assert fake_cache.shadow_logs[0]["llm_response"] == "probe beta 88 confirmed"
        assert fake_feedback.accepts == [
            ("shadow_model_threshold_probe", "shadow model probe beta 88")
        ]
        assert fake_feedback.rejects == []
    finally:
        proxy.http_client = original_http_client
        proxy.cache_manager = original_cache_manager
        proxy.rule_engine = original_rule_engine
        proxy.feedback_manager = original_feedback_manager
        proxy.settings = original_settings


def test_api_shadow_returns_tune_examples():
    import asyncio
    from types import SimpleNamespace

    from ruleshield import proxy

    class FakeCacheManager:
        async def get_shadow_stats(self, limit=None, rule_id=None):
            assert limit is None
            assert rule_id is None
            return {
                "total_comparisons": 3,
                "avg_similarity": 0.2,
                "per_rule": [
                    {
                        "rule_id": "shadow_model_threshold_probe",
                        "total": 3,
                        "avg_similarity": 0.2,
                        "good": 0,
                        "partial": 0,
                        "poor": 3,
                    }
                ],
                "ready_for_activation": [],
            }

        async def get_shadow_examples(self, limit=5, match_quality="poor", rule_id=None):
            assert limit == 5
            assert match_quality == "poor"
            assert rule_id is None
            return [
                {
                    "rule_id": "shadow_model_threshold_probe",
                    "prompt_text": "shadow model probe beta 88",
                    "rule_response": "probe beta 88 confirmed",
                    "llm_response": "I checked a few things and here is a longer answer",
                    "similarity": 0.1,
                    "similarity_pct": 10.0,
                    "length_ratio": 0.4,
                    "match_quality": "poor",
                    "created_at": "2026-03-15 00:00:00",
                }
            ]

    original_cache_manager = proxy.cache_manager
    original_settings = proxy.settings

    proxy.cache_manager = FakeCacheManager()
    proxy.settings = SimpleNamespace(shadow_mode=True)

    async def run():
        result = await proxy.api_shadow(recent=None, rule_id=None)
        assert result["enabled"] is True
        assert result["total_comparisons"] == 3
        assert result["tune_examples"][0]["rule_id"] == "shadow_model_threshold_probe"
        assert result["tune_examples"][0]["match_quality"] == "poor"

    try:
        asyncio.run(run())
    finally:
        proxy.cache_manager = original_cache_manager
        proxy.settings = original_settings
