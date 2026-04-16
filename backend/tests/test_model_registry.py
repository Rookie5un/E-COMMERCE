from pathlib import Path
import tempfile
import unittest

from app.nlp.model_registry import resolve_sentiment_model_path


class ModelRegistryTestCase(unittest.TestCase):
    def test_prefers_local_alias_when_present(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            model_root = Path(temp_dir)
            local_model_dir = model_root / "roberta-sentiment"
            local_model_dir.mkdir()

            resolved = resolve_sentiment_model_path(
                model_name="roberta-sentiment",
                model_folder=str(model_root),
                fallback_model_name="hfl/chinese-roberta-wwm-ext",
            )

            self.assertEqual(resolved, str(local_model_dir))

    def test_falls_back_to_remote_name_when_local_alias_missing(self):
        resolved = resolve_sentiment_model_path(
            model_name="roberta-sentiment",
            model_folder=None,
            fallback_model_name="hfl/chinese-roberta-wwm-ext",
        )

        self.assertEqual(resolved, "hfl/chinese-roberta-wwm-ext")


if __name__ == "__main__":
    unittest.main()
