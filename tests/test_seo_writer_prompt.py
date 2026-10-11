"""Vérifie que le prompt compose/batch reçoit le contrat SEO partagé — v0.1."""
import json
from pathlib import Path

from agent.compose_draw_report import SEO_WRITER_RULES_PATH, compose_prompt


ROOT = Path(__file__).resolve().parents[1]


def test_batch_writer_receives_the_shared_seo_constitution():
    facts = json.loads((ROOT / "dist/data/facts/EM-26078.json").read_text())
    shared = SEO_WRITER_RULES_PATH.read_text().strip()

    prompt = compose_prompt(facts)

    assert shared in prompt
    assert "ne pas produire" in prompt
    assert "le gabarit du site" in prompt


def test_shared_prompt_adapts_to_loto_and_keno_without_stars():
    for draw_id, game, domain in [('LO-20261007', 'Loto', 49), ('KE-26372', 'Keno', 56)]:
        facts = json.loads((ROOT / 'dist/data/facts' / (draw_id + '.json')).read_text())
        prompt = compose_prompt(facts)
        assert 'appliquées à ' + game in prompt
        assert '1-' + str(domain) in prompt
        assert '1-50' not in prompt
        assert ' ★ ' not in prompt
        assert SEO_WRITER_RULES_PATH.read_text().strip() in prompt
        if game == 'Loto':
            assert 'numéro Chance 08' in prompt
        else:
            assert 'ne donne pas la probabilité de gain' in prompt
