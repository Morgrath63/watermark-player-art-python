from src.watermark_publisher import AssetSubmission, PublishDecision, publish_submission


class NoCallClient:
    def process_watermark(self, image, text, request_id):
        raise AssertionError("queued submissions must not be published")


def test_long_caption_enters_moderation_queue():
    submission = AssetSubmission("p7", "image-id", "x" * 241)
    assert publish_submission(submission, NoCallClient()) == PublishDecision(status="queued", reason="caption_review")


class FixedClient:
    def process_watermark(self, image, text, request_id):
        assert request_id == "p7"
        return "watermarked-image-id"


def test_approved_caption_publishes_watermarked_image():
    submission = AssetSubmission("p7", "image-id", "Arena badge")
    assert publish_submission(submission, FixedClient()) == PublishDecision(status="published", image="watermarked-image-id")
