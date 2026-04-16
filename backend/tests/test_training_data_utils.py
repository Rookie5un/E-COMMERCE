from pathlib import Path
import unittest

from training_data_utils import (
    DatasetValidationError,
    build_dataset_summary,
    load_labeled_texts,
    read_training_csv,
)


class TrainingDataUtilsTestCase(unittest.TestCase):
    def setUp(self):
        self.sample_file = Path(__file__).resolve().parents[1] / "data" / "train_sample.csv"
        self.binary_file = Path(__file__).resolve().parents[1] / "data" / "train.csv"

    def test_sample_dataset_contains_three_labels(self):
        texts, labels, summary = load_labeled_texts(
            self.sample_file,
            require_all_labels=True,
            min_samples_per_label=1,
            min_content_length=5,
        )

        self.assertEqual(len(texts), 30)
        self.assertEqual(len(labels), 30)
        self.assertEqual(summary.label_counts["negative"], 10)
        self.assertEqual(summary.label_counts["neutral"], 10)
        self.assertEqual(summary.label_counts["positive"], 10)

    def test_binary_dataset_fails_three_class_validation(self):
        dataframe = read_training_csv(self.binary_file)

        with self.assertRaises(DatasetValidationError):
            load_labeled_texts(
                self.binary_file,
                require_all_labels=True,
                min_samples_per_label=1,
                min_content_length=5,
            )

        summary = build_dataset_summary(dataframe, self.binary_file)
        self.assertEqual(summary.label_counts["neutral"], 0)


if __name__ == "__main__":
    unittest.main()
