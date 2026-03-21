"""Tests for rulecore JSON feedback store."""
import os
import tempfile
import shutil

import pytest
from rulecore.store import JsonFileFeedbackStore, FeedbackStore
from rulecore.types import FeedbackEntry, RuleEvent


@pytest.fixture
def store_path():
    tmpdir = tempfile.mkdtemp(prefix="rulecore-store-")
    path = os.path.join(tmpdir, "feedback.json")
    yield path
    shutil.rmtree(tmpdir, ignore_errors=True)


class TestJsonFileFeedbackStore:
    def test_implements_protocol(self):
        assert isinstance(JsonFileFeedbackStore("/tmp/test.json"), FeedbackStore)

    def test_save_and_load_feedback(self, store_path):
        store = JsonFileFeedbackStore(store_path)
        entry = FeedbackEntry(rule_id="r1", prompt="hello", feedback_type="accept")
        store.save_feedback(entry)
        loaded = store.load_feedback()
        assert len(loaded) == 1
        assert loaded[0].rule_id == "r1"
        assert loaded[0].feedback_type == "accept"

    def test_save_and_load_events(self, store_path):
        store = JsonFileFeedbackStore(store_path)
        event = RuleEvent(rule_id="r1", event_type="confidence_update", delta=0.01)
        store.save_event(event)
        loaded = store.load_events()
        assert len(loaded) == 1
        assert loaded[0].event_type == "confidence_update"

    def test_filter_by_rule_id(self, store_path):
        store = JsonFileFeedbackStore(store_path)
        store.save_feedback(FeedbackEntry(rule_id="r1", prompt="a", feedback_type="accept"))
        store.save_feedback(FeedbackEntry(rule_id="r2", prompt="b", feedback_type="reject"))
        r1_only = store.load_feedback(rule_id="r1")
        assert len(r1_only) == 1
        assert r1_only[0].rule_id == "r1"

    def test_persistence_across_instances(self, store_path):
        store1 = JsonFileFeedbackStore(store_path)
        store1.save_feedback(FeedbackEntry(rule_id="r1", prompt="x", feedback_type="accept"))
        store2 = JsonFileFeedbackStore(store_path)
        loaded = store2.load_feedback()
        assert len(loaded) == 1

    def test_empty_store(self, store_path):
        store = JsonFileFeedbackStore(store_path)
        assert store.load_feedback() == []
        assert store.load_events() == []
