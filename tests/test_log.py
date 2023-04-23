import logging

import pytest
import structlog

logger = structlog.get_logger("test")


def spline_reticulator():
    logger.info("reticulating splines", n_splines=123)


def main_ish():
    structlog.configure(processors=[])
    # this configure call should be a no-op after fixture was injected
    logger.debug("yo")


def binding():
    log = logger.bind(k="v")
    log.debug("dbg")
    log.info("inf", kk="more context")
    log = log.unbind("k")
    log.warning("uh-oh")


def test_capture_creates_items(log):
    assert not log.events
    spline_reticulator()
    assert log.events


def test_assert_without_context(log):
    spline_reticulator()
    assert log.has("reticulating splines")


def test_assert_with_subcontext(log):
    spline_reticulator()
    assert log.has("reticulating splines", n_splines=123)


def test_assert_with_bogus_context(log):
    spline_reticulator()
    assert not log.has("reticulating splines", n_splines=0)


def test_assert_with_all_context(log):
    spline_reticulator()
    assert log.has("reticulating splines", n_splines=123, level="info")


def test_assert_with_super_context(log):
    spline_reticulator()
    assert not log.has("reticulating splines", n_splines=123, level="info", k="v")


def test_configurator(log):
    main_ish()
    assert log.has("yo", level="debug")


def test_multiple_events(log):
    binding()
    assert log.has("dbg", k="v", level="debug")
    assert log.has("inf", k="v", kk="more context", level="info")


def test_length(log):
    binding()
    assert len(log.events) == 3


d0, d1, d2 = [
    {"event": "dbg", "k": "v", "level": "debug"},
    {"event": "inf", "k": "v", "level": "info", "kk": "more context"},
    {"event": "uh-oh", "level": "warning"},
]


def test_membership(log):
    binding()
    assert d0 in log.events


def test_superset_single(log):
    binding()
    assert log.events >= [d0]


def test_superset_multi(log):
    binding()
    assert log.events >= [d0, d2]


def test_superset_respects_ordering(log):
    binding()
    assert not log.events >= [d2, d0]


def test_superset_multi_all(log):
    binding()
    assert log.events >= [d0, d1, d2]


def test_superset_multi_strict(log):
    binding()
    assert not log.events > [d0, d1, d2]


def test_equality(log):
    binding()
    assert log.events == [d0, d1, d2]


def test_inequality(log):
    binding()
    assert log.events != [d0, {}, d1, d2]


def test_total_ordering(log):
    binding()
    assert log.events <= [d0, d1, d2, {}]
    assert log.events < [d0, d1, d2, {}]
    assert log.events > [d0, d1]


def test_dupes(log):
    logger.info("a")
    logger.info("a")
    logger.info("b")
    assert log.events >= [{"event": "a", "level": "info"}]
    assert log.events >= [{"event": "a", "level": "info"}, {"event": "b", "level": "info"}]
    assert log.events >= [
        {"event": "a", "level": "info"},
        {"event": "a", "level": "info"},
        {"event": "b", "level": "info"},
    ]
    assert not log.events >= [
        {"event": "a", "level": "info"},
        {"event": "a", "level": "info"},
        {"event": "a", "level": "info"},
        {"event": "b", "level": "info"},
    ]


def test_filtering(log):
    binding()

    assert log.events == [d0, d1, d2]
    assert log.events.infos() == [d1, d2]
    assert log.events.warnings() == [d2]
    assert not log.events.errors()
    assert not log.events.criticals()


def test_filtering_with_errors(log):
    binding()
    logger.error("really bad", what="everything")
    logger.critical("it just keeps getting worse", what="most things")

    d3 = log.error("really bad", what="everything")
    d4 = log.critical("it just keeps getting worse", what="most things")

    assert log.events == [d0, d1, d2, d3, d4]
    assert log.events.infos() == [d1, d2, d3, d4]
    assert log.events.warnings() == [d2, d3, d4]
    assert log.events.errors() == [d3, d4]
    assert log.events.criticals() == [d4]


def test_events_filter_by_level(log):
    binding()
    expected = [d1, d2]

    assert log.events.filter_by_level(logging.INFO) == expected
    assert log.events.filter_by_level("INFO") == expected
    assert log.events.filter_by_level("info") == expected


def test_events_filter_by_unknown_level(log):
    binding()
    with pytest.raises(ValueError) as exi:
        log.events.filter_by_level("unknown")
    assert str(exi.value) == "Unknown level name unknown"


def test_partial_match(log):
    binding()
    assert log.partial_events == [
        {"event": "dbg"},
        {"event": "inf"},
        {"event": "uh-oh"},
    ]
    assert log.partial_events != [
        {"event": "dbg"},
        {"event": "inf", "extra": "WRONG"},
        {"event": "uh-oh"},
    ]


def test_partial_match_in_filtered_list(log):
    binding()
    assert log.partial_events.infos() == [
        {"event": "inf"},
        {"event": "uh-oh"},
    ]
    assert log.partial_events.infos() != [
        {"event": "inf", "extra": "WRONG"},
        {"event": "uh-oh"},
    ]
    assert log.partial_events != [
        {"event": "dbg"},
        {"event": "WRONG"},
        {"event": "uh-oh"},
    ]


def test_partial_match_in_sub_sequence(log):
    binding()
    assert log.partial_events >= [
        {"event": "dbg"},
        {"event": "inf"},
    ]
    assert not log.partial_events >= [
        {"event": "dbg"},
        {"event": "inf"},
        {"event": "WRONG"},
    ]
    assert not log.partial_events >= [
        {"event": "dbg"},
        {"event": "inf", "data": "WRONG"},
    ]


def test_event_factories(log):
    assert log.debug("debug-level", extra=True) == {"event": "debug-level", "level": "debug", "extra": True}
    assert log.info("info-level", more="yes") == {"event": "info-level", "level": "info", "more": "yes"}
    assert log.warning("warning-level", another=42) == {"event": "warning-level", "level": "warning", "another": 42}
    assert log.error("error-level", added=1) == {"event": "error-level", "level": "error", "added": 1}
    assert log.critical("crit-level", above="beyond") == {"event": "crit-level", "level": "critical", "above": "beyond"}


@pytest.mark.parametrize(
    "level, name",
    [
        (logging.DEBUG, "debug"),
        (logging.INFO, "info"),
        (logging.WARNING, "warning"),
        (logging.ERROR, "error"),
        (logging.CRITICAL, "critical"),
    ],
)
def test_dynamic_event_factory(log, level, name):
    expected = {"event": "dynamic-level", "level": name, "other": 42}

    assert log.log(level, "dynamic-level", other=42) == expected
    assert log.log(name, "dynamic-level", other=42) == expected
    assert log.log(name.upper(), "dynamic-level", other=42) == expected


def test_event_factory__bad_level_number(log):
    assert log.log(1234, "text") == {'event': 'text', 'level': 'level 1234'}
